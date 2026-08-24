# The coupling finding, explained from the ground up

**Written:** 2026-08-24 · **Working note — for the author, not the report.**
**Companion to:** `ch5_evidence_ha_coupling.md`, which is the same finding stated formally
with line citations. This file explains the Python underneath it.

You do not need to be able to write this code. You need to be able to **say what it does
and why it matters**, out loud, when someone points at it. That is what this document is
for. Part 6 is a self-test — if you can answer those six questions in your own words, you
own this finding.

---

## Part 0 — The finding in one sentence

**Home Assistant loads a third-party integration using Python's ordinary `import`
statement, which means the integration's code runs inside Home Assistant itself, as part of
it, with the same access to everything that Home Assistant has.**

Everything below is either explaining a word in that sentence, or drawing out a
consequence of it.

---

## Part 1 — Five ideas you need first

### 1.1 A process is a sealed box the operating system enforces

When you run a program, the operating system creates a **process** for it. A process gets
its own memory — its own private region of RAM. The operating system guarantees that one
process cannot read or write another process's memory. Not "shouldn't": *cannot*. The CPU
hardware enforces it.

This is the strongest security boundary a normal computer offers, and it is free — you get
it just by being a separate program.

> **Why this matters here:** if Firefox has a bug, it cannot corrupt your text editor's
> memory, because they are different processes. If a Home Assistant integration has a bug —
> or is malicious — the same protection **does not apply**, because it is not a separate
> process. It is inside Home Assistant's process. That is the entire finding.

**Home Assistant runs as one process.** I confirmed this by following the startup path:
the program starts (`__main__.py`), sets up a single event loop, and runs everything in it.
No point on that path creates a second process for integrations. So your Hue integration,
your weather integration, and Home Assistant's own core code are all *the same program*, as
far as the operating system is concerned.

### 1.2 In Python, `import` does not "load" a file — it *runs* it

This is the single most important idea in the document, and it is the one most often
misunderstood by people who have used other languages.

In many languages, adding a library means the compiler links some pre-built code into your
program before it ever starts. In Python, `import some_module` does this, at the moment the
line executes:

1. Find the file `some_module.py` on disk.
2. **Execute every line in it, top to bottom, right now.**
3. Collect whatever that execution created — functions, variables, classes — into a
   "module object".
4. Remember it in a cache (`sys.modules`) so a second import returns the same thing rather
   than running the file again.

Step 2 is the one that matters. Importing is not reading. Importing is **running**. If a
file contains, at its top level:

```python
print("hello")
```

then merely importing it prints `hello`. And if it contains something worse than `print`,
merely importing it does that instead — before any function in it has been deliberately
called by anyone.

> **Analogy, and where it breaks.** People imagine importing as *consulting a reference
> book*. It is closer to *hiring someone and letting them start work immediately*. The
> analogy breaks in an important way: a person you hire is still a separate person, with
> their own hands and their own limits. Imported code is not separate. It becomes part of
> the same running program — see 1.1.

### 1.3 The line that does it

Home Assistant does not do anything unusual or clever to load an integration. It calls the
standard library function that performs exactly the process described in 1.2:

```python
cache[domain] = cast(ComponentProtocol, importlib.import_module(self.pkg_path))
```

That is `homeassistant/loader.py`, line 1091, in version 2026.8.3.

`importlib.import_module("custom_components.my_thing")` is the function-call form of
`import custom_components.my_thing`. It is the same mechanism, used because the name of the
thing to import is only known while the program is running.

Home Assistant's own comment, four lines above it, says as much:

> *"This is mostly a thin wrapper around importlib.import_module with a dict cache."*

**Read that plainly: there is no sandbox, no checking, no separate space, no restrictions.**
There is one ordinary import. I also searched the four core startup files for any sign of
confinement machinery — the words `sandbox`, `seccomp`, `permission model`, `capability`,
`privilege separation`. Zero hits. The absence is real, not something I overlooked.

### 1.4 An object reference is the thing itself, not a copy

In Python, when you pass a value to a function, you are not passing a copy of it. You are
passing a **reference** — a way of reaching the one original object that exists.

```python
def rename(thing):
    thing.name = "changed"

rename(my_house)     # my_house.name is now "changed"
```

`rename` did not receive a photograph of `my_house`. It received the address of the real
`my_house`, and it redecorated.

> **Analogy:** passing a copy is handing someone a photocopy of a document. Passing a
> reference is handing them the key to the filing cabinet the original lives in. Python
> does the second thing.

### 1.5 A dot means "go get this from inside that", and dots chain

`hass.states` means: take the object called `hass`, and get the thing stored inside it
under the name `states`. That thing is itself an object, so you can keep going:
`hass.states.set(...)` means "reach into `hass`, get `states`, and call its `set`".

There is no access control on this. Python has no `private` keyword in the sense Java or
C# does. **If you hold a reference to an object, you can reach everything inside it, and
everything inside those things, indefinitely.** The dots are a path through a structure,
and nothing stands at any junction checking whether you should be allowed through.

---

