# §9 System Architecture and Technology Integration — plan for approval

**Written 2026-10-10.** Budget 2,600 words, about 9 pages (`rewrite_plan_outline_mapping.md` §0), and
the pages come mostly from figures. Style: third person, each paragraph topic sentence → evidence →
analysis → link, IEEE citations integrated. The topic sentences below are drafts. Prose is written
only after this plan is approved, and Younes reviews the section against its sources before §8 starts.

**Sources.** Working report Ch5 §5.6–§5.15 (≈17,000 words) and Ch6 (≈21,000), plus the architecture
that was built after Ch6 was written and is recorded only in Ch7: egress (§7.24–§7.25), the push loop
(§7.36), (A) behind the mediator (§7.37), commands from the house (§7.38), the home network
(§7.40–§7.41), OAuth inside the sandbox (§7.42), the refusal flood (§7.44) and the non-admin mediator
(§7.45.11). F54's change to the record (2026-10-10) is included. The 2026-09-08 draft
(`submission/09_system_architecture.md`, 2,883 words) is a skeleton only. It predates everything from
§7.24 on, and its numbers are stale.

## The organising decision

The current draft is organised by the four design decisions, which repeats §8's job (the method and
the design rationale) and leaves no room for what was built later. **Proposed: §9 follows one request
through the system.** It opens with the whole system in one figure and the four decisions in one table,
then takes each component in the order a request meets it: the sandbox the integration runs in, the
manifest that says what it may ask for, the channel and the mediator that decide, the network paths,
the record, and what happens when something fails. Each component is described as built, with its
reason in a sentence and the full argument left in §8 or the working report. The reader therefore
meets the architecture as a system before meeting its parts, and every part answers "what happens to
a request here".

## Opening + 9.1 The system at a glance (≈350 words)

> *The framework moves each third-party integration out of Home Assistant's process into a sandbox of
> its own, and places a mediator between the two that decides, records and performs every request
> that crosses.*

**Figure 9.1 — The system (new).** (A) with the bridge integration; the mediator, running as the
non-admin user `confine-mediator`; the supervisor; N sandboxes, each holding a minimal Home Assistant
runtime, the bridge runtime and one unmodified integration; the channel per sandbox; the egress
broker; the durable audit log. Credentials are drawn where they live: (A)'s token in the mediator,
never in a sandbox.

**Table 9.1 — Four decisions** (one row each: decision, chosen, rejected candidates, the evidence).
1. Where enforcement lives: outside the platform's process (an in-process check is defeated by the
   garbage-collector walk, §12.1).
2. What runs inside: each integration in its own minimal Home Assistant, whose state starts empty and
   holds only what the manifest declares, so an undeclared entity is absent rather than refused.
3. The isolation primitive: Linux namespaces, seccomp-BPF and a cgroup v2 slice per integration,
   chosen over containers, virtual machines and WebAssembly.
4. Scope: every third-party integration, and none of the platform's own.

Link: the sandbox is where a request begins.

## 9.2 The sandbox (≈400 words)

> *Each sandbox is built so that what an integration must not reach is absent from its view, not
> merely forbidden.*

**Figure 9.2 — One sandbox (new).** The namespaces as nested boundaries (user, mount, pid, network,
ipc, uts), the seccomp filter on the syscall edge, the cgroup slice with its memory bound, the
filesystem view (its own directory read-only, `/sandbox/data`), loopback-only networking, and the one
descriptor that leaves: the channel.

Topic sentences: (1) the mechanism table compressed to the figure plus one sentence per namespace
(5.7.3); (2) *the supervisor must run inside the cgroup subtree systemd delegates, which Chapter 5 had
placed wrongly* (6.4.1), and its preflight refuses to confine anything on a host that cannot hold the
boundary (6.4.2); (3) the seccomp narrowing stated honestly (6.4.6); (4) the cost in one line,
pointing to §12.3: memory per sandbox and how many fit on the reference device.

## 9.3 The manifest (≈400 words)

> *An integration's authority is what its manifest declares, and nothing in the manifest can widen
> what Home Assistant itself would allow.*

