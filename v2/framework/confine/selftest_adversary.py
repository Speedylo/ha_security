"""A deliberately hostile integration, inside a sandbox, trying everything it can.

§5.8.2's fourth scope item: "Adversarial cases — S1, S2, S6, S8: the garbage-collector
technique, credential recovery attempts, absent and malformed manifests, and the 2021
file-theft pattern."

**The test is one string.** The configuration directory holds a canary in `secrets.yaml` and
another in `.storage/core.config_entries`. The adversary runs inside a sandbox, attempts every
attack it can, and reports what it found. The suite fails if either canary appears anywhere in
that report — no matter which attack produced it, and no matter what the attack's own verdict
said. A single unambiguous criterion is worth more than thirty individual assertions that could
each be written slightly wrong.

**Three outcomes, not two, and the distinction is the design's whole argument.**

    BLOCKED   the attempt raised — something refused it
    EMPTY     the attempt *succeeded* and found nothing, because there was nothing there
    LEAKED    the attempt returned something it should not have

§5.6.2's claim is that denial under R2 is structural rather than procedural: an integration
reading `secrets.yaml` "is not refused by a check — there is nothing there to read". A design
that produced only BLOCKED would be the procedural one. **EMPTY is the stronger result**, and
reporting the two separately is the only way to show which is which. The garbage-collector
attack is the clearest case: it runs perfectly, exactly as §2.4.1 published it, and finds
nothing — not because it was stopped, but because the objects it enumerates are the only ones
in the process.

Run:  systemd-run --user --scope -q python3 -m confine.selftest_adversary
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from .channel import Channel
from .audit import attach
from .audit import summarise as durable_summary
from .cgroup import Delegation, ResourceLimits, SandboxCgroup
from .manifest import Manifest, policy_for
from .mediator import Mediator
from .preflight import require_ready
from .sandbox import SandboxSpec
from .spawn import become_subreaper, start

# If either of these ever reaches the adversary, the framework has failed. They are long and
# unusual so that a substring search cannot match them by accident.
CANARY_SECRET = "CANARY-SECRETS-9d41c7b2e8f04a16-DO-NOT-DISCLOSE"
CANARY_TOKEN = "CANARY-TOKEN-5b8e0a3f71c94d62-DO-NOT-DISCLOSE"

# A plausible manifest for a hostile integration: the 2021 disclosures were not integrations
# that asked for everything, they were ordinary ones with a flaw. This one legitimately reads
# one sensor, and everything it does beyond that is the attack.
ADVERSARY_GRANT = {"schema_version": 1,
                   "entities": {"read": ["sensor.outdoor_temperature"]}}

ATTACKS = r"""
import ctypes, ctypes.util, gc, json, os, select, signal, socket, stat, struct, sys, time
from pathlib import Path

libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)

# A wall-clock budget for the two attacks that search the whole filesystem.
#
# **It exists because of an asymmetry that is itself a result.** Confined, "/" is the sandbox's
# mount namespace — a few dozen files — so an exhaustive search finishes in milliseconds and
# this budget never binds. Unconfined, "/" is the entire host, and the same search walks
# hundreds of thousands of inodes including `/proc`. The bound is applied to **both** arms so
# the attack stays one piece of code with one meaning; it simply never takes effect where the
# filesystem is small. An attack that cannot finish is not evidence either way, and the first
# unconfined run of §7.13 was killed at fifteen minutes having reported nothing at all.
SEARCH_BUDGET_S = 90


def expired(deadline):
    return time.monotonic() > deadline


def emit(entry):
    # One line per attempt, flushed immediately. An adversarial probe that reports only at the
    # end loses everything if the framework stops it part-way — which is precisely the outcome
    # worth recording. Same reasoning as §6.8.3: write the record before the thing that might
    # not survive.
    sys.stdout.write(json.dumps(entry) + "\n")
    sys.stdout.flush()


