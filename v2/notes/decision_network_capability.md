# Decision — the network capability, redesigned against measurement

**Written 2026-09-03**, before the egress proxy is built. Supersedes §5.10.3's one-line
`network.egress` row. Evidence: §7.24 (`experiments/egress_shape/`), `results/udp_demand.md`,
`results/broadcast_fallbacks.md`.

§5.10.3 gave outbound network a single clause — a list of hostnames, "resolved and pinned by the
mediator", with a separate flag for non-public destinations. Measurement found that clause wrong
in four ways, and the corrections do not fit inside one list. This note fixes the capability.

---

## 1. What the measurement forced

| Finding | Consequence for the clause |
|---|---|
| ~~96%~~ of name resolution goes through `aiodns`, and the name does not survive to `connect` (§7.24.2) — *2026-10-03, §7.31.11: the 96% was the platform's `dhcp` LAN sweep; four of six integrations' own API names go through `aiodns`, two through `getaddrinfo`, so both seams stand* | the enforcement point is the resolver, and a placeholder address carries the name to the connection |
| Ports 443, 8123, 6445, 20086, 5000 all reached (§7.24.3) | a host without a port grants **all 65,535 ports** on that host |
| 15 of 75 integrations need UDP (`udp_demand.md`) | TCP-only costs 20% of the corpus |
| `localtuya` **listens** rather than broadcasts; `govee` needs a multicast **join**; three others broadcast (`broadcast_fallbacks.md`) | "discovery" is three capabilities, not one |
| A device's address comes from the user's DHCP lease | the author cannot declare it, and must not be asked to |

---

## 2. The governing rule, which already existed

§5.10.4 fixed the test when it argued about services and entities:

> Requiring exactness where it is knowable and permitting patterns where it is not is what keeps
> the manifest writable.

Applied here, it splits the declaration cleanly in two, and the split is the whole design:

| | Knowable at authoring time? | Who supplies it |
|---|---|---|
| A **cloud host** — `api.pirateweather.net` | yes; it is a constant in the source | the **author**, exactly |
| A **protocol port** — 48899, 6666, 6445 | yes; it is a constant in the source | the **author**, exactly |
| A **device address** — 192.168.1.50 | **no**; it is a DHCP lease | the **user**, at configuration time |

So the manifest declares the *shape* of the integration's networking, which its author knows. The
*instance* — which machine — comes from the user, who is the only party that has it. The mediator
pins the binding between them.

**Nothing new is asked of anyone.** The user already types the device address into the config
flow today; the author already writes the port into the source today.

---

## 3. The four capabilities

`network.egress` becomes four clauses, because they differ in reach and therefore in what a user
is being asked to consent to.

### 3.1 `egress` — a named host on the internet

```json
"egress": ["api.pirateweather.net:443"]
```

Exact host **and port**, no wildcards. Wildcards are refused for the reason §5.10.4 refuses them
in `services.call`: the author knows their API hosts because they are written into the code, so
exactness is knowable and therefore required. A suffix pattern would grant every present and
future subdomain, including ones that do not exist yet.

Ports are required. `api.example.com` alone is not a grant of "the web"; it is a grant of every
port on that machine.

### 3.2 `local` — a device the user configured

```json
"local": { "tcp": [6668], "udp": [6445, 20086] }
```

Declares the **ports the integration speaks**, never an address. An address enters the permitted
set only by §4's binding rule below.

### 3.3 `discover.listen` — passive

```json
"discover": { "listen": [6666, 6667] }
```

Bind a port and hear devices announce themselves. **Sends nothing and reaches nothing** —
`localtuya`, one of the most-installed integrations in the corpus, needs only this. It is the
quietest capability in the schema and should be presented as such.

### 3.4 `discover.scan` — active

```json
"discover": { "scan": [48899] }
```

The **mediator** broadcasts the integration's payload on the declared port and returns what
answers. The integration never holds a socket that can reach the network.