Declarable capabilities in one table (entities read/subscribe, services call, network egress by host
and port, home-network ports, resource limits). The asymmetry rule (`lock.lock` may be granted without
`lock.unlock`), and what no grant may reach. **Table 9.2 — a worked manifest** with each line's effect
(kept from the draft, numbers rechecked). Who writes it, in one paragraph: author-declared, derived
with the user's confirmation, or absent, which grants nothing (5.9.4). Link: a declaration is only as
good as the point that enforces it.

## 9.4 The mediated request (≈450 words)

> *Every request that crosses the boundary is identified by the channel it arrived on, decided against
> the manifest, recorded durably, and only then performed.*

**Figure 9.3 — The life of a request (new), as a sequence diagram.** Integration → its local Home
Assistant → bridge → channel → mediator: (1) identity from the channel, never from the message;
(2) the decision against the manifest; (3) the durable record; (4) the act on (A); (5) the answer.
Below it, the two other directions: a declared entity's change pushed into the sandbox (§7.36), and
a household's command sent into the integration (§7.38).

Topic sentences: (1) not everything is mediated, because an integration's work inside its own
runtime never crosses, and that is the performance argument (5.11.1); (2) identity is a property of
the channel (5.11.2); (3) the order of the steps, record before act (5.11.3), with the record now
naming the devices a service call targets (F54); (4) the wire format in one sentence, a four-byte
length and JSON; (5) the credential: the mediator holds (A)'s token as a non-admin user, so a
confined integration holds none and the mediator holds less than an integration held before (F45).

## 9.5 Reaching the network (≈400 words)

> *The network namespace gives a sandbox no route anywhere, so every connection it makes is one the
> mediator opened for it.*

**Figure 9.4 — Egress, resolve then pin (new).** The integration connects to a declared host; the
mediator resolves the name, checks the resolved address against the declaration and the private
ranges, connects, and passes the connected descriptor back over the channel. A rebinding answer is
refused at the re-check.

Topic sentences: (1) cloud egress by declared host and port (7.25); (2) the home network behind a
separate and more explicit permission, TCP and UDP, the address pinned to one the mediator observed
answering (7.40, 7.41); (3) the multicast-loopback correction that made the ordinary HTTP client work
at all, in one sentence pointing to §12.2; (4) OAuth refresh inside the sandbox: the new token never
leaves it (7.42).

## 9.6 Identity and the record (≈300 words)

> *A decision is attributable only if the record names which code made the request and cannot be
> altered afterwards without detection.*

**Figure 9.5 — The audit record (new).** Records chained by hash and, separately, by a keyed MAC;
what each detects (reordering or deletion; forgery by someone without the key); the run record that
binds an identity to a sandbox. Identity as three hashed components (code, manifest, resolved
dependency versions), computed once per sandbox (5.12.1–5.12.2). What is recorded and what is not:
decisions, not consequences (5.12.3).

## 9.7 When something fails (≈300 words)

> *The framework fails closed, and when it stops an integration it tells the household in plain
> language and offers one action that cannot widen anything.*

Topic sentences: (1) the mediator unavailable: requests fail and nothing falls back to direct access
(5.11.5); (2) the refusal flood: 100 refusals in 10 s stop the sandbox, one record, a Repairs issue
in (A) with one Restart button that restores the same permissions and never more (7.44); (3) the
supervisor keeps an integration running across restarts (`supervise.py`); (4) one limitation: a
restart cannot reuse `/sandbox/data` (§14).

## 9.8 What the architecture does not do (≈200 words)

The inherited limits in one table: three from the platform (5.15.3) and the component nothing checks
(5.15.4). Plus three stated in this rewrite: service data given as a dict is still dropped (F54),
three declarable operations are recorded but not acted on (F50), and a command in a sandbox's first
second has no effect (F53). Each points to §14.

**Total ≈2,800 words** against 2,600. The 200 words come out of 9.4 and 9.5 at drafting, not by
dropping a component.

## Figures

All five are new, generated from source in `figures/` like Figures 4.1 and 5.1 (a Python script
writes the SVG, so the figure cannot drift from its description). Proposed: plain boxes and arrows,
greyscale, labels in words rather than colour, as Figure 4.1's script argues.