# Run one attack in a forked child and return what it managed to say. Bulk filesystem search
# reaches the cgroup's memory limit -- cgroup v2 charges page cache to whichever cgroup faulted
# it in, so reading enough file data hits memory.max without the process holding anything. That
# termination is a result, so the attack runs where its death is observable rather than ending
# the whole run.
# The attack ran out of time. NOT a block: nothing refused it, and recording it as one would be
# exactly the mistake §6.6.5 is about.
class Unfinished(Exception):
    pass


def in_child(fn, budget=SEARCH_BUDGET_S + 15):
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)

        def bail(signum, frame):
            try:
                os.write(write_fd, b'"__unfinished__"')
                os.close(write_fd)
            except BaseException:
                pass
            os._exit(0)

        signal.signal(signal.SIGALRM, bail)
        signal.alarm(budget)
        try:
            os.write(write_fd, json.dumps(fn()).encode()[:2000])
        except BaseException as err:
            try:
                os.write(write_fd, json.dumps(f"raised {type(err).__name__}").encode()[:2000])
            except BaseException:
                pass
        try:
            os.close(write_fd)
        except BaseException:
            pass
        os._exit(0)
    os.close(write_fd)

    # **The parent never trusts the child to finish, or even to die**, and that is not
    # defensive style — it is forced by what the attacks do when they work. `PTRACE_TRACEME`
    # succeeds unconfined, and from that moment every signal delivered to the caller — the
    # `SIGCHLD` from this very fork included — stops it for a tracer that will never answer.
    # The earlier form blocked on `read()` and then on `waitpid()`, and three unconfined runs
    # hung for fifteen minutes each reporting nothing. Confined the problem never appeared,
    # because seccomp refuses the call: **the harness was only fragile where the attacks
    # succeed**, which is precisely the arm that had never been run.
    deadline = time.monotonic() + budget
    chunks: list[bytes] = []
    unfinished = False
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            unfinished = True
            break
        ready, _, _ = select.select([read_fd], [], [], min(remaining, 1.0))
        if not ready:
            continue
        chunk = os.read(read_fd, 4096)
        if not chunk:
            break
        chunks.append(chunk)
        try:
            # A whole message in hand ends the wait. The child may still wedge on its way out
            # and there is no reason to care: it has already said everything it was going to.
            json.loads(b"".join(chunks).decode(errors="replace"))
            break
        except ValueError:
            continue
    os.close(read_fd)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
    status = 0
    try:
        _, status = os.waitpid(pid, 0)
    except OSError:
        pass

    message = b"".join(chunks).decode(errors="replace")
    if not message:
        # The distinction is the whole of S9's evidence and must not be collapsed. A child the
        # **kernel** killed was stopped by a control; a child **this harness** killed merely ran
        # out of patience. Reporting the second as the first is how §6.9 came to cite a cgroup
        # kill that was really a device node, and reporting the first as the second would throw
        # away the only in-band demonstration S9 has.
        if not unfinished and os.WIFSIGNALED(status):
            raise OSError(f"stopped by signal {os.WTERMSIG(status)} before it could finish")
        raise Unfinished(f"did not complete within {budget}s")
    value = json.loads(message)
    if value == "__unfinished__":
        raise Unfinished(f"did not complete within {budget}s")
    return value


def record(family, name, fn):
    # BLOCKED: it raised. EMPTY: it worked and found nothing. LEAKED: it returned something.
    # UNFINISHED: it ran out of time, which is none of the three and must not be read as any.
    try:
        found = fn()
    except Unfinished as err:
        emit({"family": family, "attack": name, "outcome": "UNFINISHED", "detail": str(err)})
        return
    except BaseException as err:
        emit({"family": family, "attack": name, "outcome": "BLOCKED",
              "detail": f"{type(err).__name__}: {err}"[:120]})
        return
    emit({"family": family, "attack": name,
          "outcome": "LEAKED" if found else "EMPTY",
          "detail": str(found)[:400] if found else ""})