## Part 2 — What I actually followed, in plain language

I read the source from the moment the program starts to the moment third-party code first
runs. Five steps.

**Step 1 — One program, one loop.** Home Assistant starts, creates a single event loop (the
scheduler that decides which piece of work runs next), and everything happens inside it.
No integration is given a process of its own.

**Step 2 — One object to rule it all.** Home Assistant builds a single object called `hass`
— a `HomeAssistant` instance. This is the root of the system. Stored inside it are
references to essentially every subsystem: the state of every device, the event bus, the
service registry, the configuration, the authentication manager, the web server.

**Step 3 — Integrations are just folders of Python files.** A custom integration is a
directory inside `custom_components/`. Home Assistant lists that directory to see what is
installed. There is no registry, no signature, no vetting step in the code.

**Step 4 — Loading is the plain import from 1.3.** `importlib.import_module`. At this
moment the integration's code is *running*, inside Home Assistant's process (1.1), because
importing means executing (1.2).

**Step 5 — `hass` is handed over by direct call.** Home Assistant then calls a function the
integration defines, passing `hass` as an argument. There are exactly two such places:

| When | The actual line | What gets passed |
|---|---|---|
| Configured in YAML | `setup.py:412` — `component.async_setup(hass, processed_config)` | the real `hass` object |
| Configured in the UI | `config_entries.py:798` — `component.async_setup_entry(hass, self)` | the real `hass` object, **and** the config entry — which is where that integration's saved passwords and API keys live |

By 1.4, "passes `hass`" does not mean a copy or a limited view. It means the integration now
holds a reference to the actual root of the actual running system.

---

## Part 3 — The three consequences, and why each one bites

### 3.1 Holding `hass` is holding everything

Because of 1.5, an integration that has `hass` can reach, by following dots, all of this:

| What it reaches | Through | Meaning in ordinary terms |
|---|---|---|
| Every integration's working data | `hass.data` | One shared dictionary. Everyone's runtime state, in one place, keyed by name |
| The event bus | `hass.bus` | Publish any event; listen to every event in the house |
| The service registry | `hass.services` | Call any service any integration offers — including `lock.unlock` |
| Every device's state | `hass.states` | Read the state of everything; also *write* it |
| The config directory path | `hass.config.path()` | Resolve any file path under your config folder — including `secrets.yaml` |
| The auth manager | `hass.auth` | Users and tokens |
| The web server | `hass.http` | Register new URL routes on the running server |
| Everyone's stored credentials | `hass.config_entries` | Every integration's saved configuration, credentials included |
| The event loop and thread pool | `hass.loop` | Schedule work on Home Assistant's own scheduler |

A weather integration needs roughly one of these. It is handed all nine.

### 3.2 Taking `hass` away would not help — and this is the deep part

The obvious fix is: don't pass `hass`. Pass something smaller. That does not work, for two
separate reasons, and understanding both is what makes this finding worth a chapter.

**Reason one: the object is available without being passed.** Home Assistant stores the
`hass` object in a module-level location and provides a public function,
`async_get_hass()` (`core.py:244`), whose documented purpose is to hand it to code that
wasn't given it. Any code inside the process can call it. Its own docstring says it exists
for "where it's very cumbersome or downright impossible to pass hass". So `hass` is not a
secret being disclosed at line 412 — it is ambient, available on request to anything
running inside the process.

**Reason two — the real one: everything is reachable anyway.** Python provides a way to
ask the interpreter for a list of every object currently alive in the process
(`gc.get_objects()`, part of the garbage collector, which normally exists to clean up
unused memory). Code inside the process can walk that list, find another integration's live
objects, and read or modify them. This is not theoretical — it is the published
demonstration by Corno & Mannella that Chapter 4 already relies on. What my source walk
adds is the *mechanism*: this is possible precisely because Step 4 was an ordinary import,
so everything is in one process, in one object graph, with nothing between the pieces.

**So:** an integration's power does not come from something it was *given*. It comes from
**where its code is running**. Nothing was granted, so nothing can be withheld.

> This is what the report means by **positional authority**, and it is worth having a
> sentence ready for it: *an integration is not powerful because Home Assistant hands it
> power; it is powerful because it is inside.*
>
> **Analogy:** the difference between giving a visitor a key to one room, and letting them
> stand inside the vault. Confiscating the key changes nothing about the second case.

**And this is the argument Chapter 1 §1.9 owed.** If authority comes from position, then
merely *moving* an integration somewhere else does not constrain it — it just gives it a
new position. Relocation is necessary but not sufficient; what it must be paired with is
scoping *what the relocated code is allowed to ask for*. That is what the manifest is for.

### 3.3 Home Assistant knows which code is untrusted, and uses that to word a warning

This is the finding I did not expect, and it is rhetorically the strongest one.

Home Assistant *does* distinguish community code from its own. There is a flag,
`is_built_in`, which is true for official integrations and false for everything installed
from HACS. I checked every place in the platform that reads it — seven of them:

| Where it's used | What it does |
|---|---|
| `loader.py:704` | Logs "We found a custom integration … might cause stability problems" |
| `loader.py:853` | Labels its quality scale as `"custom"` |
| `loader.py:1761` | Points the bug-report link at the author instead of Home Assistant |
| `setup.py:274` | Puts the words "custom integration" into an error message |
| `frame.py:288, 304` | Chooses how loudly to log a deprecation warning |
| `requirements.py:273` | Puts the word "custom" into another message |

Every single one is **presentation**: a log line, a label, a link, a message. Not one of
them changes what the code is allowed to do. And critically, the flag is **never consulted**
at the place where the integration is loaded (Step 4), nor at either place where `hass` is
handed over (Step 5).

**Say it like this:** Home Assistant knows which code is untrusted. It uses that knowledge
to phrase a warning.

That sentence pairs exactly with the literature. Corno & Mannella's threat model defines
every threat as a plug-in acting outside its "scope" — where scope exists only in the
plug-in's prose documentation. So the published threat model assumes a boundary that is
written in English, and the platform's own trust distinction is a string in a log message.
**The manifest is that notion made machine-readable and enforced.** That is the
contribution, in one line, and it is now supported by source evidence rather than assertion.

### 3.4 One more thing, worth knowing

When an integration is set up, Home Assistant reads the list of Python packages it says it
needs, and runs `pip` to install them into the live interpreter
(`requirements.py:190` → `util/package.py`). Code is downloaded from the internet and made
importable, during startup, on the integration's say-so. This is relevant to the
supply-chain threats in Chapter 4; it is not the main finding, but do not be surprised by
it in a viva.

---

## Part 4 — Why this makes Chapter 5 genuinely hard

Chapter 3 committed to a constraint: **integrations must run unmodified.** Nobody is going
to rewrite four thousand community integrations, so a solution that requires changes to
them is not a solution.

Combine that with what Part 2 established, and the difficulty is sharp:

- The integration must run in a **different process** (that's the only real boundary — 1.1).
- But the integration's code says `hass.states.set(...)`, `hass.data[...]`, `hass.bus...`,
  and expects real answers.
- And it cannot be edited to say anything else.

So whatever sits in the sandbox and plays the part of `hass` has to **present the same
surface** — the same dots have to work, and return plausible things — while actually
forwarding each request across a process boundary to something that decides whether to
allow it.

That is the hardest engineering problem in the project, and it is now *specified* rather
than vague: the nine-row table in 3.1 is the list of what must be faced. That is exactly
what an evidence note is supposed to produce — the question, made precise enough to answer.

**What is still open** (deliberately, and stated so no one thinks it was missed):

- How that stand-in is actually built. Chapter 5's job.
- Which of the nine handles must be mediated, which can simply be refused, and which are so
  rarely used that refusing them costs nothing. That is a **measurement** question — the
  answer comes from counting what real integrations actually use.
- Who writes the manifest. Untouched by this note; still Chapter 5's.

---

## Part 5 — Saying it out loud

**The thirty-second version.** *Home Assistant loads community integrations with Python's
ordinary import statement. Importing in Python means executing, so the integration's code
runs inside Home Assistant's own process, and it is handed a reference to the root object of
the entire system. It can reach every device's state, every stored credential, and every
other integration's data — not because it was granted permission, but because it is inside.
Home Assistant does know which code is third-party; it uses that knowledge only to word a
warning.*

**If they ask "are you sure it's really that simple?"** *Yes — it's one line,
`loader.py:1091`, and Home Assistant's own comment calls it a thin wrapper around
`importlib.import_module`. I read it at version 2026.8.3, commit 759e465.*

**If they ask "why not just not pass `hass`?"** *Two reasons. There's a public function,
`async_get_hass()`, that hands out the same object to anything that asks. And more
fundamentally, in one process the whole object graph is walkable — Corno & Mannella
demonstrated reaching another integration's live objects through the garbage collector.
Authority comes from being in the process, not from the argument list.*

**If they ask "isn't a warning enough — users are told?"** *The warning is real, and it's
the only thing the flag does. The platform has the information needed to make a security
decision and spends it on log formatting. That's the gap.*

---

## Part 6 — Check yourself

Answer these in your own words, without looking above. If one is shaky, re-read the section
in brackets — that is a cheaper fix now than in a viva.

1. Why is "importing runs the code" the crucial fact, and not merely a technical detail?
   [1.2]
2. What does a process boundary give you that being careful inside one program does not?
   [1.1]
3. An integration is passed `hass`. Why is that different from being passed a copy of some
   settings? [1.4, 1.5]
4. Someone proposes: "just pass integrations a stripped-down `hass` with only what they
   need." Give the two reasons that fails. [3.2]
5. Home Assistant has an `is_built_in` flag. Why does its existence *strengthen* your
   argument rather than weaken it? [3.3]
6. Why does the compatibility constraint (integrations run unmodified) make the fix hard,
   given everything above? [Part 4]

**If you can only keep one thing:** `loader.py:1091` is an ordinary Python import.
Everything else in this document — and every constraint on the architecture in Chapter 5 —
is a consequence of that one line.