Multicast group membership (`govee`'s `239.255.255.250`) is served by the same mechanism and needs
no separate clause: the mediator joins, collects, relays.

---

## 4. The binding rule — how an address becomes permitted

> **An address may be pinned only if the mediator has observed it responding on a port the
> manifest declared.**

One rule, covering all three ways an address can arrive. Measured over the 1,482 integrations
Home Assistant ships: 21% declare automatic discovery, 22% carry a host or IP field, 12% do both,
and **69% involve no address at all** — they are cloud accounts.

| Source | How the rule is satisfied | Cost |
|---|---|---|
| **Platform discovery** — zeroconf (111), dhcp (110), bluetooth (53), ssdp (43)… | Home Assistant core observed the device and *tells* the integration the address; the integration does not invent it | none |
| **Mediated discovery** — `discover.scan` or `discover.listen` | the mediator performed the scan or relayed the listen, so it saw which addresses answered | none — the data is already in hand |
| **Manual entry** — 152 integrations with no discovery at all | pinned on first successful connection to a declared port | small |

The first draft of this section said instead that *"no address enters the permitted set except
through a user action"*, and that was the wrong rule: the config flow is the integration's own
code, so "the user acted" really means "the integration's own interface reports that the user
acted." The observed-responder rule replaces an assertion about consent with an observation the
mediator makes for itself.

### 4.1 What that makes the ceiling of `scan` — corrected

**The first draft of this section claimed more than it could support**, and the sentence is
withdrawn rather than softened:

> ~~No declaration of `scan`, however broad, can produce a connection.~~

That was false. An integration declaring `scan: [80]` can find a device that answers on 80 — the
router's web interface, say — and then present it through its own config flow as the device the
user is setting up. The address was genuinely observed responding on a genuinely declared port, so
the binding rule is satisfied and the pin is legitimate by every check the mediator can make.

What survives is narrower and true:

- an address must have **answered on a declared port**, so a machine that does not speak the
  integration's protocol cannot be pinned merely by naming it;
- the reachable set is **one address at a time, on declared ports**, recorded in the audit log
  together with the source of the pin.

### 4.2 The residual is T13, which Chapter 4 already retains

The remaining exposure — an integration misrepresenting, through its own interface, what the user
is consenting to — is not a new threat. It is **T13**, *"the declaration accompanying an
integration misrepresents its behaviour"*, which §4.10 rates 16 High and treats as **Retain
(partially): declaration made visible; enforcement bounded to it** (F4, R1).

Rated the way Chapter 4 rates everything, this instance lands around impact 3–4 (A8 — *"extends
reach without itself being a loss"*) and likelihood 2–3: it needs a hostile integration, a
completed setup, **and** something exploitable at the pinned address. Medium. It is not a design
driver, and a confirmation surface was considered and **rejected as scope creep against a threat
the register already prices**.

**Reported against the baseline, as every security result in Chapter 7 is.** In unmodified Home
Assistant an integration reaches any address on the home network with no declaration, no pinning,
no observation and no record. Under this design the worst case is one address, on ports declared
in advance, observed behaving like the declared protocol, and logged. The residual is real; it is
not the comparison.

---

## 5. What the mediator enforces, and by what means

The distinction that matters to this project is whether a control is **structural** — a property
of the thing — or **procedural** — a check that could be written wrong.

| Capability | Mechanism | Structural? |
|---|---|---|
| `egress` TCP | mediator resolves, checks, connects, passes the connected descriptor back | **Yes — verified.** The peer cannot be changed |
| `local` TCP | same | **Yes — verified** |
| `local` UDP unicast | **relayed over the channel** — *not* a descriptor | Yes, from the sandbox's side: it holds no socket |
| `discover.listen` | relayed | Same |
| `discover.scan` | relayed — the mediator broadcasts and returns replies | Same |

### 5.1 The rule, and the assertion it replaces

**This section originally said the opposite, and the error was worth catching.** The first draft
handed a *connected UDP socket* to the sandbox and claimed the kernel would pin its peer the way
it pins a TCP one. `selftest_socket_pinning.py` was written to check that claim and disproved it,
on x86_64 and aarch64 alike:

| | connected TCP | connected UDP |
|---|---|---|
| `sendto()` naming another address | address **ignored**; data reaches only the pinned peer | **delivered to the other address** |
| a second `connect()` | refused, `EISCONN` | — |
| inbound from a non-peer | — | dropped |

An integration granted UDP to one lamp would have been able to send a datagram to **every host on
the home network** — T10, delivered by the control written to prevent it. The mediator's check
would have happened and then stopped mattering.

So the rule is narrower than the first draft's, and it is now evidence rather than assertion:

> **Descriptor passing is safe only for TCP, because only TCP refuses to be re-pointed.
> Every UDP path — unicast, listening, discovery — is relayed through the mediator.**

Two further reasons the receive-shaped capabilities could not have been handed over anyway: a
socket bound to `0.0.0.0:6666` to hear announcements can also *send* anywhere, as can one joined
to a multicast group. Listening is not a weaker capability than sending when it arrives as a
descriptor — it is the same descriptor.

Relaying costs a copy per datagram, and §7.19 answers the performance objection in advance:
mediation runs at 0.009% utilisation at the 26-sandbox budget, with three to four orders of
magnitude of headroom.

**The connected UDP socket is still used — on the mediator's side.** Its inbound filter is real,
so the mediator's own socket drops datagrams from anyone but the pinned peer, and the relay never
sees traffic it would have to filter in software.

### 5.2 Where the trust actually sits

The integration's capability is structural in every row. The *mediator's own* correctness is
procedural — it decides what to broadcast and where. That is not a weakening: §5.15.4 already
names the supervisor and mediator as the components nothing checks, and this design keeps every
procedural decision on the trusted side of that line.

---

## 6. What the user reads (F4)

The manifest is machine-checkable; `describe.py` is what a person evaluates. The user should
never need to know what 48899 is — the same way they never need to parse
`sensor.outdoor_temperature`.

| Clause | Rendered |
|---|---|
| `egress` | "contact **api.pirateweather.net** on the internet" |
| `local` | "contact **the device you set up**, and nothing else on your network" |
| `discover.listen` | "watch for its own devices announcing themselves" |
| `discover.scan` | "**search your home network** for its devices" |

The four sentences are deliberately of different loudness, and the ordering is the point: watching
is quieter than searching, and searching is the one that touches every machine in the house. A
non-expert can rank those without knowing what a port is, which is what F4 asks for and what a
single `network` permission could not have delivered.

Denials render at the same weight as grants, per F4 — an integration with no `discover` clause
shows "will not look for devices on your network."

---

## 7. Clause pointers (F3)

Every decision names the clause that produced it:

| Decision | Pointer |
|---|---|
| permitted cloud host | `/permissions/network/egress/0` |
| permitted device port | `/permissions/network/local/udp/1` |
| permitted scan | `/permissions/network/discover/scan/0` |
| denied by absence | `/permissions/network/discover` |
| denied by rule — broadcast requested directly | the rule, not a clause |

`discover.scan` additionally writes an outcome record — *"scanned port 48899, three responses"* —
because a capability that touches every device in the house should be attributable after the fact,
which is S7 and T18.

---

## 8. Residual risks, for Chapter 8 and for §4.11

Stated here so they are chosen rather than discovered.

1. **`discover.scan` maps the home network.** The integration learns what hardware is present, and
   can exfiltrate that map through its permitted `egress` — which is T09, already retained as
   structural. A8 is rated Moderate and Chapter 4's own wording is *"extends reach without itself
   being a loss."* This is the clearest case of that sentence being load-bearing.
2. **A one-shot payload reaches every listener on the scanned port.** Broadcast is connectionless,
   so this cannot become a session — but a device with a pre-authentication UDP defect is exposed
   to one datagram. The mediator bounds the rate and duration; it cannot make the datagram safe.
3. **The shim depends on Home Assistant's choice of DNS library.** If `aiodns` is replaced,
   honest integrations lose network access until the shim is updated. The failure direction is
   compatibility, never containment (§7.24.6).
4. **`govee`'s firmware split.** Some firmware answers a scan by multicast; the relay handles it,
   but this was the one case in 75 that unicast-only could not have served, and it is why the
   relay exists rather than descriptor passing alone.
5. **Undeclared UDP is invisible.** `udp_demand.md`'s 20% counts declared requirements only, and
   §6.13.3 found 16% of the corpus imports packages it never declares.
6. **Relayed UDP is procedural where handed-over TCP is structural.** §5.1's rule means the UDP
   destination check lives in the mediator's code rather than in the kernel. That is a real
   asymmetry between the two transports and it should be stated as one: TCP's guarantee survives a
   bug in the mediator's relay loop, UDP's does not.

---

## 9. What this changes in Chapter 5

Chapter 5 is **not edited to be right** — §5.10.3 keeps its text and carries the correction block
added on 2026-09-03, as §5.6.5 and §5.7.4 do for Chapter 6's corrections. This note is the design
Chapter 6 implements and Chapter 7 evaluates against §7.5's pre-registered F2 and S4 rows, which
are frozen and not being revised.

The one place Chapter 5's *argument* is extended rather than corrected is §5.10.4. Its rule —
exactness where knowable, patterns where not — was written about services and entities and turns
out to decide the network clause too, which is the strongest available evidence that the rule was
the right one rather than a rationalisation of two particular cases.

---

## 10. Open, and deliberately

- **How many devices may be pinned.** A count (`"devices": 1`) was considered and dropped: the
  provenance rule in §4 is a stronger bound than a number, because every pinned address traces to
  a user action regardless of how many there are. If a count is wanted later it is additive.
- **Whether `discover.listen` needs a rate bound.** It receives only, so it cannot flood anything
  outward; the risk is the sandbox's own memory, which S9's `memory_mb` already bounds.
- **IPv6 link-local.** Not observed in the sample. Not designed for, and said so rather than
  assumed absent.