# ---- S8 / T14: the 2021 file-theft pattern -------------------------------------------
# The disclosed flaw was directory traversal reaching "any file that is accessible by the
# Home Assistant process ... including any credential that you might have stored".
TRAVERSALS = [
    "../../secrets.yaml", "../../../secrets.yaml", "../../../../secrets.yaml",
    "/config/secrets.yaml", "secrets.yaml", "../secrets.yaml",
    "../../.storage/core.config_entries", "/config/.storage/core.config_entries",
    "/sandbox/../secrets.yaml", "/sandbox/component/../../secrets.yaml",
    CONFIG_ROOT + "/secrets.yaml", CONFIG_ROOT + "/.storage/core.config_entries",
]
for target in TRAVERSALS:
    record("2021 traversal", target, lambda t=target: Path(t).read_text()[:200])


# Bounded on purpose. The unbounded version is a separate attack below, because it does not
# survive its own greed.
SWEEP_FILE_LIMIT = 20000
SWEEP_BYTE_LIMIT = 32 * 1024 * 1024


# `/dev` is pruned along with the kernel filesystems, and only **regular** files are read.
#
# This is a correction, not a precaution. The original form called `os.path.getsize()` and read
# anything it reported as small — and a character device reports zero. So the attack opened
# `/dev/zero` and read an infinite stream into memory until something killed it. Unconfined that
# is a hang; confined the cgroup killed it, the harness recorded `BLOCKED ... stopped by signal
# 9`, and §6.9 read that as the resource limit stopping a filesystem search. The verdict was
# right and the reason was wrong: the process died reading a device node, not reading secrets.
#
# §6.6.5 is the general form of this and it has now happened a fourth time — a negative result
# that was correct for a reason nobody checked. An attacker hunting for credentials reads
# regular files; restricting the sweep to them is what the attack always meant.
SKIP_ROOTS = ("/proc", "/sys", "/dev", "/run")


def sweep():
    hits, seen, read = [], 0, 0
    deadline = time.monotonic() + SEARCH_BUDGET_S
    for base, dirs, files in os.walk("/", topdown=True):
        if base.startswith(SKIP_ROOTS):
            dirs[:] = []
            continue
        for name in files:
            seen += 1
            if seen > SWEEP_FILE_LIMIT or read > SWEEP_BYTE_LIMIT or expired(deadline):
                return hits
            path = os.path.join(base, name)
            try:
                info = os.stat(path)
                if not stat.S_ISREG(info.st_mode) or info.st_size > 262144:
                    continue
                text = Path(path).read_text(errors="ignore")
                read += info.st_size
            except OSError:
                continue
            if "CANARY-" in text:
                hits.append(path)
    return hits


record("2021 traversal", "walk every reachable file", lambda: in_child(sweep))


def exhaust():
    # The same search with no bound at all: hold every byte it reads. Regular files only, for
    # the reason above — otherwise this measures `/dev/zero` rather than the resource limit,
    # and S9 is not what a device node demonstrates.
    blob = []
    for base, dirs, files in os.walk("/", topdown=True):
        if base.startswith(SKIP_ROOTS):
            dirs[:] = []
            continue
        for name in files:
            path = os.path.join(base, name)
            try:
                if not stat.S_ISREG(os.stat(path).st_mode):
                    continue
                blob.append(Path(path).read_bytes())
            except OSError:
                continue
    return f"read {sum(len(b) for b in blob)} bytes and kept them"


def exhaust_memory():
    # **Allocate, do not read.** §6.9's resource-limit evidence came from an attack that read
    # files, and reading only exhausts memory where there is enough data to read — which
    # §5.6.2 guarantees there is not. Once `/dev/zero` was excluded, the file-reading attack
    # stopped reaching the cap at all, and S9 was left with no in-band demonstration. An
    # integration that wants to exhaust memory does not go looking for large files; it asks
    # for memory. This is that attack, and the cgroup's kill is the result.
    blob = []
    while True:
        blob.append(bytearray(8 * 1024 * 1024))