**Found while mapping:** Figure 5.1 (which belongs to §8) draws TB2 as **UNCHANGED** ("the mediator
holds as unscoped a credential as an integration holds today"). Since F45, the mediator runs as a
non-admin user, so that boundary did change. Figure 5.1 and R3's rating need updating in the §8 week,
as the carried-in item "re-rate R3 after F45" already says.

## Decisions for Younes

**Decided 2026-10-10: organise by the life of a request.** Figures: the five proposed, unless Younes swaps one.

1. **Organise by the life of a request (proposed), or keep the four-decision structure of the
   draft?** The proposal moves the decisions into Table 9.1 and gives the space to what was built.
2. **Five new figures.** Is that the right set, or would you rather swap one (for example, a
   deployment view of the Pi with (A), the mediator and the sandboxes as processes and users, in place
   of Figure 9.2)?

## Progress

**2026-10-10: prose drafted** (`submission/09_system_architecture.md`; the 2026-09-08 draft is replaced
and recoverable from git). 2,826 words of prose against 2,600; over in 9.2 (566 vs 400) and 9.4 (609 vs
450), to trim after Younes's review, not before. Checked against source while drafting: seven
namespaces, not six (`namespaces.py`: cgroup too); default limits 640 MB / 64 processes / 64 MB
(`cgroup.py`); seccomp deny-list groups (`seccomp.py`); egress order (`egress.py`); F50's three
operations are `event.fire`, `event.subscribe`, `config_entries.list` (`entities.write` is performed);
flood limit 100 in 10 s (`mediator.py`); the non-admin mediator still controls every entity (§7.45.11).

**References owed** (provisional numbers; the list is rebuilt in week 5): [33] namespaces(7), [34]
seccomp(2), [35] the Linux kernel's cgroup v2 documentation, [36] unix(7) (socket pairs, `SCM_RIGHTS`). Added 2026-10-10 with §9.2's mount explanation: [37] chroot(2) (not for security; the `mkdir foo; chroot foo; cd ..` escape), [38] pivot_root(2), [39] user_namespaces(7) (full capabilities in a new user namespace). [35] also carries the cgroup common-ancestor rule (cgroups(7) states it too).
[29]–[31] (Jiang et al.; CC FAU_STG.4; NIST SP 800-53 AU-5) are the working report's numbers.

**2026-10-10: figures drawn.** `figures/fig_9_1_system.py` … `fig_9_5_record.py` write the SVGs, through one shared renderer (`figures/svg9.py`). Checked against code while drawing: the supervisor is in the mediator's process (`supervise.py` builds the `Mediator`), so Figure 9.1 draws one framework process; `confine-mediator` is a Home Assistant user, not a Linux user, and the 9.1 caption now says so; the seccomp deny-list includes `bpf`, `unshare` and `setns` and fails with `EPERM`; the egress placeholder is from 240.0.0.0/4; the broker also refuses multicast and unspecified addresses; an egress decision is recorded before step 2 and a refusal at step 3 is recorded too; clauses are JSON pointers (`/permissions/services/call/0`). Previewed with a scratch rasteriser (no cairosvg here, so no PNGs are committed).

**2026-10-10: Table 9.1 became four paragraphs** (Younes asked, so readers get the reasoning with its context). The containers argument now says what a container is; the scope argument rests on the platform's own boundary: [10] excludes "attacks that require the user to install a malicious other software, like a third-party integration" (checked on the live page 2026-10-10), plus the components the mediator acts through. Old Tables 9.2/9.3 are now 9.1/9.2. Prose is about 3,470 words by a line count that excludes tables, captions and headings, so the trim after review must be larger, about 850 words.

**2026-10-10: §9.2 explained, at Younes's request.** `pivot_root` versus `chroot` now has its own paragraph (what each changes, the escape, why the sandbox holds the capability, the detached old root); the control-group tree is defined where the slice first appears, and the delegation paragraph explains systemd's ownership, delegation and the common-ancestor rule. Each claim checked against the man pages. Prose grows by roughly 400 words.

**F57 (2026-10-10):** §9.3's "used only after the user confirms it" overstates the code (no approval gate). Younes chose to gate both provenances; the fix waits until his §9 review is complete. Reword 9.3 to the built behaviour after the fix, and add F57 to Table 9.2 only if it is not fixed.

**Next:** Younes's review of §9 and the five figures (collect all feedback), then F57, then trim.
