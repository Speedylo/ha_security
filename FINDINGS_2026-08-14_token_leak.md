# Two findings: the token leaks into the sandbox, and the audit log cannot prove what it appears to

**Date:** 2026-08-14
**Status:** Both confirmed by test on the development machine. No repository code changed.
**Affects:** `spike/supervisor.py` — the credential-confidentiality property and the
non-repudiation property that the framework rests on.
**Feeds into:** `THREAT_MODEL.md` (unwritten), and the justification for workstream 4 (isolation).

**Common root cause:** the sandbox runs as the same user account as the supervisor, with an
unrestricted view of the filesystem and of `/proc`. Both findings follow from that single fact,
and one control — isolation — substantially addresses both.

This document is written to be read cold. Parts 1–4 build the background concepts (tokens,
environment variables, `/proc`) before any finding appears; Part 6 does the same for hash chains.
Skip ahead only if those are already familiar.

---

## Contents

1. [What a token is, and why the project depends on it](#part-1)
2. [A note on the word "path" — it means two unrelated things](#part-2)
3. [Environment variables: the "bag of notes"](#part-3)
4. [`/proc`: Linux showing running programs as files](#part-4)
5. [What an attacker actually does with this](#part-5)
6. [**The audit log: what a hash chain does and does not prove**](#part-6)
7. [Why this cannot be fixed in `supervisor.py` — and why that's good news](#part-7)
8. [The test that confirmed it](#part-8)
9. [Check yourself](#part-9)
10. [Draft threat-model rows](#part-10)

---

<a name="part-1"></a>

## Part 1: What a token is, and why the project depends on it

Home Assistant has a **web API**. That means HA is listening on `http://your-pi:8123`, and any
program that can reach it over the network can send it requests — "give me the state of every
device", "unlock the front door".

Obviously it can't let *anyone* do that. So HA requires proof that the caller is allowed. That
proof is a **long-lived access token** — a long random string of characters, much like a very
long password. You generate one in HA's UI. It looks roughly like:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4YzI4...
```

Two properties matter:

1. **Whoever holds it can do anything to HA.** There are no partial tokens. It is not
   "read-only" or "sensors only". It is a master key to the whole house — read every sensor,
   see who is home, unlock every lock, call every service.
2. **It is just text.** There is no hardware element, no fingerprint, no device binding. If a
   program can *read those characters*, that program has full control of the house. Copying it
   costs nothing and leaves no trace.

**The entire project design rests on one sentence:**

> The supervisor holds the token. The sandboxed integration never sees it.

That is *why* the sandbox has to ask permission for everything. It is not that the sandboxed
integration is choosing to be polite — it is that it has no other way to reach HA. It does not
have the key. It must knock on the supervisor's door and ask, and the supervisor checks the
manifest before acting on its behalf.

### The analogy used throughout this document

- The **supervisor** is a security guard holding the master key to the building.
- The **sandboxed integration** is a contractor you have let inside.
- The contractor cannot open any door themselves. They ask the guard, and the guard consults a
  list (the **manifest**) of which rooms this contractor may enter.

The security claim is: *the contractor never gets a copy of the master key.*

**What this document reports is that the contractor can read the master key off the guard's
desk.** Four different ways, all confirmed by test. But two Linux concepts have to be clear
first, or none of the rest means anything.

---

<a name="part-2"></a>

## Part 2: A note on the word "path" — it means two unrelated things

This caused confusion in conversation and is worth stating explicitly. "Path" gets used for two
completely different concepts in this project:

| Term | What it means | Relevant here? |
|---|---|---|
| `sys.path` | The list of **folders Python searches** when you write `import something`. This is the *shim* trick: put the fake `homeassistant` folder first, so `import homeassistant` finds the fake one instead of the real one. | **No.** Nothing to do with tokens. |
| A file location such as `/proc/1234/environ` | A **location of a file**, the ordinary everyday meaning. | **Yes.** This is the token problem. |

Everything from here on uses only the second meaning. The shim and `sys.path` play no part in
this finding.

---

<a name="part-3"></a>

## Part 3: Environment variables — the "bag of notes"

Every running program on Linux carries a **bag of labelled notes**. Each note has a name and a
value:

```
HOME     = /home/younes
USER     = younes
LANG     = en_GB.UTF-8
HA_TOKEN = eyJhbGciOiJIUzI1NiIs...
```

These are **environment variables**. They are the standard way to hand a program some settings
without putting them on the command line, and passing secrets this way is extremely common —
it is how most software receives API keys.

### The rule that causes the problem

> **When a program starts another program, the child gets a copy of the parent's entire bag by
> default.**

This is normal, default behaviour, and usually convenient: a child program automatically knows
your home folder, your language, your terminal type. But it means **secrets ride along too**,
unless you deliberately take them out.

### What `supervisor.py` does

The supervisor starts the sandbox as a child program. Two lines set up the child's bag:

```python
env = dict(os.environ)        # line 320: make a COPY of my entire bag of notes
env.update({ ... })           # line 321: ADD some new notes to that copy
```

`update` **adds**. It never removes. So if the supervisor's bag contained a note labelled
`HA_TOKEN`, that note is now in the sandbox's bag as well.

### Why that is not a hypothetical

The supervisor *deliberately* reads the token out of its own bag, at line 283:

```python
token = args.ha_token or os.environ.get("HA_TOKEN", "")
```

In plain terms: *"use the token given on the command line; if there isn't one, take the note
labelled `HA_TOKEN` out of my bag."*

So supplying the token through the bag is a **supported, documented way to run the supervisor** —
the `--ha-token` help text says as much: *"(or set HA_TOKEN)"*. And that supported route is
precisely the route that hands the token to the sandbox.

### The comment that claims otherwise

Directly above the copy, at line 329:

```python
# No HA token in the child's environment: the supervisor holds it.
```

That comment describes an **intention**. The code does not implement it. This matters beyond the
bug itself: a reader auditing the file would take that comment as an assurance, and it is not
one.

---

<a name="part-4"></a>

## Part 4: `/proc` — Linux showing running programs as files

This is the second concept, and it is the one that makes the problem hard to fix.

Linux has a folder called `/proc`. It is not a real folder on disk — it is a **live window into
the kernel**, presented as files so that ordinary programs can read it. Inside `/proc` there is
a numbered folder for every running program on the machine:

```
/proc/1234/     <- everything about the program whose ID is 1234
/proc/5678/     <- everything about the program whose ID is 5678
```

Every running program has an **ID number** (a "PID", process ID). Two files inside each folder
matter here:

| File | Contents |
|---|---|
| `/proc/1234/environ` | Program 1234's entire **bag of notes** — including any secrets in it |
| `/proc/1234/cmdline` | The exact **command line** that started program 1234 |

So `/proc` means: *a running program's private settings are readable as an ordinary file, by
anything permitted to read that file.*

### Who is permitted?

**By default, any program running under the same user account.** Not merely the same program —
the same *user*.

That is the crux. The supervisor and the sandbox both run as the user `younes`. The sandbox is
started with a plain `subprocess.Popen(...)` — an ordinary child program, same user account, no
restrictions of any kind applied. As far as Linux is concerned, the sandbox has every right to
read the supervisor's `/proc` files.

### The two-step read

A program can always ask for its own parent's ID number. `os.getppid()` does this; it is a
completely normal, unprivileged call. So the sandbox can:

1. Ask *"what is my parent's ID?"* → gets `1234`
2. Open `/proc/1234/environ` → **reads the supervisor's entire bag of notes, `HA_TOKEN`
   included**

### Why this is the door that matters

**Even if Part 3 is fixed, this one still works.**

You could carefully strip `HA_TOKEN` out of the copy handed to the child — and the child would
simply read the supervisor's *own* bag directly through `/proc` instead. Removing the note from
the copy does not help while the original is readable.

### The command line leaks identically

A reasonable reaction to Part 3 is: *"fine, don't use the environment variable — pass the token
as `--ha-token` on the command line instead."*

That does not help either. `/proc/1234/cmdline` holds the command line and is readable by the
same user for the same reason. The sandbox reads the token straight out of it.

### Four doors, one key

*Originally written as three. A fourth was found on 2026-08-14 while verifying that isolation had
actually closed the others — see the note below. It is the simplest of the four, which is worth
noticing: the sophisticated routes were found first.*

| # | Door | Closing it alone is enough? |
|---|---|---|
| 1 | The token sits in the **child's own bag** (copied at line 320) | No |
| 2 | The token sits in the **parent's bag**, readable via `/proc/<parent>/environ` | No |
| 3 | The token sits in the **parent's command line**, readable via `/proc/<parent>/cmdline` | No |
| 4 | The token sits in **a file on disk**, `spike/.ha_token`, readable with plain `open()` | No |

Closing any one leaves the other three open.

**Door 4, added 2026-08-14.** `run_targets.sh` and `ha_compare_setup.sh` read the credential from
`spike/.ha_token` and pass it with `--ha-token`. The file is mode `0600` — but that only restricts
*other users*, and the sandbox runs as the same user, so `open("/home/.../spike/.ha_token")` is
enough. No `/proc` trick required.

This is worth recording as a methodological point rather than quietly fixing. Doors 2 and 3
require knowing that `/proc/<pid>/environ` exists and is same-uid readable; door 4 requires
noticing that a file is a file. The first pass found the clever routes and missed the obvious
one, which is a normal failure mode in security review and an argument for **enumerating where a
secret physically lives** — environment, command line, kernel-exposed process state, disk — rather
than reasoning attack-by-attack.

**All four are closed by `--isolate`** (§5.9 / `RESULTS_2026-08-14_isolation_spike.md`): door 1 by
the environment scrub in `supervisor.py`, doors 2 and 3 by the PID namespace, and door 4 by the
mount namespace, since `.ha_token` is not on the filesystem allowlist. Verified with a real token
present — baseline reports `readable — CONTAINS HA_TOKEN`, isolated reports `BLOCKED`.

---

<a name="part-5"></a>

## Part 5: What an attacker actually does with this

This is the part worth internalising, because it is what makes this a finding rather than a
nitpick.

A malicious integration author does **not** need to defeat the `Manifest` class. They do not
need to find a flaw in `decide()`. They do not attack the policy engine at all. They add roughly
this to their integration:

```python
import os, urllib.request

# Step 1: read the supervisor's secrets straight out of /proc
with open(f"/proc/{os.getppid()}/environ", "rb") as f:
    notes = f.read().decode(errors="replace")
token = [n for n in notes.split("\0") if n.startswith("HA_TOKEN=")][0].split("=", 1)[1]

# Step 2: talk to Home Assistant directly, as a fully trusted client
urllib.request.urlopen(urllib.request.Request(
    "http://homeassistant:8123/api/services/lock/unlock",
    data=b'{"entity_id": "lock.front_door"}',
    headers={"Authorization": f"Bearer {token}"},
))
```

That code grabs the master key, then **phones Home Assistant directly** and unlocks the front
door.

### Contrast with the probe

`probe.py` check #3 attempts `hass.services.async_call("lock", "unlock", ...)`. That call goes
through the shim, through the socket, into `decide()`, hits the `calls_services` check, and is
**denied**. Correctly. That result is real and it stands.

But the code above **never touches the socket**. It walks around the building rather than trying
the guard's door.

### The consequence that should bother you most

> **The audit log records nothing.**

The hash chain remains perfectly intact. `AuditLog.verify()` reports `OK — chain intact`.
Because the chain only records decisions that were *asked for*, and this attacker never asked.

The tamper-evidence is genuinely sound. It simply has nothing to say about an event that
bypassed it entirely.

### In the project's own vocabulary

The glossary in `PROJECT_STATUS.md` §7 defines the confused deputy as: *"The attacker never
escapes the sandbox because they never need to."*

The same shape applies here, one step earlier. The attacker is not breaking out of the sandbox.
**They picked up the key that was sitting inside the sandbox with them.**

---

<a name="part-6"></a>

## Part 6: The audit log — what a hash chain does and does not prove

Part 5 ended with the claim *"the audit log records nothing."* That deserves a full explanation,
because the audit log is a real piece of engineering that does a real job — and understanding
precisely **which** job it does is what lets you state its limit confidently rather than
defensively.

### 6.1 Why have a log at all

When the supervisor makes a decision — *allow this, deny that* — it writes a line to a file in
`spike/audit/`. One line per decision, in JSON. That file is the evidence trail: what did this
integration ask for, and what did the supervisor say?

This matters because prevention alone is not a security story. If a lock integration tried to
unlock the front door at 3am and was denied, you want a **record** of the attempt. The denial
protects the house; the record is what tells you the integration is malicious and should be
removed.

### 6.2 The problem with an ordinary log file

A plain text log has an obvious weakness: **anyone who can write to the file can edit it.**

An attacker who gets write access can open the file and delete the line recording their attempt.
Now the house is unchanged, but the evidence is gone. A log that can be silently edited is not
evidence — it is a suggestion.

The standard defence is not to make the file un-editable (usually impossible), but to make edits
**detectable**. That is what "tamper-evident" means: you cannot stop someone changing it, but you
can guarantee that if they do, it shows.

### 6.3 What a hash is

A **hash function** takes any input text and produces a fixed-length fingerprint:

```
sha256("hello")  ->  2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
sha256("hellp")  ->  fbe27d78a4a17e3c1f66f9e0ca4d0e5b32e3a0ee16b4e0f1a6e08a2b6f0c1f4e
```

Three properties matter:

1. **Deterministic** — the same input always gives the same fingerprint.
2. **Avalanche** — change one character of the input and the fingerprint changes completely.
   There is no partial resemblance.
3. **One-way** — you cannot work backwards from a fingerprint to the original text.

So a fingerprint is a compact way to say *"this exact text, unchanged."* If the text changes at
all, the fingerprint no longer matches.

### 6.4 What "chaining" adds

A fingerprint per record would catch someone editing a record — but not someone **deleting** a
whole record, or **reordering** records. Each remaining record would still match its own
fingerprint.

Chaining fixes that. **Each record's fingerprint is computed over its own content *plus the
previous record's fingerprint*.** In `supervisor.py`:

```python
@staticmethod
def _digest(prev: str, record: dict) -> str:                       # line 96
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()
```

Read `(prev + payload)`: the previous record's hash is glued onto the front of this record's
content before fingerprinting. Then in `append()`:

```python
record["prev"] = self._prev                    # line 111: point back at the last record
record["hash"] = self._digest(self._prev, record)   # 112: fingerprint content + that pointer
self._prev = record["hash"]                    # 113: become the anchor for the next record
```

Laid out, the structure is:

```
record 0:  prev = 0000...0   content C0    hash H0 = sha256( 0000...0 + C0 )
record 1:  prev = H0         content C1    hash H1 = sha256(   H0     + C1 )
record 2:  prev = H1         content C2    hash H2 = sha256(   H1     + C2 )
record 3:  prev = H2         content C3    hash H3 = sha256(   H2     + C3 )
```

Every record is welded to the one before it. The first record's `prev` is sixty-four zeros — an
agreed starting anchor, since there is no earlier record.

### 6.5 Why that makes tampering visible

Suppose an attacker edits record 1 — changing a `DENY` to an `allow`.

- Record 1's content is now `C1'`, so its true fingerprint would be `H1' = sha256(H0 + C1')`.
- But the file still stores the *old* `H1` on record 1, and record 2 still stores `prev = H1`.
- `verify()` recomputes record 1's fingerprint from its content, gets `H1'`, compares against the
  stored `H1` — **mismatch, detected.**

To hide the edit, the attacker must also update record 1's stored hash. But then record 2's
`prev` points at a hash that no longer exists, so record 2 must be updated, which changes record
2's hash, which breaks record 3... **the damage cascades all the way to the end of the file.**

That is the entire idea. `verify()` (lines 121–134) just walks the file, recomputing each
fingerprint and checking each `prev` pointer:

```python
if record.get("prev") != prev:
    return False, f"line {line_number}: chain broken (prev mismatch)"
if AuditLog._digest(prev, record) != stored_hash:
    return False, f"line {line_number}: record altered (hash mismatch)"
```

**The analogy:** the audit log is a visitor sign-in book at the guard's desk, where each page is
sealed with a wax seal that includes an imprint of the previous page's seal. You cannot tear out
page 5 without every seal after it being visibly wrong.

### 6.6 Demonstrated — the naive tamper is caught

Run against a copy of a real audit log from 2026-08-12, which contains a genuine denial at
sequence 9 (`call_service lock.unlock -> DENY`):

```
$ ./supervisor.py --verify orig.jsonl
OK: chain intact (11 records)
```

Now edit record 9, flipping the denial to an allow, and change nothing else:

```
$ ./supervisor.py --verify attack_a.jsonl
BROKEN: line 10: record altered (hash mismatch)
```

**Caught.** This is the design working exactly as intended, on real data.

---

### 6.7 Limit 1 — integrity is not completeness

Here is the crux, and it is the answer to *"why doesn't the log help against the token attack?"*

A hash chain guarantees:

> **Every record that is in this file is exactly as it was written, in the order it was written,
> with none removed.**

It says **nothing whatsoever** about events that were *never written in the first place*.

Look at where `append()` is called — `handle_connection`, line 250:

```python
allowed, reason, payload = self.decide(message)
...
self.audit.append(self.manifest.name, str(message.get("op")), params, allowed, reason)
```

That is the **only** place a record is ever created. It sits inside the loop that reads messages
off the bridge socket. So the causal chain is:

```
message arrives on the socket  ->  decide() runs  ->  append() writes a record
```

**No socket message means no `decide()` call, which means no record.**

The token attack in Part 5 never sends a socket message. It reads the token out of `/proc` and
calls Home Assistant's REST API directly. The supervisor is not merely fooled — it is *not
involved*. There is nothing for it to log, because from its point of view nothing happened.

So after a successful token-bypass attack:

- The lock was unlocked.
- `verify()` reports `OK — chain intact`.
- Both statements are true simultaneously.

**Back to the analogy:** the contractor climbed in through a window. The sign-in book is
pristine — no torn pages, every seal perfect. There is no missing entry to notice, because they
never walked past the desk.

> **Integrity of a log ≠ completeness of a log.** The chain protects the first. Only *unavoidable
> mediation* can deliver the second — and mediation is unavoidable only when the sandbox has no
> route to HA other than the socket. Which is, once again, isolation.

### 6.8 "But wouldn't the sequence numbers show a gap?"

This is the natural objection, and it is worth working through because the answer is instructive.

Each record carries a `seq` counter (0, 1, 2, 3...). Surely a missing event leaves a gap?

**No — and the reason is precise.** `self._seq` increments inside `append()`, at line 114. It
counts **records created**, not **events that occurred**. When an attack bypasses the socket, no
record is created, so the counter simply never advances for it. The file reads 0, 1, 2, 3 with
no gap at all.

A gap would indicate a record was created and then *deleted* — that is tampering, and the chain
already catches it. But there is no tampering here. Nothing was removed. The event never entered
the system.

**This distinction is exactly what makes the finding worth writing up.** The log is not broken,
and the attacker did not defeat it. The log is answering a different question from the one you
want answered.

---

### 6.9 Limit 2 — the chain can be rebuilt wholesale

A second, independent limit, which an auditor will find if you do not state it first.

Look again at `_digest`: it is plain `sha256`. **There is no secret key.** The function is fully
public and fully deterministic. Anyone who can read `supervisor.py` can compute valid hashes.

So an attacker who can *write to the log file* need not attempt the naive edit that Part 6.6
caught. They can rewrite every record with whatever contents they like and **recompute the entire
chain from the zero anchor**, producing a file that is internally perfectly consistent.

Demonstrated against the same real log — the same edit as before, but this time recomputing all
eleven hashes:

```
$ ./supervisor.py --verify attack_b.jsonl
OK: chain intact (11 records)

   seq 9: call_service lock unlock -> allow | calls_services matches lock.unlock
```

**The chain verifies as intact while asserting that the lock unlock was allowed.** The record of
the denial is gone and nothing detects it.

### 6.10 Why limit 2 has the same root cause as the token leak

The obvious reply is: *"only the supervisor can write to the log, and the supervisor is trusted."*

**That is not true today.** The audit file lives at `spike/audit/<domain>-<run>.jsonl`, an
ordinary file owned by `younes`. The sandbox runs as `younes` too, with no filesystem
restrictions — this is the same fact established in Part 4, and it is exactly what `probe.py`
check #5 already reports as unblocked ("read host filesystem — no fs isolation yet").

So a sandboxed integration can **read, rewrite, or delete its own audit log** while it runs. The
tamper-evidence property, like the credential-confidentiality property, is **currently dependent
on isolation that does not exist yet.**

That unification is the useful insight: two apparently separate weaknesses, one root cause.

### 6.11 What actually fixes each limit

| Limit | Fix | Workstream |
|---|---|---|
| **Completeness** (6.7) — bypassed events are never logged | Make mediation unavoidable: sandbox under a separate uid / PID namespace, with no network route to HA and no access to the credential | 4 (isolation) |
| **Rebuild** (6.9) — no secret, chain is recomputable | Any *one* of: (a) **HMAC** the chain with a key the sandbox never sees; (b) **sign** each record with a private key held only by the supervisor; (c) **anchor** the head hash externally — append to a remote append-only store, or periodically publish it — so a rebuilt chain disagrees with a witness the attacker cannot reach | New, small |
| **Write access** (6.10) — the sandbox can reach the file at all | Filesystem isolation: the audit directory is simply not visible inside the sandbox's mount namespace | 4 (isolation) |

Option (c) is worth noting because it is the honest general answer: a purely local chain can
always be rebuilt by whoever holds the file. Detecting that requires **something outside the
attacker's reach** to compare against. `supervisor.py`'s own docstring gestures at this — *"the
decentralised attestation layer is out of scope"* (lines 83–85) — which was the right scoping
call. This finding gives the concrete reason why, and that belongs in the report.

### 6.12 What to claim, and what not to claim

The value of this section is that it lets you make a **precise** claim instead of a vague one.
Precision here is an asset with an auditor, not a weakness.

**Do not claim:** *"the framework provides a tamper-proof audit log."* Two words are wrong —
*tamper-proof* (it is tamper-*evident*, and only against an attacker who cannot recompute) and
the implication of completeness.

**Do claim:**

> The framework maintains a hash-chained decision log which is tamper-evident against
> after-the-fact modification by an actor that cannot recompute the chain. Two limits are
> documented and both are addressed by planned work: the chain records only *mediated*
> operations, so its completeness depends on mediation being unavoidable (isolation, workstream
> 4); and it uses an unkeyed digest with no external anchor, so an actor with write access to the
> log file can rebuild it consistently (addressed by an HMAC or external anchoring, and by
> denying the sandbox filesystem access to the log).

That sentence is longer than the marketing version, and it is the one that survives questioning.

---

<a name="part-7"></a>

## Part 7: Why this cannot be fixed in `supervisor.py` — and why that is good news

### The candidate fixes, and what each leaves open

| Fix | Closes | Leaves open |
|---|---|---|
| Delete `HA_TOKEN` from the child's copied bag | Door 1 | `/proc/<parent>/environ`, `/proc/<parent>/cmdline` |
| Stop accepting `--ha-token` on the command line | Door 3 | Both `environ` doors |
| Read the token from a file only the supervisor opens | Door 1 and 3 | The supervisor still holds it in memory, and same-user `/proc` access remains broad |

None of these is sufficient, because none of them changes the fact that **the sandbox runs as
the same user as the supervisor, with an unrestricted view of `/proc`.**

### The fixes that actually work

Both are structural, and both are the same category of change:

- **Run the sandbox under a different user account.** Then `/proc/<supervisor>/environ` is no
  longer readable by it. The kernel enforces this; no application code is involved.
- **Put the sandbox in a PID namespace.** Already confirmed feasible on the development machine
  — `unshare --user --mount --pid --fork` succeeds unprivileged (recorded in `PROJECT_STATUS.md`
  §10.2). A PID namespace means the sandbox *cannot see* other programs at all: `/proc` shows it
  only itself. It cannot find the supervisor to read its files, because from inside the
  namespace the supervisor does not exist.

Both are **workstream 4** — namespaces + seccomp. The workstream currently at zero lines.

### Why this strengthens the project

At present `PROJECT_STATUS.md` justifies isolation as *"the precondition for reproducing the
2021 HACS file-theft result."* That is a fine reason, but it is about reproducing someone
else's finding.

This gives a considerably stronger sentence, about this system:

> **Isolation is not an additional hardening layer. It is a precondition for the confidentiality
> of the Home Assistant credential, without which the mediation layer can be bypassed entirely
> rather than defeated.**

That reframes workstream 4 from *"a feature not yet reached"* into *"a load-bearing element of
the argument, identified by analysis of our own design."*

For an advisor who is a lead auditor by profession, a team that finds this in its own system and
writes it up precisely is demonstrating exactly the discipline being graded. It joins three
existing instances of the same pattern:

1. The `FrozenOrThawed` fix
2. The registry gap — measured, then closed
3. The install-weighting reversal (4.6% → 1.2%)

This is the fourth. **The project keeps catching its own gaps before anyone else does.**

---

<a name="part-8"></a>

## Part 8: The test that confirmed it

Run on the development machine, 2026-08-14. Two throwaway files in a scratch directory — nothing
in the repository was modified.

**`parent.py`** — mimics exactly what `supervisor.py` lines 320–321 do:

```python
import os, subprocess, sys
env = dict(os.environ)                 # <-- exactly what supervisor.py:320 does
env.update({"HACS_DOMAIN": "demo"})    # <-- and :321, which never removes the token
subprocess.run([sys.executable, "child.py"], env=env)
```

**`child.py`** — mimics the sandboxed integration, checking all three doors:

```python
import os
ppid = os.getppid()
# 1. Did the parent's secret land in MY environment?
print("my env has FAKE_SECRET :", "FAKE_SECRET" in os.environ)
# 2. Can I read the parent's environment directly?
with open(f"/proc/{ppid}/environ","rb") as f:
    blob = f.read().decode(errors="replace")
print("parent /proc environ    : READABLE", "and contains FAKE_SECRET" if "FAKE_SECRET" in blob else "")
# 3. Can I read the parent's command line (where --ha-token would be)?
with open(f"/proc/{ppid}/cmdline","rb") as f:
    print("parent /proc cmdline    : READABLE ->", f.read().decode(errors="replace").replace("\x00"," ").strip())
```

**Invocation** — a fake secret in the bag, a fake token on the command line:

```
FAKE_SECRET=llat_pretend_token python3 parent.py --ha-token llat_on_the_cmdline
```

**Result — all three doors open:**

```
my env has FAKE_SECRET : True
parent /proc environ    : READABLE and contains FAKE_SECRET
parent /proc cmdline    : READABLE -> python3 parent.py --ha-token llat_on_the_cmdline
```

No exotic technique is used anywhere in this. Every call is ordinary, unprivileged, and available
to any Python program.

---

### The audit-log tests

Run against a **copy** of a genuine audit log produced by the framework on 2026-08-12
(`spike/audit/andrews_arnold_quota-20260812-114143.jsonl`, 11 records). The original was not
modified. That log contains three real denials, including:

```
seq 7   get_state     lock.front_door   -> DENY
seq 9   call_service  lock.unlock       -> DENY
seq 10  net_request   (exfil host)      -> DENY
```

**Baseline — the untouched log verifies:**

```
$ ./supervisor.py --verify orig.jsonl
OK: chain intact (11 records)
```

**Attack A — flip record 9's `DENY` to `allow`, change nothing else:**

```
$ ./supervisor.py --verify attack_a.jsonl
BROKEN: line 10: record altered (hash mismatch)
```

Caught. The hash chain works as designed.

**Attack B — the same edit, then recompute all eleven hashes from the zero anchor:**

```
$ ./supervisor.py --verify attack_b.jsonl
OK: chain intact (11 records)

   seq 9: call_service lock unlock -> allow | calls_services matches lock.unlock
```

**Not caught.** The log now testifies that a denied lock-unlock was permitted, and `verify()`
endorses it. The rebuild required no secret, because `_digest` uses unkeyed `sha256` — the
recomputation is fifteen lines of Python using only what is already in `supervisor.py`.

---

<a name="part-9"></a>

## Part 9: Check yourself

Reason these out rather than re-reading the text — being able to answer them unprompted is what
makes this defensible in a viva.

1. Suppose `supervisor.py` is patched to strip `HA_TOKEN` out of the bag handed to the child.
   **Is the sandbox now unable to obtain the token? Why or why not?**

2. The audit log's hash chain is cryptographically sound and `verify()` reports `OK`.
   **Why does that not help here?** What class of event does a hash chain fundamentally not
   protect against?

3. Every record carries a `seq` number counting 0, 1, 2, 3… **Why doesn't a bypassed operation
   leave a gap in that sequence?**

4. Attack A (naive edit) was caught; attack B (edit plus full chain rebuild) was not.
   **What single missing ingredient explains the difference** — and name one way to supply it.

<details>
<summary>Answers — try first</summary>

1. **No.** Stripping the copy closes door 1 only. The sandbox reads `/proc/<parent>/environ` and
   gets the token out of the supervisor's *own* bag (door 2), or `/proc/<parent>/cmdline` if the
   token was passed as an argument (door 3). Both remain readable because both processes run
   under the same user account. Only a different uid or a PID namespace closes them.

2. A hash chain provides **integrity of the records that exist** — it proves nobody edited,
   removed, or reordered an entry after the fact. It says nothing about **events that were never
   recorded**. The bypass never sends a message through the socket, so `decide()` is never
   called, so no record is ever created. There is nothing to tamper with. Integrity of a log is
   not the same as completeness of a log, and completeness depends on the mediation being
   unavoidable — which is exactly what isolation provides.

3. Because `seq` increments inside `append()` (line 114), it counts **records created**, not
   **events that happened**. A bypassed operation creates no record, so the counter never
   advances for it and the file reads 0, 1, 2, 3 with no discontinuity. A gap would mean a record
   was created and then deleted — that is tampering, and the chain catches it. Here nothing was
   deleted; the event simply never entered the system.

4. **A secret.** `_digest` is unkeyed `sha256`, so the hashing function is fully public and any
   attacker can recompute a consistent chain. Attack A failed only because it did not bother to;
   attack B succeeded because nothing stopped it. Supply the missing ingredient with any of:
   an **HMAC** keyed with a secret the sandbox never sees; a **digital signature** per record
   using a private key held only by the supervisor; or an **external anchor** — publishing the
   head hash somewhere the attacker cannot rewrite, so a rebuilt chain disagrees with a witness
   out of their reach. (Separately, the sandbox should not be able to reach the log file at all —
   that is isolation again.)

</details>

---

<a name="part-10"></a>

## Part 10: Draft threat-model rows

Two entries for the threat → control → residual-risk table in the (unwritten)
`THREAT_MODEL.md`.

### Row 1 — credential disclosure across the sandbox boundary

| Field | Content |
|---|---|
| **Asset** | Home Assistant long-lived access token — a single unscoped credential granting full read/write over every entity and service |
| **Trust boundary** | Supervisor process (trusted, holds credential) ↔ sandbox process (untrusted, runs third-party code) |
| **Actor** | Malicious or compromised integration author, distributing via HACS |
| **Threat (STRIDE)** | **Information Disclosure** leading to **Elevation of Privilege** — sandbox reads the credential and acts with full supervisor authority |
| **Attack** | Read the credential from any of four locations — the inherited environment, `/proc/<ppid>/environ`, `/proc/<ppid>/cmdline`, or `spike/.ha_token` on disk — then call HA's REST API directly, bypassing the bridge socket entirely |
| **Control (current)** | ✅ **Effective as of 2026-08-14.** `supervisor.py --isolate`: environment scrub (door 1), PID namespace (doors 2–3), mount namespace excluding `.ha_token` from the filesystem allowlist (door 4). Verified with a real token present — probe check #6 goes ALLOWED → BLOCKED. *Before this:* none effective, since both processes shared a uid and the sandbox had unrestricted `/proc` and filesystem visibility |
| **Control (planned)** | Run the sandbox under a **distinct uid** as well, so the boundary does not rest solely on namespace correctness. Also: never place the token in the environment or on a command line at all, so door 1 and door 3 cannot recur if isolation is ever disabled |
| **Residual risk after control** | The supervisor still holds an **unscoped** token. Compromise of the supervisor itself remains full house compromise. HA offers no scoped tokens, so this cannot be mitigated within the framework — it is an upstream limitation and must be stated as such |
| **Detection** | **None.** The hash-chained audit log records only mediated operations; a bypass produces no record. Log integrity is intact but log completeness is not guaranteed without enforced mediation |

**Note the residual-risk row.** Even with isolation built, the supervisor holds a master key that
HA provides no way to scope down. That limitation is upstream, not a design flaw here, and
stating it explicitly is exactly the sort of scope honesty `PROJECT_STATUS.md` §8 identifies as
an asset with this advisor.

### Row 2 — audit log completeness and forgeability

| Field | Content |
|---|---|
| **Asset** | The decision log — the evidence trail showing what each integration attempted and how the supervisor ruled |
| **Trust boundary** | Same boundary as Row 1: supervisor (writes the log) ↔ sandbox (subject of the log) |
| **Actor** | Malicious integration author seeking to act without leaving evidence, or to erase evidence already written |
| **Threat (STRIDE)** | **Repudiation** — the integration performs an action and no attributable record of it exists |
| **Attack A — bypass** | Act without going through the socket (e.g. via the Row 1 credential leak). `decide()` is never called, so no record is created. `verify()` reports `OK`; the log is intact and silent |
| **Attack B — rebuild** | Rewrite the log file with preferred contents and recompute every hash from the zero anchor. `_digest` is unkeyed `sha256`, so this requires no secret. **Demonstrated: `verify()` returns `OK: chain intact (11 records)` on a log doctored to show a denied `lock.unlock` as allowed** |
| **Control (current)** | Hash chain (`supervisor.py:78–134`). **Effective** against naive after-the-fact edits — demonstrated: a single-line edit yields `BROKEN: line 10: record altered`. **Not effective** against either attack above |
| **Control (planned)** | Attack A: isolation (workstream 4) makes mediation unavoidable, so nothing can act without being logged. Attack B: key the chain (HMAC with a secret the sandbox never holds) or anchor the head hash externally; and deny the sandbox filesystem access to `spike/audit/` |
| **Residual risk after control** | A compromised **supervisor** can still write whatever it likes, since it legitimately holds the key. Local logs can never be authoritative against an attacker who controls the writer — only external anchoring shifts that, and full decentralised attestation is explicitly out of scope (`supervisor.py:83–85`) |
| **Detection** | Attack B is currently **undetectable** by `verify()`. Attack A is undetectable in principle by any log, since no event reaches the logger |

**Note how the two rows interlock.** Row 1 is a confidentiality failure and Row 2 is a
non-repudiation failure, but both trace to the same physical fact: the sandbox runs as the same
user with an unrestricted view of the filesystem and of `/proc`. One control — isolation —
substantially addresses both. That is a good structural argument to make in the report: the
threat model should show controls mapping to *several* threats, not one each.

---

## Status and next steps

*This section originally recorded both weaknesses as deliberately unfixed, so the "before" state
would stay demonstrable. That plan held, and the fixes landed the same day — updated below.*

- ✅ **Token: all four doors closed** (§5.9, `RESULTS_2026-08-14_isolation_spike.md`). Door 1 by
  scrubbing `HA_TOKEN` from the child's environment in `supervisor.py`; doors 2 and 3 by the PID
  namespace; door 4 by the mount namespace. **Probe check #6 was added while the gap was still
  open**, so the before/after is a measurement rather than an assertion: baseline reports
  `readable — CONTAINS HA_TOKEN`, isolated reports `BLOCKED`.
- ⚠️ **Log: partly addressed, and the remaining half is still worth doing.** The mount namespace
  removes the sandbox's *access* to `spike/audit/`, which closes the practical attack. The chain
  itself is **still unkeyed**, so anything that does obtain write access can rebuild it. Keying it
  is a small change (roughly `hashlib.sha256` → `hmac.new(key, …, sha256)`, plus deciding where
  the key lives) and the two controls fail independently — which is the argument for having both
  rather than relying on the namespace alone.
- ✅ **Both misleading comments corrected.** `supervisor.py:329` no longer claims the child has no
  token (it now describes the scrub, and notes the scrub alone is insufficient). The `AuditLog`
  docstring now states both measured limits — unkeyed digest, and mediated-only records — instead
  of claiming a compromised integration "cannot remove or reorder a decision".
- 🆕 **Door 4 was found after the fixes**, while verifying the others were closed. It was already
  covered by the mount namespace, so nothing had to change — but see Part 4 for why it is worth
  recording rather than quietly absorbing.

**Still open, and not addressed by anything in this document:**

- ~~**Network egress and lateral movement.**~~ **Closed later the same day** — see
  `RESULTS_2026-08-14_egress_broker.md`. It was correctly identified here as *not* a token
  problem: closing all four doors above did nothing about it, and it needed a separate control
  (seccomp denying IP sockets, plus supervisor-brokered HTTP). **What remains is content, not
  destination:** exfiltration through a host the manifest legitimately declares. No allowlist
  fixes that.
- **Resource exhaustion.** No cgroups.
- **aarch64 is unverified.** Every measurement in this document was taken on x86_64 under WSL2,
  and the four doors are closed by namespaces whose behaviour on the Pi has never been observed.

**A fifth route appeared later the same day, and not through a token at all.** `THREAT_MODEL.md`
§5.1 found that the egress broker — built to close the network route above — authorised host
*names* without resolving them, so an integration could have the supervisor fetch a LAN address
on its behalf. It needs no credential, which is exactly the property that made the raw-socket
route interesting here. Closed the same day.

**For the report:** these join `FrozenOrThawed`, the registry gap, and the install-weighting
reversal as instances of the project auditing itself. The full arc — find it, measure it, write
the failing check, fix it, find a fourth route while verifying the fix, then find a fifth in the
*fix for a different problem* — is more convincing than any single finding, and is worth making
explicit rather than leaving the reader to notice it.