# Skippable, and only ever skipped in the **unconfined** arm (§7.12's pairing). Confined, this
# attack is bounded by the cgroup and its death is the S9 result. Unconfined there is no cgroup,
# so running it would read the host's filesystem into memory until the machine died — a
# demonstration of T16 that costs the test hardware and settles nothing anyone disputes. The
# omission is recorded in the report rather than left silent.
if os.environ.get("CONFINE_ADVERSARY_SKIP_UNBOUNDED"):
    for skipped in ("read every file with no bound at all", "allocate memory until stopped"):
        emit({"family": "resource limit", "attack": skipped, "outcome": "NOT RUN",
              "detail": "skipped unconfined: nothing would bound it, and T16 is not in dispute"})
else:
    record("resource limit", "read every file with no bound at all", lambda: in_child(exhaust))
    record("resource limit", "allocate memory until stopped",
           lambda: in_child(exhaust_memory, budget=60))

# ---- S2 / T15: credential recovery ----------------------------------------------------
record("credential recovery", "read another process's environ",
       lambda: [p for p in os.listdir("/proc") if p.isdigit() and p != str(os.getpid())])
record("credential recovery", "read /proc/self/environ for a token",
       lambda: [line for line in Path("/proc/self/environ").read_bytes()
                .decode(errors="ignore").split("\0") if "CANARY-" in line])
record("credential recovery", "read /etc/shadow", lambda: Path("/etc/shadow").read_text()[:80])
record("credential recovery", "list the host's home directory",
       lambda: os.listdir(os.path.expanduser("~")))

# ---- S1 / §2.4.1: the garbage-collector technique -------------------------------------
# Corno & Mannella's published attack: walk the heap and read another integration's live
# objects. It is expected to run flawlessly and find nothing, which is the point.
def gc_sweep():
    hits = []
    for obj in gc.get_objects():
        try:
            if isinstance(obj, (str, bytes)) and b"CANARY-" in (
                    obj.encode(errors="ignore") if isinstance(obj, str) else obj):
                hits.append(str(obj)[:80])
            elif isinstance(obj, dict):
                for value in obj.values():
                    if isinstance(value, str) and "CANARY-" in value:
                        hits.append(value[:80])
        except BaseException:
            continue
    return hits


record("gc technique", "gc.get_objects() heap sweep", gc_sweep)
record("gc technique", "objects reachable in this heap",
       lambda: None if len(gc.get_objects()) >= 0 else 1)
emit({"family": "gc technique", "attack": "heap size", "outcome": "EMPTY",
      "detail": f"{len(gc.get_objects())} objects, all its own"})

# ---- escaping the sandbox --------------------------------------------------------------
record("escape", "chroot(/)", lambda: libc.chroot(b"/") == 0 or _raise())
record("escape", "unshare(CLONE_NEWUSER)",
       lambda: libc.unshare(0x10000000) == 0 or _raise())
record("escape", "mount a tmpfs over /sandbox",
       lambda: libc.mount(b"tmpfs", b"/sandbox", b"tmpfs", 0, None) == 0 or _raise())
record("escape", "setuid(0)", lambda: os.setuid(0))

# ---- reaching another integration ------------------------------------------------------
record("reach another", "connect to a TCP service on the host",
       lambda: socket.create_connection(("127.0.0.1", 8123), timeout=2) and "connected")
record("reach another", "resolve a name on the internet",
       lambda: socket.gethostbyname("example.invalid"))
record("reach another", "list open unix sockets",
       lambda: [line for line in Path("/proc/net/unix").read_text().splitlines()[1:]])

