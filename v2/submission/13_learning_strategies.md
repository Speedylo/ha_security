# 13. Learning Strategies

## 13.1 Tackling complexity through targeted research

The project's hardest constraint was identified by reading rather than by building. **One published
result — an integration walking the Python garbage collector into another integration's live
objects [9] — eliminated an entire class of designs before any code existed.** Had that paper been
skimmed rather than read in full, the obvious first implementation would have been an in-process
API wrapper, and it would have been unsound in a way no test the author wrote would have revealed.

The strategy generalised into a rule: **read the closest prior work completely, and characterise it
precisely enough that its limits become your requirements.** Four requirements in this project
derive from limitations *in* prior work rather than from the problem statement — including the one
that forced the architecture, and the one about per-integration attribution that distinguishes this
design from the closest published alternative. That return only arrives from reading carefully
enough to distinguish what a paper *recommends* from what it *builds*.

The same discipline was applied to the platform. Where a claim about Home Assistant's behaviour was
load-bearing, it was **re-derived from the platform's own source** rather than taken from
documentation — which is how the measurement in §9.2 was produced, and that measurement reversed
the design decision it was run to inform.

## 13.2 Building expertise through practical experimentation

Several conclusions in this report contradict what was believed before the measurement, and each
was reached by building the smallest experiment that could settle the question.

**The habit that produced the most value was measuring the thing rather than reasoning about it.**
Whether a stripped platform fits on the target device was not argued from component sizes; it was
measured across six live sandboxes by proportional set size, because the obvious method —
subtracting two resident-set figures — is arithmetically wrong for shared pages. Whether the kernel
offered the primitives the design assumed was not read from documentation; it was probed on the
device, and the probe found two facts that changed the deployment story.

**Six of eight predictions registered before measurement were wrong.** Registering them was
uncomfortable and it is the single practice most worth carrying forward: a prediction that cannot
be wrong teaches nothing, and the pattern in *which* ones were wrong — every incorrect prediction
was about the world, none about the design — is a result the project could not otherwise have
stated.

## 13.3 Independent troubleshooting and system adaptation

The most instructive failure in the project arrived last. **A real community integration, run
confined against its own real API, could not construct an HTTP client inside the sandbox at all** —
because the platform's recommended helper builds its resolver by instantiating a service that joins
a multicast group, and a fresh network namespace's loopback carries no multicast flag.

The diagnosis required working down through four layers that each looked like the answer: an
opaque client-session error, a resolver constructor, a Zeroconf multicast join, and finally a
kernel interface flag. **The fix then failed on the first attempt**, because setting the flag is not
sufficient: an unbound multicast join resolves its interface from the *routing table*, and a fresh
namespace has no route for the multicast range at all. Only measuring both join paths separately —
via a specific address, and via `INADDR_ANY` — distinguished the two.

**What that episode taught is not about multicast.** It is that the design had been unusable for
41% of its target population, for as long as it had existed, **behind nineteen self-test suites
that all passed** — because every earlier test subject had been written by the author of the
sandbox, and none of them called the helper the platform tells real authors to call.

A second instance of the same lesson had already occurred. Writing an *attack* against the egress
broker — rather than a test of it — found that the broker read a security-relevant flag from the
sandbox's own request. A hostile integration could have granted itself the whole of a Critical
threat's reach by writing one key into a message it already composed. **That was a defect in the
artifact, and it was found by adversarial construction rather than by review.**

**Two instances is a pattern**, and it is the argument for the next stage of work being to run the
whole system for real rather than to write more tests out of the same assumptions.

## 13.4 Managing knowledge acquisition and technical breadth

The project required working competence in areas that do not usually meet: Linux kernel isolation
interfaces, Python interpreter internals, a large third-party codebase, risk-management process,
and empirical evaluation design. Three strategies made that manageable.

**Write the constraint down before acquiring the knowledge.** Every requirement states how it will
be verified, before any implementation existed. That kept learning directed at questions the
project actually had, and it is why the evaluation could not be fitted to whatever the
implementation turned out to do.

**Prefer one mechanism understood completely to three understood partially.** The framework uses
only the standard library and `ctypes` — no container runtime, no third-party sandboxing library.
That was slower, and it means every security property in this report is one the author can explain
down to the system call.

**Keep a record that can correct you.** Superseded text was never edited to be right; it kept its
original wording and gained a dated pointer to the correction. Over the project this produced
something more useful than tidy prose: an auditable record of what was believed before each number
arrived. **Across four chapters and three full read-through passes, every correction has been to a
sentence standing next to a measurement, and none to a measurement itself** — which has a plain
explanation worth carrying into any future project:

> A number here is produced by a harness that is itself tested. A sentence about a number is
> produced by an author writing at the end of a long day. **The measurements had mechanisms that
> caught their errors. The prose had only a read-through.**

## 13.5 The five mechanisms, ranked by what each caught

The most transferable output of this project is not the artifact. It is the ranking below, which is
what the record above supports:

1. **A paired baseline** stops misattribution — it corrected three claims in this project, every
   one of them in the direction of charging the design *more* than it deserved.
2. **Two instruments bounding each other** catch counting errors — the same class was caught twice,
   and the second time the error was in the cross-check rather than in the instrument it checked.
3. **A self-test that passes when the surprising thing is true** freezes a fact that would
   otherwise be silently invalidated by a future change.
4. **Recomputing a figure from the recorded results** checks a sentence against its source rather
   than against another sentence. Three times, a recount was wrong and the report was right — which
   is why a disagreement is treated as a question until the field being counted is confirmed.
5. **Running unmodified real code finds what none of the other four are looking for**, because the
   other four are written out of the same assumptions as the thing they test.

The fifth is also the most expensive, which is why it happened last — and why the future work in
§14 is ordered the way it is.
