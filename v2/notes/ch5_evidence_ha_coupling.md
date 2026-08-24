# Evidence — how an integration is coupled to Home Assistant's process

**Derived:** 2026-08-24 · **Working note, not a report chapter.** · **Discharges:** item 1 of
`00_METHOD.md` §2 ("Integrations cannot run outside HA's process — read HA's bootstrap;
show the coupling"). · **Feeds:** Ch. 5 (architecture), Gate G2, Ch. 4 §4.6 figure.

## 1. Question, and why it is asked here

Chapter 3 deferred a question to Chapter 5: **how does an unmodified integration run
outside the process it expects?** That question presupposes an answer to a prior one —
*what, exactly, does an integration expect?* Until the coupling is described from the
source, "run it elsewhere" has no defined content, and any architecture proposed in Ch. 5
would be resting on an assumption rather than on evidence.

The evidence rule (`00_METHOD.md` §2) makes this mandatory rather than optional. The
first pass already established that integrations cannot be relocated naively. That is
private knowledge: it says the trap exists, and it is not citable until re-walked here.

## 2. Method

Static reading of the Home Assistant source, following the control flow from process entry
to the moment third-party code is called. No instrumentation, no running instance — the
claims below are all about *what the code does*, and every one is anchored to a line that
can be re-read.

**Source under examination:**

| | |
|---|---|
| Repository | `home-assistant/core` |
| Version | **2026.8.3** (`MAJOR/MINOR/PATCH_VERSION`, `homeassistant/const.py`) |
| Commit | `759e4658f40b3ccb671d418b8a0ed95224bf4561`, dated 2026-08-21 |
| Obtained | `git clone --depth 1 --branch 2026.8.3` on 2026-08-24 |
| Location | `~/ha-src/core` — **outside** the capstone repository, so it is never committed and never confused with the frozen spike |

Line references below are `file:line` **at that commit**. They will drift in later
releases; the commit hash is what makes them checkable.

**Scope limit, stated up front.** This is the *startup and dispatch* path. It establishes
what an integration is handed and in what process it runs. It does not enumerate every
capability reachable from those handles — that is Ch. 4's work, already done, and §5 below
only connects the two.

## 3. The chain, from process entry to third-party code

**1 — One process, one interpreter, one event loop.**
`__main__.py:213` calls `runner.run(runtime_conf)`. `runner.py:287` creates a single event
loop and `runner.py:290` drives the whole system with
`loop.run_until_complete(setup_and_run_hass(runtime_config))`. That coroutine
(`runner.py:255`) calls `bootstrap.async_setup_hass(runtime_config)` at `runner.py:257`.
There is no fork, no subprocess, no worker pool for integrations anywhere on this path.

**2 — One `HomeAssistant` object, constructed once.**
`core.py:381` defines the class; `core.py:404–425` its `__init__` builds the object that
becomes the whole system's root: `self.data`, `self.loop`, `self.bus`, `self.services`,
`self.states`, `self.config`, `self.import_executor`, `self.timeout`. Three more are
declared at class level (`core.py:384–386`) and assigned during bootstrap: `auth`, `http`,
`config_entries`.

**3 — Integrations are discovered as directories and imported as Python packages.**
Custom integrations are found by importing the `custom_components` package and listing its
subdirectories (`loader.py:305–331`). Each becomes an `Integration` object holding a
`pkg_path` (`loader.py:774`) — for a custom integration, `custom_components.<domain>`.

**4 — Loading is `importlib.import_module`, and nothing else.**
`loader.py:1091`:

```python
cache[domain] = cast(ComponentProtocol, importlib.import_module(self.pkg_path))
```

The docstring above it (`loader.py:1076–1078`) says so plainly: *"This is mostly a thin
wrapper around importlib.import_module with a dict cache."* Platform modules
(`sensor.py`, `switch.py`, …) load the same way at `loader.py:1321`. The consequence is
the whole of the coupling problem: **third-party code enters the same interpreter, the
same `sys.modules`, and the same address space as the platform**, by the ordinary import
mechanism, with no namespace, no restricted builtins, and no separate execution context.

**5 — The live root object is handed to third-party code by direct call.**
Two entry points, and they are the only two that matter:

| Path | Call site | What is passed |
|---|---|---|
| YAML setup | `setup.py:412` — `task = component.async_setup(hass, processed_config)` | the live `hass` object |
| Config entry setup | `config_entries.py:798` — `result = await component.async_setup_entry(hass, self)` | the live `hass` object **and** the `ConfigEntry` (`config_entries.py:391`), whose `data` (`config_entries.py:397`) is where an integration's stored credentials live |

A synchronous integration is dispatched through the *shared* default executor
(`setup.py:416–418`), so its blocking code runs on a thread pool the platform also uses.

**6 — There is no confinement machinery to find.**
`grep -niE '\b(sandbox|seccomp|permission model|capability|privilege separation)\b'` across
`loader.py`, `setup.py`, `bootstrap.py` and `core.py` returns **nothing**. This is a
deliberate negative result: the absence is not an oversight in my reading.

## 4. What `hass` confers, and why the object itself is the boundary problem

The argument of §3 is not "an integration is given several powerful APIs." It is stronger
and simpler: **an integration is given the object graph's root**, and everything else is
reachable by attribute access from there.

| Handle | Reached as | What it confers |
|---|---|---|
| Shared mutable store | `hass.data` (`core.py:404`) | Every integration's runtime state, in one dict, by domain key |
| Event bus | `hass.bus` (`core.py:408`) | Fire any event; subscribe to all of them |
| Service registry | `hass.services` (`core.py:409`) | Call any service any integration has registered |
| State machine | `hass.states` (`core.py:410`) | Read and write the state of every entity in the home |
| Config, incl. paths | `hass.config` (`core.py:411`), `.path()` at `core_config.py:625` | Resolve any path under the configuration directory — where `secrets.yaml` and the credential store live |
| Auth manager | `hass.auth` (`core.py:384`) | The user and token model |
| HTTP component | `hass.http` (`core.py:385`) | Register HTTP routes on the running server |
| Config entries | `hass.config_entries` (`core.py:386`) | Every integration's stored configuration, credentials included |
| Event loop / executor | `hass.loop`, `hass.import_executor` (`core.py:405`, `422`) | Schedule work on the platform's own loop and threads |

Two structural facts compound this. First, `HomeAssistant.__new__` (`core.py:388–392`)
stores the instance in a module-level thread-local (`_hass.hass = hass`), so the root
object is reachable *without* being passed — holding a reference is a convenience, not a
requirement. Second, and decisively for Ch. 5, none of this depends on the argument list
at all: since the integration shares an interpreter, the Python object graph is a
navigable structure at runtime. This is the published `gc.get_objects()` result that
Ch. 4 already relies on (Corno & Mannella), and §3 step 4 is its mechanism.

**Restating an argument owed since §1.9:** an integration's authority here is not conferred
by any grant that could be withheld. It is a consequence of *where the code runs*. That is
why relocation is necessary — and, on its own, insufficient: moving the code without
scoping what it may then ask for simply relocates the same authority.

## 5. The built-in / custom distinction exists, and is not a privilege boundary

Worth recording precisely, because it is the obvious objection to the claim that HA draws
no line around third-party code. It *does* draw one — `Integration.is_built_in`
(`loader.py:944`), true when `pkg_path` starts with the built-in package prefix. Every
consumer of it in the platform:

| Site | Use |
|---|---|
| `loader.py:704–706` | Logs `CUSTOM_WARNING` (`loader.py:155`) — "might cause stability problems" |
| `loader.py:853` | Reports quality scale as `"custom"` |
| `loader.py:1761` | Routes the issue-tracker URL away from HA's own tracker |
| `setup.py:274` | Inserts the words "custom integration" into a setup-failure log line |
| `frame.py:288, 304` | Selects deprecation-report *severity*, and the word "custom" in the message |
| `requirements.py:273` | The word "custom" in a requirements-failure message |

Every one is **reporting**: log wording, a label, a URL, a severity. Not one gates a
capability, and the flag is never consulted on the load path (§3 step 4) or at either
dispatch site (§3 step 5). A custom integration and a built-in one are loaded by the same
call and handed the same object. Home Assistant knows which code is untrusted; it uses
that knowledge to phrase a warning.

Adjacent and worth one line, since it bears on Ch. 4's supply-chain threats: an
integration's declared `requirements` are installed **at setup time** by running `pip`
against the live interpreter (`requirements.py:190`, → `util/package.py:143–157`, which
invokes `sys.executable`). Code arrives from PyPI into the same interpreter, during
startup, on the integration's say-so.

## 6. What this settles, and what it does not

**Settled, and now citable in this pass:**

1. Integrations run in the platform's process, by construction, via `importlib`
   (`loader.py:1091`). Item 1 of `00_METHOD.md` §2 is **discharged**.
2. The coupling is not an API surface but an object reference: the root of the system is
   an argument to third-party code (`setup.py:412`, `config_entries.py:798`).
3. Authority is positional — a consequence of the execution context, not of a grant.
4. HA's own custom/built-in distinction is presentational, not enforcing.

**Not settled here, and deliberately left to Ch. 5:**

- *How* an unmodified integration can run outside this process. §4's table is the
  specification any answer must satisfy: whatever replaces `hass` has to present the same
  attribute surface, or the integration must be modified — and Ch. 3's compatibility
  constraint forbids modification.
- Which of the nine handles must be mediated, which can be denied outright, and which are
  used so rarely that denial costs nothing. That is an **empirical** question, and the
  spike's 3,105-repo API-surface measurement is the shape of the answer — to be re-derived
  in this pass, not imported.
- Who authors the manifest (Ch. 3's other deferred question). Untouched by this note.

## 7. Re-walking this yourself

Every claim above is one command away. In `~/ha-src/core`:

```bash
git log -1 --pretty='%H %ad' --date=short        # confirm the commit these lines refer to
sed -n '400,426p' homeassistant/core.py          # what the hass object is
sed -n '1085,1095p' homeassistant/loader.py      # importlib.import_module — the whole coupling
sed -n '408,418p'  homeassistant/setup.py        # hass handed to third-party code
sed -n '795,800p'  homeassistant/config_entries.py
grep -rn "is_built_in" homeassistant/*.py homeassistant/helpers/frame.py
```

The one to be able to narrate under questioning is `loader.py:1091`. Everything in §4 and
every architectural constraint in Ch. 5 follows from that single line being an ordinary
Python import.