# ---- S7 / T18: reaching the audit log ---------------------------------------------------
# `Path("/").rglob` was the original form and it does not terminate on a real host: it descends
# `/proc` and stats every inode on the machine. Same search, same meaning, bounded the same way
# as the sweep above.
def find_audit_log():
    hits, seen = [], 0
    deadline = time.monotonic() + SEARCH_BUDGET_S
    for base, dirs, files in os.walk("/", topdown=True):
        if base.startswith(SKIP_ROOTS):
            dirs[:] = []
            continue
        for name in files:
            seen += 1
            # Checked per file, not per directory. One directory holding a million entries is
            # enough to carry a per-directory check past any budget.
            if seen > SWEEP_FILE_LIMIT * 20 or expired(deadline):
                return hits
            if name.endswith(".jsonl"):
                hits.append(os.path.join(base, name))
                if len(hits) >= 10:
                    return hits
    return hits


record("audit log", "find any .jsonl on the filesystem", lambda: in_child(find_audit_log))

# ---- S6: what the mediator will do for it ------------------------------------------------
# Absent unconfined, and that absence is the finding rather than a gap in the test: an
# unconfined integration asks nobody for anything, so there is no decision to record.
CHANNEL_FD = os.environ.get("CONFINE_CHANNEL_FD")
sock = (socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, fileno=int(CHANNEL_FD))
        if CHANNEL_FD is not None else None)


def ask(message):
    payload = json.dumps(message).encode()
    sock.sendall(struct.pack(">I", len(payload)) + payload)
    header = b""
    while len(header) < 4:
        header += sock.recv(4 - len(header))
    (length,) = struct.unpack(">I", header)
    body = b""
    while len(body) < length:
        body += sock.recv(length - len(body))
    return json.loads(body)


MEDIATED = [
    ("read the sensor it declared", {"op": "entity.read",
                                     "entity": "sensor.outdoor_temperature"}),
    ("read an entity it did not declare", {"op": "entity.read",
                                           "entity": "sensor.bedroom_occupancy"}),
    ("call lock.unlock", {"op": "service.call", "service": "lock.unlock"}),
    ("claim to be another integration", {"op": "entity.read", "integration": "demo_trusted",
                                         "entity": "sensor.bedroom_occupancy"}),
    ("enumerate everyone's config entries", {"op": "config_entries.list"}),
    ("reach a host it did not declare", {"op": "network.egress", "host": "evil.invalid"}),
    ("an operation that does not exist", {"op": "platform.eval", "code": "1"}),
    # T4. Decided on `service` and, until T4, *recorded* against `entity` — a field the
    # sandbox chose. The decision was never wrong; the audit trail of it could be made to lie.
    ("misdirect the audit log", {"op": "service.call", "service": "lock.unlock",
                                 "entity": "sensor.outdoor_temperature"}),
]
if sock is None:
    emit({"family": "mediated", "attack": "ask the mediator for anything at all",
          "outcome": "UNMEDIATED",
          "detail": "no mediator exists; this process acts directly and asks no one"})
else:
    for label, message in MEDIATED:
        answer = ask(message)
        emit({"family": "mediated", "attack": label,
              "outcome": "PERMIT" if answer.get("ok") else "DENY",
              "detail": answer.get("clause") or ""})
    # T4, and last because it costs the channel: a frame that is not JSON. The mediator must drop
    # this sandbox and nothing else — and, from T4, record that it did, durably.
    junk = b"{not json"
    sock.sendall(struct.pack(">I", len(junk)) + junk)
    try:
        closed = sock.recv(4) == b""
    except OSError:
        closed = True
    emit({"family": "mediated", "attack": "send the mediator a malformed frame",
          "outcome": "DENY" if closed else "PERMIT",
          "detail": "channel closed by the mediator" if closed else "the mediator answered"})
    sock.close()


# Last, and deliberately last. `PTRACE_TRACEME` is the one attack that changes the process
# rather than reading it: where it succeeds, the caller becomes a tracee and the next signal
# stops it indefinitely. Every attack that forks runs above this line.
record("escape", "ptrace(PTRACE_TRACEME)", lambda: libc.ptrace(0, 0, 0, 0) == 0 or _raise())


