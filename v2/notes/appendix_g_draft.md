## Appendix G — Manifest schema

This appendix specifies the `permissions` block that Section 9.3 introduces, as the framework's parser (`framework/confine/manifest.py` at the final tag) reads it. Its purpose is to let a reader check two properties the body relies on: that a manifest grants nothing it does not state, and that every decision the mediator records can be traced to one clause.

### G.1 Where a manifest is read

A manifest is read from one of two places, and the place records who wrote it. If the integration's own `manifest.json` contains a `permissions` key, that block is used and is marked as declared by the author. Otherwise the framework reads a file named `<domain>.permissions.json` in the folder that holds the integration, which only the installation can place there, and marks it as derived. If neither exists, the integration runs with no mediated capability at all. In every case the block must state `"schema_version": 1`, and no grant takes effect until a person has approved it for the integration's current identity (Section 9.3).

### G.2 Capabilities and clauses

The block has eight top-level capabilities. Seven grant something, and one, `resources`, bounds the sandbox. Table G.1 lists every member the parser accepts. A capability or member that is not in the table is a reason to reject the whole manifest rather than to ignore the key, because an ignored key would leave a manifest written for a later schema silently under-enforced.

**Table G.1 — The `permissions` block**

| Capability | Member | Value | What it grants |
|---|---|---|---|
| `entities` | `read`, `subscribe`, `write` | A list of `domain.object_id` patterns. An object part of `*` matches every entity of that domain; the domain is always required and is never a wildcard | Mirroring an entity's state into the sandbox, once or on every change; setting the state of an entity the integration does not own |
| `services` | `call` | A list of `domain.service`, matched exactly; no wildcard is accepted | Calling one named service |
| `events` | `subscribe`, `fire` | A list of event types, matched exactly; no wildcard is accepted | Permitted and recorded, but no action is taken (F50) |
| `network` | `egress` | A list of `host:port`, matched exactly, with an IPv6 literal written in brackets; no wildcard is accepted | A connection to one host and port on the internet, resolved and pinned by the mediator (Section 9.5) |
| | `local` | `{"tcp": [ports], "udp": [ports]}` | A port on the home network, at an address the mediator pins |
| | `discover` | `{"listen": [ports], "scan": [ports]}` | Discovery of devices on the home network by broadcast |
| | `allow_private` | A boolean, superseded by `local` | Nothing; accepted so that a manifest written against the earlier schema still parses |
| `files` | `read`, `write` | A list of paths | Validated as described in G.3, but not mounted into a sandbox the supervisor starts (finding F63) |
| `config_entries` | `read_all` | `true` | Listing every integration's configuration entries; permitted and recorded, but no action is taken (F50) |
| `http` | `register` | A list of path prefixes | Accepted and shown at approval, but matched against no request (finding F63) |
| `resources` | `memory_mb`, `cpu_percent`, `max_processes`, `disk_mb` | Integers within 16–8,192, 1–1,600, 1–4,096 and 1–4,096 | The sandbox's limits. Without a declaration the framework's defaults apply (640 MB, 64 processes, 64 MB of disk, no processor cap), and a declaration can only lower them (F32) |

Two asymmetries in the table are deliberate. Entity patterns are permitted because an author cannot know which devices a household owns, while services and network destinations must be named exactly because an author always knows which services and hosts the integration's own code contacts. The network clauses are also split by reach: `egress` names a host, because the author knows the service it uses, whereas `local` and `discover` name only ports, because a device's address on the home network is a lease that does not exist when the manifest is written.

### G.3 Rejection at parse time

Every constraint is applied when the manifest is read, so a manifest that reaches the mediator has already been found well formed and the decision path has no error cases of its own. A manifest is rejected, and the integration receives nothing, if any of the following holds:

- it is not valid JSON, or `permissions` is not an object, or `schema_version` is not 1;
- it names a capability or member that Table G.1 does not list, or a value of the wrong type;
- an entity pattern has no domain, or wildcards the domain;
- a service, event or `egress` entry contains a wildcard, a service is not of the form `domain.service`, or an `egress` entry lacks a port between 1 and 65,535;
- a `local` or `discover` port is not between 1 and 65,535;
- a `resources` value is not an integer within its range;
- a declared path, after resolving `..` and symbolic links, is, contains or lies inside the configuration directory, its `.storage` folder or `secrets.yaml`. The same check is repeated when a grant becomes a mount, so that it does not depend on the parser alone.

### G.4 Clause pointers

Every decision carries a pointer into the manifest, in the form of a JSON pointer, and the pointer is built by whichever branch of the decision procedure decided, rather than looked up afterwards. Table G.2 gives the request operations and the clause each is decided against.

**Table G.2 — Request operations and the clauses that decide them**

| Operation | Decided against | Target |
|---|---|---|
| `entity.read`, `entity.subscribe`, `entity.write` | `/permissions/entities/read`, `/subscribe`, `/write` | The entity |
| `service.call` | `/permissions/services/call` | The service |
| `event.subscribe`, `event.fire` | `/permissions/events/subscribe`, `/fire` | The event type |
| `config_entries.list` | `/permissions/config_entries/read_all` | — |
| `network.egress` | `/permissions/network/egress` | `host:port` |
| `network.tcp.local`; `network.udp.send`, `network.udp.recv` | `/permissions/network/local/tcp`; `/udp` | The port |
| `discover.scan`, `discover.listen` | `/permissions/network/discover/scan`, `/listen` | The port |

A permitted request is recorded with the pointer of the entry that matched, such as `/permissions/network/egress/0`. A request denied because nothing matched is recorded with the pointer of the clause that held no match, so that a denial by absence is attributable rather than merely true. A request from an integration with no manifest, and a request whose operation is not in Table G.2, are denied with the reason stated. Because no branch of the procedure can return a decision without a pointer, a decision that names no clause cannot be constructed, which `selftest_policy` checks (Appendix E).

### G.5 An example

The manifest used for `midea_ac_lan` in the evaluation grants three ports on the home network and nothing else:

```json
"permissions": {
  "schema_version": 1,
  "network": { "local": { "tcp": [6444], "udp": [6445, 20086] } }
}
```

Read through Table G.1, it lets the integration exchange datagrams with a device on ports 6445 and 20086 and open a connection to port 6444, at an address the mediator pins when the device answers. It reads no entity, calls no service, reaches no host on the internet and runs within the default limits, all without any of that being written down.
