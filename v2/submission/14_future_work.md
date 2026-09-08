# 14. Future Work

Ordered by what each would settle rather than by effort, with the effort stated so the ordering can
be argued with. **Every item is one change to one artifact; none is a wish.** The order was revised
once by evidence: running a single real integration promoted the network-stack item from nowhere to
sixth, which is what evidence is supposed to do to a plan.

| | Work | What it settles | Cost |
|---|---|---|---|
| **1** | **The push loop** | S3's subscription half moves from a refusal to a demonstrated filter, and the one latency path that could consume the 63× margin becomes measurable. Both are currently gaps in the artifact rather than in the measurement | **Days.** The largest missing piece and the highest-value one |
| **2** | **The real Home Assistant component** | The mediator's far side is a stand-in, so what a *live* instance does with a mediated write is untested. What this settles is **entity identity, not realism**: publishing over the states API produces states with no registry row, and **83% of community integrations publish by the path that creates one** | **Days** |
| **3** | **Static analysis for a derived manifest** | The undeclared-package *and* undeclared-component bound — the only measured compatibility cost in the whole report. A top-level import is trivially detectable, and a component dependency is a name in the platform's own source, so the closure is computable **exactly** rather than approximated | **Days** |
| **4** | **The one unevaluated threat** | The only threat in either register with no evidence at all. Set an integration up, change its manifest, spawn it again, and show the second run is bounded by the second declaration and that the change is visible before it takes effect | **Hours.** It was never scheduled, which is why closing out the schedule did not catch it |
| **5** | **Re-run the API-surface parser on the uniform corpus** | The other half of contribution 1 — what most *integrations* ask for, against what most *installations* run | **One run.** The script exists and the corpus is fetched: **the cheapest outstanding item in the report** |
| **6** | **The other two network stacks, confined** | A synchronous HTTP stack and a raw socket, each spawned in real namespaces against a real destination. **Promoted by §12.6's result:** the one stack actually spawned turned out to break, so "the other two are presumably fine" is exactly the reasoning that was wrong once | **Days**, and may need recorded fixtures |
| **7** | **asyncio datagram transports, and a confined UDP round trip** | The unserved quarter of datagram integrations, and whether relayed UDP behaves in real namespaces as it does against the decision path | **Days** |
| **8** | **Filesystem quota for the sandbox's writable directory** | An integration can currently fill the user's disk through its own data directory. Needs privilege, so it also needs a decision about whether the design's unprivileged position admits a privileged installer step | Small, plus a design decision that is not small |
| **9** | **The end-to-end arm at scale** | The compatibility number at the level that matters, as something other than a named set of five. **Blocked on credentials for 26 of 37**, so it needs a cooperating vendor set or recorded request fixtures | **Weeks**, and the honest framing is that this is a different project's measurement |
| **10** | **Off-box audit anchoring** | The audit log's authority against whoever controls the machine. The contribution here is that **the artifact already emits the record such a layer would consume** | A different project |
| **11** | **Enforcement inside the platform's own loader** | The better design on every axis except deployability. **Not this project's to do, and that is why it is last rather than absent** — but a platform proposal must answer what confinement costs, what the declaration should express, and which threats it closes, and those answers do not depend on the architecture that produced them | Upstream |

## 14.1 The next engineering work, and why it is a composition rather than an item

The list above prices the pieces separately, and that framing **understates them**, because what
has never happened is all of them at once: a real Home Assistant, real integrations at volume,
executed rather than merely imported, with the durable audit log actually engaged.

| Part | Where it stands |
|---|---|
| A real Home Assistant | **Never.** The mediator's far side is a stand-in |
| Real integrations | **Partly.** 77 at import; **5** executed; **1** against a real API |
| A large sample, executed | **n=5**, with a ceiling of 11 |
| The logging mechanism, engaged | **One run of about eight.** Every other experiment recorded to an in-memory list |

**The logging half is the sharpest of the four, and it has no home in the report's own limitations
until now.** The mechanism is built and its properties are demonstrated — both chains fail
independently, tamper, delete and reorder are all detected, durability is measured. What is *not*
demonstrated is the mechanism running underneath the evaluation. **And the one time it did run for
real, it produced three defects in a single session:** the log was created inside a directory the
harness deletes, so the run reported no decisions at all; the destination evidence was read from a
structure that does not carry the request, so every destination read as empty; and the log recorded
an egress target as a host **without its port**, so it could not distinguish a grant of 443 from
one of 6445 on the same machine.

**This is §13.3's lesson arriving a second time on a different component**, and it is the argument
for the composition being *the* next work rather than one of eleven ranked items.

**The cheapest first move is not the big run:** wire the durable log into the other experiment
harnesses. It is a small change to code that already exists, requires no new measurement, and on the
evidence above it is likelier to find something than to confirm something.