def _raise():
    raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))
"""


def build_config(root: Path) -> dict[str, Path]:
    layout = {"own": root / "custom_components" / "demo_adversary",
              "data": root / ".confine" / "demo_adversary",
              "storage": root / ".storage"}
    layout["storage"].mkdir(parents=True)
    (layout["storage"] / "core.config_entries").write_text(
        json.dumps({"entries": [{"token": CANARY_TOKEN}]}))
    (root / "secrets.yaml").write_text(f"api_key: {CANARY_SECRET}\n")
    layout["own"].mkdir(parents=True)
    layout["data"].mkdir(parents=True)
    (layout["own"] / "__init__.py").write_text("# hostile\n")
    (layout["own"] / "manifest.json").write_text(json.dumps(
        {"domain": "demo_adversary", "name": "Adversary", "version": "1.0.0",
         "permissions": ADVERSARY_GRANT}))
    return layout


def main() -> int:
    require_ready(deep=False)
    become_subreaper()

    root = Path(tempfile.mkdtemp(prefix="confine-adversary-"))
    mediator = Mediator()
    audit_dir = attach(mediator, "confine-adversary-audit-")
    durable: dict = {}
    try:
        layout = build_config(root)
        manifest = Manifest.load(layout["own"], root)
        mediator.policy = policy_for({"demo_adversary": manifest})
        mediator_end, sandbox_end = Channel.pair()
        mediator.register("demo_adversary", Channel(mediator_end), component=layout["own"])

        script = (f"CONFIG_ROOT = {json.dumps(str(root))}\n"
                  "def _raise():\n"
                  "    import ctypes, os\n"
                  "    raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))\n"
                  + ATTACKS)
        spec = SandboxSpec(domain="demo_adversary", own_dir=str(layout["own"]),
                           data_dir=str(layout["data"]),
                           argv=[sys.executable, "-c", script])
        delegation = Delegation.discover()
        out = tempfile.NamedTemporaryFile(prefix="confine-adversary-", suffix=".json",
                                          delete=False)
        # stderr goes to a file rather than DEVNULL. §6.4.5 cost twenty minutes to a swallowed
        # error that presented as "the sandbox never reported a pid"; a hostile payload that
        # dies before it can report is exactly the same failure, and it is not worth learning
        # twice.
        err = tempfile.NamedTemporaryFile(prefix="confine-adversary-err-", suffix=".txt",
                                          delete=False)
        with SandboxCgroup.create(delegation, "confine-adversary",
                                  ResourceLimits(memory_mb=512)) as cgroup:
            with open(out.name, "wb") as stdout, open(err.name, "wb") as stderr:
                sandbox = start(spec, cgroup, stdout=stdout.fileno(),
                                stderr=stderr.fileno(),
                                channel_end=sandbox_end.fileno())
                sandbox_end.detach()
                mediator.serve(timeout=300)
                status = sandbox.wait(timeout=300)
            oom = cgroup.event_count("oom_kill")
            peak = cgroup.peak_memory()
        text = Path(out.name).read_text().strip()
        diagnostic = Path(err.name).read_text().strip()
        Path(out.name).unlink(missing_ok=True)
        Path(err.name).unlink(missing_ok=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        durable = durable_summary(mediator, audit_dir, keep_records=True)

    report = [json.loads(line) for line in text.splitlines() if line.startswith("{")]
    if os.WIFSIGNALED(status):
        # Being stopped is a result, not a failure of the harness — but it has to be recorded
        # as one of the attacks rather than silently ending the run.
        report.append({
            "family": "resource limit", "attack": "the sandbox itself, at the point it stopped",
            "outcome": "BLOCKED",
            "detail": f"killed by signal {os.WTERMSIG(status)}; cgroup oom_kill={oom}, "
                      f"peak {peak / 2**20:.0f} MB"})
    if not report:
        print("the adversary reported nothing at all.")
        print(f"  exit: {status}, oom_kill={oom}, peak {peak / 2**20:.1f} MB")
        if diagnostic:
            print("  said: " + "\n        ".join(diagnostic.splitlines()[-20:]))
        return 1
    verdict = render(report)
    return verdict or durable_verdict(durable)


def durable_verdict(durable: dict) -> int:
    """T4: what the durable record says about the attacks, beside what the attacks said."""
    log = durable.get("log") or []
    decoy = [r for r in log if r.get("kind") == "decision" and r.get("op") == "service.call"
             and (r.get("requested") or {}).get("entity")]
    checks = [
        (durable.get("ok"), "the durable record verifies and reconciles with the in-memory one",
         "; ".join((durable.get("breaks") or []) + (durable.get("reconcile") or []))[:300]),
        (durable.get("runs") == 1, "one run record, written by register()",
         f"{durable.get('runs')} run records"),
        (bool(decoy) and all(r.get("target") == "lock.unlock" for r in decoy),
         "the decoy entity is recorded as requested, and the target is the service decided on",
         str([(r.get("target"), r.get("requested")) for r in decoy])),
        (any(r.get("kind") == "protocol_error" for r in log),
         "the malformed frame is in the durable record", "no protocol_error record"),
    ]
    print("\n  the durable record (T4)")
    for ok, label, detail in checks:
        print(f"    {'ok  ' if ok else 'FAIL'}  {label}" + ("" if ok else f"\n          {detail}"))
    if all(ok for ok, _, _ in checks):
        return 0
    print("FAILED — the durable record disagrees with what happened.")
    return 1


def render(report: list[dict]) -> int:
    print("adversarial self-test — a hostile integration, inside a sandbox\n")
    families: dict[str, list[dict]] = {}
    for entry in report:
        families.setdefault(entry["family"], []).append(entry)

    for family, entries in families.items():
        print(f"  {family}")
        for entry in entries:
            mark = {"BLOCKED": "ok  ", "EMPTY": "ok  ", "DENY": "ok  ",
                    "LEAKED": "LEAK", "PERMIT": "??  ", "NOT RUN": "--  ",
                    "UNMEDIATED": "--  ", "UNFINISHED": "??  "}.get(entry["outcome"], "??  ")
            detail = entry["detail"][:52]
            print(f"    {mark}  {entry['outcome']:<8} {entry['attack']:<38} {detail}")
        print()

    blob = json.dumps(report)
    leaked = [e for e in report if e["outcome"] == "LEAKED"]
    canaries = [c for c in (CANARY_SECRET, CANARY_TOKEN) if c in blob]

    counts = {}
    for entry in report:
        counts[entry["outcome"]] = counts.get(entry["outcome"], 0) + 1
    print("  " + "   ".join(f"{k} {v}" for k, v in sorted(counts.items())))

    # The one criterion. Everything above is diagnosis; this is the test.
    print()
    if canaries:
        print(f"FAILED — {len(canaries)} canary string(s) reached the adversary.")
        return 1
    if leaked:
        print(f"FAILED — {len(leaked)} attack(s) returned something: "
              f"{[e['attack'] for e in leaked]}")
        return 1

    # The declared read must be permitted, or the sandbox is confining by being broken.
    permitted = [e["attack"] for e in report if e["outcome"] == "PERMIT"]
    if permitted not in ([], ["read the sensor it declared"]):
        print(f"FAILED — the permit set is {permitted}, expected only the declared read")
        return 1
    if not permitted:
        print("INCOMPLETE — the adversary was stopped before it reached the mediated attacks.")
        print("             Nothing leaked, but the mediated half of the suite did not run.")
        return 2

    print("PASS — neither canary reached the adversary, and the only thing it was permitted")
    print("       is the one thing its manifest declared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
