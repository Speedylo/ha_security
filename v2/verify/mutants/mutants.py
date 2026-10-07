#!/usr/bin/env python3
"""Phase 4.3: one mutant per enforcement point, each a single exact replacement in the framework.

Plan §7.3: remove or invert each security-relevant check and confirm that at least one suite fails.
A mutant that survives is a claim with no test behind it. Each mutant below is one `old → new`
replacement that must match exactly once, so the patch it generates is small enough to review by
eye. `python3 verify/mutants/mutants.py` writes `Mxx.patch` beside this file (unified diffs against
`framework/`, applied with `patch -p1` from `v2/`).

**Criteria, fixed before any mutant runs (2026-10-06).** A mutant is *killed* when at least one of
the 26 suites exits non-zero with the mutant applied, and *survives* otherwise. Every kill is then
read: the failing check is recorded, and a kill only by a crash unrelated to the claim (the sandbox
failing to start, say) is reported as *killed, weakly*. The unmutated tree passes 26/26
(`experiments/verify/results/phase4/regress_f03/`). The plan listed 17; M8 is split into its two
independent chains, so 18.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent.parent

MUTANTS = [
    ("M01", "S6", "default deny becomes allow: a request matching no clause is granted",
     "framework/confine/manifest.py",
     '        return Decision(False, f"{target!r} matches no clause at {pointer}", clause=pointer)',
     '        return Decision(True, f"{target!r} matches no clause at {pointer}", clause=pointer)'),
    ("M02", "S1, T02", "identity is taken from the request's own `integration` field, not the socket",
     "framework/confine/mediator.py",
     # Regenerated 2026-10-06 for the final tag: F33 put the call inside a `try`, one indent deeper.
     "            decision = self.policy(identity, request)",
     '            decision = self.policy(str(request.get("integration") or identity), request)'),
    ("M03", "S4, F3", "an egress clause matches on the host and ignores the port",
     "framework/confine/manifest.py",
     "            return str(clause) == target",
     '            return str(clause).rpartition(":")[0] == str(target).rpartition(":")[0] '
     'if ":" in str(clause) else str(clause) == target'),
    ("M04", "T10", "`is_public` accepts RFC 1918 addresses",
     "framework/confine/egress.py",
     "    return not (parsed.is_private or parsed.is_loopback or parsed.is_link_local\n"
     "                or parsed.is_multicast or parsed.is_reserved or parsed.is_unspecified)",
     "    return not (parsed.is_loopback or parsed.is_link_local\n"
     "                or parsed.is_multicast or parsed.is_reserved or parsed.is_unspecified)"),
    ("M05", "T10", "`is_lan` accepts public addresses (§7.43's exfiltration)",
     "framework/confine/egress.py",
     "    return parsed.is_private and not (parsed.is_loopback or parsed.is_link_local",
     "    return not (parsed.is_loopback or parsed.is_link_local"),
    ("M06", "T11", "the address resolved at request time is not re-checked before connecting",
     "framework/confine/egress.py",
     "            if not allow_private and not is_public(address):",
     "            if False:"),
    ("M07", "S7, §5.11.3", "an acting decision is recorded after it acts (§7.36.1)",
     "framework/confine/mediator.py",
     # Regenerated 2026-10-06 for the final tag: F33 wrapped the act in a `try`. Same mutation: an
     # acting decision's record is written after the act instead of before it.
     "        self._record(identity, request, decision)\n"
     "        if not decision.allowed and self._refused(identity):\n"
     "            return\n"
     "        if decision.allowed and decision.act is not None:\n"
     "            try:\n"
     "                outcome = decision.act()\n",
     "        if decision.act is None or not decision.allowed:\n"
     "            self._record(identity, request, decision)\n"
     "        if not decision.allowed and self._refused(identity):\n"
     "            return\n"
     "        if decision.allowed and decision.act is not None:\n"
     "            try:\n"
     "                outcome = decision.act()\n"
     "                self._record(identity, request, decision)\n"),
    ("M08a", "S7", "the keyed MAC chain is not checked",
     "framework/confine/audit.py",
     '            if not hmac.compare_digest(computed_mac, record.get("mac", "")):',
     '            if False and not hmac.compare_digest(computed_mac, record.get("mac", "")):'),
    ("M08b", "S7", "the hash chain's link is not checked",
     "framework/confine/audit.py",
     '            if record.get("prev_hash") != last_hash:',
     '            if False and record.get("prev_hash") != last_hash:'),
    ("M09", "T12, §8.7 #14", "the manifest is not re-read at registration",
     "framework/confine/mediator.py",
     "        if bind is not None and component is not None:\n"
     "            bind(identity, Path(component))",
     "        if False:\n"
     "            bind(identity, Path(component))"),
    ("M10", "S3", "the subscription filter is bypassed: every subscriber gets every push",
     "framework/confine/mediator.py",
     "            if entity_id not in entities:\n"
     "                continue",
     "            if False:\n"
     "                continue"),
    ("M11", "T19", "the flood cut-off counts nothing",
     "framework/confine/mediator.py",
     "        if len(recent) < self.flood_limit:\n"
     "            return False",
     "        if True:\n"
     "            return False"),
    ("M12", "T19", "a cut-off integration may register again",
     "framework/confine/mediator.py",
     "        if identity in self.cut_off:\n"
     "            raise CutOff(",
     "        if False:\n"
     "            raise CutOff("),
    ("M13", "S8", "the seccomp filter allows the calls it lists instead of refusing them",
     "framework/confine/seccomp.py",
     "                                SECCOMP_RET_ERRNO | (errno.EPERM & 0xFFFF)))",
     "                                SECCOMP_RET_ALLOW))"),
    ("M14", "C1, S8", "the integration's own directory is mounted read-write",
     "framework/confine/sandbox.py",
     "    _bind(spec.own_dir, inside(SandboxSpec.COMPONENT), read_only=True)",
     "    _bind(spec.own_dir, inside(SandboxSpec.COMPONENT), read_only=False)"),
    ("M15", "T15", "`/proc` is the host's, bound in, not a fresh mount of the sandbox's PID namespace",
     "framework/confine/sandbox.py",
     '    mount("proc", inside("/proc"), "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC)',
     '    _bind("/proc", inside("/proc"), read_only=False)'),
    ("M16", "§7.38, C7", "a command's answer is accepted from a channel it was not sent to",
     "framework/confine/mediator.py",
     # Regenerated 2026-10-06 for the final tag: F33 added a type check before the lookup. Same
     # mutation: an answer is accepted from any channel, not only the one the command went to.
     "        if not isinstance(ident, int) or self._sent_commands.get(ident) != fd:",
     "        if not isinstance(ident, int) or ident not in self._sent_commands:"),
    ("M17", "S5", "a wildcard in `services.call` (`lock.*`) is accepted at parse",
     "framework/confine/manifest.py",
     "    for entry in services:\n"
     '        if "*" in entry:',
     "    for entry in services:\n"
     '        if False and "*" in entry:'),
    # Added 2026-10-07 (notes/tests_bite_prediction_20261007.md): F45's gate, added after 4.3 ran.
    # The bridge runs inside (A), so these need (A) brought up from the mutated tree.
    ("M18a", "F45, R3", "the bridge's gate admits every authenticated user",
     "framework/ha_bridge/confine_bridge/__init__.py",
     "        if user is None or not (user.is_admin or (designated and user.id == designated)):",
     "        if user is None:"),
    ("M18b", "F45, R3", "the bridge's gate admits every user once some mediator is designated",
     "framework/ha_bridge/confine_bridge/__init__.py",
     "        if user is None or not (user.is_admin or (designated and user.id == designated)):",
     "        if user is None or not (user.is_admin or designated):"),
    ("M18c", "F45, R3", "any user may designate the mediator, not only an admin",
     "framework/ha_bridge/confine_bridge/__init__.py",
     "@websocket_api.require_admin\n"
     "@websocket_api.websocket_command({\n"
     '    vol.Required("type"): "confine_bridge/designate_mediator",',
     "@websocket_api.websocket_command({\n"
     '    vol.Required("type"): "confine_bridge/designate_mediator",'),
    # Added 2026-10-07 (notes/f48_f49_prediction_20261007.md): the branches branch coverage found
    # no suite running (F49), and the supervisor (F48). M25 is predicted equivalent on 3.13/3.14.
    ("M19", "F49, S6", "a declared config_entries clause grants whatever its value",
     "framework/confine/manifest.py",
     "            allowed = clauses is True",
     "            allowed = True"),
    ("M20", "F49, S6", "an events clause matches every event",
     "framework/confine/manifest.py",
     "            return str(clause) == target\n        return clause == target",
     "            return str(clause) == target\n        return True"),
    ("M21", "F49, S6", "policy_for permits an identity with no manifest bound",
     "framework/confine/manifest.py",
     '            return Decision(False, f"no manifest is bound to {identity} (S6)",',
     '            return Decision(True, f"no manifest is bound to {identity} (S6)",'),
    ("M22", "F49, S7", "an act that raises is reported as permitted",
     "framework/confine/mediator.py",
     '                outcome = Decision(False, f"acting on the request failed: "',
     '                outcome = Decision(True, f"acting on the request failed: "'),
    ("M23", "F49, T19", "an act that fails does not count toward the cut-off",
     "framework/confine/mediator.py",
     "                self._record(identity, request, outcome)\n"
     "                if self._refused(identity):\n"
     "                    return",
     "                self._record(identity, request, outcome)\n"
     "                if False:\n"
     "                    return"),
    ("M24", "F49, W2 (b)", "a granted datagram decision's relay socket is not watched",
     "framework/confine/mediator.py",
     "        if decision.allowed and decision.source is not None:",
     "        if False:"),
    ("M25", "F49, T10", "is_lan does not unwrap IPv4-mapped IPv6 (predicted equivalent)",
     "framework/confine/egress.py",
     "        parsed = parsed.ipv4_mapped\n    return parsed.is_private and not",
     "        pass\n    return parsed.is_private and not"),
    ("M26", "F49, T10", "open_local ignores a refused decision",
     "framework/confine/egress.py",
     "        if not decision.allowed:\n"
     "            raise EgressRefused(decision.reason, decision.clause)\n"
     '        address, port = request.get("address"), request.get("port")',
     "        if False:\n"
     "            raise EgressRefused(decision.reason, decision.clause)\n"
     '        address, port = request.get("address"), request.get("port")'),
    ("M27", "F49, channel", "a declared frame length over MAX_FRAME is believed",
     "framework/confine/channel.py",
     "            if length > MAX_FRAME:",
     "            if False:"),
    ("M28", "F49, channel", "more than MAX_FDS descriptors in one frame are accepted",
     "framework/confine/channel.py",
     "        if len(fds) > MAX_FDS:",
     "        if False:"),
    ("M29", "F49, channel", "a frame that is not a JSON object is accepted",
     "framework/confine/channel.py",
     "            if not isinstance(message, dict):",
     "            if False:"),
    ("M30", "F49, channel", "the sending side frames a message over MAX_FRAME",
     "framework/confine/channel.py",
     "        if len(payload) > MAX_FRAME:",
     "        if False:"),
    ("M31", "F48, T19", "a cut-off does not stop the sandbox",
     "framework/confine/supervise.py",
     '        say(f"{identity} cut off by the mediator; killing its sandbox")\n        self.stop()',
     '        say(f"{identity} cut off by the mediator; killing its sandbox")\n        pass'),
    ("M32", "F48, §7.44", "a reinstatement does not ask for a start",
     "framework/confine/supervise.py",
     '        say(f"{identity} reinstated (recorded); starting it again")\n        self.wanted = True',
     '        say(f"{identity} reinstated (recorded); starting it again")\n        self.wanted = False'),
    ("M33", "F48, F29", "after (A) returns, the supervisor forgets the integration was running",
     "framework/confine/supervise.py",
     "        self.wanted = was_running\n",
     "        self.wanted = False\n"),
    ("M34", "F48, F30", "a dead supervisor's sandboxes are not cleared",
     "framework/confine/supervise.py",
     "        if self.delegation.parent is None:\n            return 0\n        cleared, stuck = 0, []",
     "        if True:\n            return 0\n        cleared, stuck = 0, []"),
    ("M35", "F48", "a sandbox that exits by itself is restarted",
     "framework/confine/supervise.py",
     '            say(f"{self.domain} exited by itself (status {status}); not restarting it")\n',
     '            say(f"{self.domain} exited by itself (status {status}); not restarting it")\n'
     "            self.wanted = True\n"),
    ("M36", "F49, channel", "a truncated length prefix is not caught",
     "framework/confine/channel.py",
     "        if len(header) < _LENGTH.size:",
     "        if False:"),
    ("M37", "F49, channel", "a frame shorter than its declared length is accepted",
     "framework/confine/channel.py",
     "            if payload is None or len(payload) < length:",
     "            if payload is None:"),
]


def main() -> int:
    for ident, claim, what, path, old, new in MUTANTS:
        source = (V2 / path).read_text()
        count = source.count(old)
        if count != 1:
            print(f"{ident}: the original text occurs {count} times in {path}; expected once")
            return 1
        mutated = source.replace(old, new)
        rel = path.split("/", 1)[1]           # patch -p1 from v2/: a/confine/... → framework/
        diff = difflib.unified_diff(source.splitlines(keepends=True),
                                    mutated.splitlines(keepends=True),
                                    fromfile=f"a/{path}", tofile=f"b/{path}", n=2)
        header = f"# {ident} ({claim}): {what}\n"
        (HERE / f"{ident}.patch").write_text(header + "".join(diff))
        print(f"{ident:<5} {claim:<14} {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
