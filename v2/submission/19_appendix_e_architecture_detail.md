## Appendix E — Limits of the architecture

Table E.1 lists the architecture's limits, with the verification finding behind each where there is one; the findings are listed in the repository (Appendix A). None of them gives a confined integration a capability its manifest withholds.

**Table E.1**
*Limits of the architecture*

| Limit | Kind | Consequence |
|---|---|---|
| The kernel is the boundary | Inherited | A kernel exploit escapes every sandbox; a stronger primitive is the deployer's choice and the architecture does not prevent one |
| The memory controller is off by default on the reference device | Inherited | A precondition on deployment; the framework refuses to start without it |
| The mediator's user still controls every entity | Inherited, narrowed | A compromised mediator can operate any device, though no administrative function. Future work: the platform's policy engine can express a per-entity policy, and its auth store loads custom groups, but nothing in its interface creates one; a supported policy limited to the entities the installed manifests name would bound the mediator to their union |
| The supervisor is trusted and checked by nothing in the design | Structural | It runs once per sandbox, off the request path and unprivileged, which bounds it without removing it |
| A local network clause reaches any home-network host on its port | Design | An integration granted a port can reach every device that answers on it |
| A service-call value that is itself a set of named fields is not forwarded | Implementation | Plain values and lists cross; a nested value reaches the platform without it (finding F54) |
| Five declarable clauses are accepted but not acted on | Implementation | `events.fire`, `events.subscribe` and `config_entries.read_all` are permitted and answered, and nothing acts (finding F50); a `files` grant is validated but not mounted, and `http.register` is matched against no request (finding F63). Each fails closed |
| A command in a sandbox's first second has no effect | Implementation | It is recorded as permitted and is lost (finding F53) |
| Any administrator of (A) can approve a grant | Design | A compromised administrator account can approve a wider grant, but such an account already controls every device in the house. Home Assistant admits only administrators to a Repairs action (Home Assistant, 2026a) and does not tell the action which administrator took it, so the record names the role |
| An integration that logs in through OAuth cannot be set up under the supervisor | Implementation | Its first login needs a person's browser (Hardt, 2012); once it is set up, its entry and token survive restarts |
| The kept data store is checked against its limit only at start | Implementation | Within one run it can grow past the limit, and the next start refuses |
