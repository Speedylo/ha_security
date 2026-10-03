# A curriculum for owning the technical substrate

**Written 2026-09-11.** The purpose is not to revise the artifact. It is to build the layer of understanding *underneath* it, so that every mechanism in `framework/confine/` becomes something you could have derived rather than something you can recognise.

**The standard to aim at.** For each module: *given only the man pages and a blank editor, could I build this mechanism and defend every flag in it?* Recognition is not ownership. Re-derivation is.

**How to use this.** Ten modules, each with prerequisites, objectives, a concept sequence, primary sources, graded exercises, and a self-assessment. **Do the exercises in a scratch directory, not in `framework/`** — the point is to build the mechanism from nothing, not to read the version that exists. Only after your own version works should you diff it against the project's, and every difference is a finding: either you missed something, or the project did.

Two tracks are given in Part 3: a **3-week critical path** for the viva, and the **full 6-week curriculum**. The modules are the same; the fast track cuts depth, not breadth.

---

# Part 1 — The modules

---

## Module 0 — The operating system's model of a process

*Everything else is a modification of this model. Without it, namespaces and cgroups are magic words.*

**Prerequisites:** C literacy enough to read a man page's SYNOPSIS. You do not need to write much C.

**Objectives.** After this module you can explain, without notes: what a process *is* to the kernel; what a file descriptor actually refers to; how a system call crosses into the kernel and what an errno is; how memory is shared between processes and why "how much memory does this process use" is an ambiguous question.

### Concept sequence

1. **The process as a kernel object.** Address space, page tables, the task struct, the process tree. `fork`, `exec`, `wait`, orphans and reparenting, `PR_SET_CHILD_SUBREAPER`.
2. **The three-level file descriptor model, and it is the one most people never learn properly:**
   - the per-process **file descriptor table** (integers → entries)
   - the system-wide **open file description** (offset, status flags, and the thing `dup` shares)
   - the **inode** (the file itself)

   Nearly every subtle fd behaviour — `dup2`, `O_CLOEXEC`, fork inheritance, and later `SCM_RIGHTS` — follows from knowing which of the three levels is being copied. Learn this properly here and Module 2's fd passing becomes obvious instead of mystical.
3. **Process credentials.** real/effective/saved uid and gid, `fsuid`, supplementary groups, and how `setuid` behaves differently for root and non-root.
4. **The syscall boundary.** How a syscall is issued (`syscall` on x86-64, `svc` on aarch64), the syscall *number* as an architecture-specific index into a table, arguments in registers, the return-value/errno convention. **Why this matters to you:** it is the reason `seccomp.py` hard-codes two tables and checks the architecture first.
5. **Virtual memory and the meaning of "used".** Pages, copy-on-write, the page cache, shared library mappings. Then **RSS vs PSS vs USS** — resident, proportional (shared pages divided by the number of sharers), unique. Read `/proc/PID/smaps_rollup` and see all three.

### Primary sources

- **Kerrisk, *The Linux Programming Interface*** — chapters 2, 5 (file I/O and fd semantics), 6 (processes), 9 (credentials), 24–28 (process creation and execution). This book is the spine of Modules 0–4 and is worth owning in print.
- **Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*** — free online. Virtualisation section for the process/address-space model if Kerrisk assumes too much.
- `man 2 open`, `man 2 dup`, `man 7 credentials`, `man 5 proc` (the `smaps` section).

### Exercises, graded

1. **Write a 50-line shell** that forks, execs, and waits. Add a pipeline. This is the "hello world" of process control and it makes the process tree concrete.
2. **Demonstrate the three-level fd model.** Open the same file twice; `dup` one of them. Write through each and show which share an offset and which do not. Predict before you run.
3. **Measure yourself.** Write a program that allocates 100 MB, then reports its own RSS, PSS and USS from `/proc/self/smaps_rollup`. Fork it and watch PSS halve while RSS does not.

### Self-assessment

- What exactly does `dup2` copy, and what does it share?
- Two processes map the same shared library. How much of it does each "use"?
- Why is a syscall number not portable across architectures?
- **Project link:** exercise 3 is the measurement underneath every memory figure in the report — the 176 MB first sandbox, the 136 MB marginal, the 26-sandbox budget. Be ready to answer *"why PSS?"*

---

## Module 1 — The Linux privilege model

*You cannot explain why your sandbox is unprivileged until you can explain what privilege is.*

**Prerequisites:** Module 0.

**Objectives.** Explain the decomposition of root into capabilities; describe the five capability sets and how they transform across `execve`; explain `no_new_privs` and why it is a precondition for unprivileged seccomp; place seccomp, capabilities and LSMs as three distinct layers.

### Concept sequence

1. **DAC**: uid/gid/mode, and its limits. Why "root can do anything" was the design and the problem.
2. **POSIX capabilities.** Root split into ~40 independent bits — `CAP_NET_ADMIN`, `CAP_SYS_ADMIN` (the "new root", and why that is a criticism), `CAP_SYS_CHROOT`, `CAP_DAC_OVERRIDE`.
3. **The five sets** — permitted, effective, inheritable, bounding, ambient — and the transformation rules on `execve`. This is genuinely intricate and most people hand-wave it. Do not hand-wave it.
4. **`no_new_privs`.** A one-way flag: no `execve` after it can gain privilege (setuid binaries stop elevating). **It is mandatory before loading a seccomp filter without `CAP_SYS_ADMIN`**, and the reason is a design decision about not letting an unprivileged filter confuse a setuid program.
5. **The layers, kept distinct**: DAC → capabilities → seccomp (syscall gate) → LSM (SELinux, AppArmor; hooks deep inside the kernel, with object-level knowledge seccomp cannot have). Knowing why seccomp is not an LSM — and what an LSM could express that seccomp cannot — is a strong viva answer.

### Primary sources

- `man 7 capabilities` — read it end to end, twice. It is dense and it is the definitive text.
- Kerrisk, *TLPI* chapter 39.
- `man 2 prctl` (`PR_SET_NO_NEW_PRIVS`), `man 7 user_namespaces` (the capability rules section).

### Exercises

1. Write a program that prints its own capability sets, parsed from `/proc/self/status`.
2. Run a binary that needs `CAP_NET_RAW` (ping is the classic) with and without the capability.
3. Set `no_new_privs`, then `execve` a setuid binary and observe that it does not elevate.

### Self-assessment

- Why is `CAP_SYS_ADMIN` described as "the new root"?
- What is the bounding set for, given that permitted already limits you?
- Why must `no_new_privs` be set before an unprivileged `PR_SET_SECCOMP`?
- **Project link:** `seccomp.py` sets `PR_SET_NO_NEW_PRIVS` — you should be able to say what breaks without it and why the kernel insists.

---

## Module 2 — Namespaces

*The isolation dimension. Eight per-process views of resources the kernel otherwise treats as global.*

**Prerequisites:** Modules 0 and 1. Module 1 is not optional here — the user namespace's whole behaviour is a capability rule.

**Objectives.** Describe each namespace type and what it virtualises; explain precisely why a user namespace makes the other seven available to an unprivileged process; write the `uid_map`/`gid_map` pair correctly and explain the `setgroups` restriction; describe namespace lifetime and ownership; and state the security argument *against* unprivileged user namespaces.

### Concept sequence

1. **The idea.** A namespace virtualises a global resource so that processes inside see a different instance of it. `clone`/`unshare`/`setns` as the three verbs; `/proc/PID/ns/*` as the handles; `nsfs` and why holding an open fd keeps a namespace alive after its last process exits.
2. **The eight types**, each with the global resource it virtualises: **mnt** (the mount table), **pid** (process IDs, and the special role of PID 1), **net** (interfaces, routes, ports, the whole stack), **ipc**, **uts** (hostname), **user** (uid/gid mappings *and capabilities*), **cgroup** (the cgroup root a process sees), **time** (boot/monotonic offsets).
3. **User namespaces in depth — the keystone.** When a process creates a user namespace it receives a **full capability set inside that namespace**. That single rule is why an unprivileged user can then create the other seven: they are privileged operations *with respect to a namespace you own*. Then:
   - `uid_map` / `gid_map`: format, the single-line restriction for the unprivileged case, and what "mapped" means to file ownership (an unmapped uid appears as `nobody`/`overflowuid`).
   - **The `setgroups` rule.** You must write `deny` to `/proc/self/setgroups` before `gid_map` when unprivileged. The reason is specific and worth being able to state: dropping a supplementary group can *increase* access, because a file mode can deny a group what it grants to others. The kernel therefore refuses to let an unprivileged user namespace call `setgroups` at all.
4. **PID namespaces.** PID 1's special semantics: it reaps orphans, and signals to it are handled differently. What happens when it dies. Why `/proc` must be remounted to see the new PID view.
5. **The counter-argument, which you must own before an examiner raises it.** Unprivileged user namespaces hand unprivileged code a large amount of previously root-only kernel surface, and they have a real CVE history; several distributions have shipped switches to restrict them. **Your design trades Python-level authority for kernel-level attack surface.** That is a defensible trade — state it as a trade, with the mitigation (seccomp cuts the surface back down), rather than being caught by it.

### Primary sources

- **Michael Kerrisk's LWN namespaces series** (seven parts, plus the user-namespace articles). It is the canonical tutorial treatment and it is free.
- `man 7 namespaces`, `man 7 user_namespaces`, `man 7 pid_namespaces`, `man 7 mount_namespaces`.
- **Liz Rice, *Container Security*** (O'Reilly) — chapters on isolation; and her live-coded "containers from scratch" conference talks, which build one in front of you.

### Exercises

1. **`unshare(1)` before any code.** Explore from the shell: `unshare -Ur`, `unshare -Urp --fork`, `unshare -Urn`. Get an intuition for what each flag changes before automating it.
2. **Build a container from scratch**, ~100 lines, no libraries — user + pid + mnt + uts namespaces, a mapped uid, a hostname, and a shell inside. This is the single highest-value exercise in the curriculum.
3. **Break it deliberately, predicting first each time:** omit the `setgroups` deny and observe the `gid_map` failure; write a multi-line map unprivileged; let PID 1 exit while children live.

### Self-assessment

- Why can an unprivileged user create a network namespace but not move a host interface into it?
- What does a process inside a userns see as the owner of a file owned by an unmapped uid?
- What is the argument that unprivileged user namespaces made Linux *less* secure?
- **Project link:** `namespaces.py` is exactly exercise 2 plus error handling. After this module you should be able to rewrite it from blank.

---

## Module 3 — Filesystem containment

*Isolating the process is half of it. Isolating what it can see is the other half, and mount propagation is where people get it wrong.*

**Prerequisites:** Module 2 (mount namespaces).

**Objectives.** Explain mount propagation's four types and why a new mount namespace must be made private first; construct a root filesystem from bind mounts; explain why `pivot_root` and not `chroot`, including the escape; know what overlayfs would have given you.

### Concept sequence

1. **`mount(2)` beyond `mount(8)`.** Source, target, filesystem type, flags, data. `MS_BIND` and what a bind mount actually is (a second view of a subtree). `MS_REC`.
2. **Mount propagation — study this properly, it is the subtlest thing in the module.** The four types: **shared**, **private**, **slave**, **unbindable**; peer groups; how a new mount namespace *inherits* propagation from its parent, so without `MS_REC|MS_PRIVATE` on `/` your "private" mounts appear on the host. The canonical document is the kernel's `sharedsubtree` text.
3. **The read-only bind gotcha.** `MS_BIND` does **not** take its flags from the same call; a read-only bind requires a second `MS_REMOUNT|MS_BIND|MS_RDONLY`. A silently-skipped remount produces a writable mount that looks exactly like a working read-only one — a failure mode that passes every test that only checks the mount exists.
4. **`MS_NOSUID`, `MS_NODEV`, `MS_NOEXEC`** — what each actually prevents, and why `nosuid` matters most in a user namespace.
5. **`pivot_root` vs `chroot`.** `chroot` only changes the root *directory lookup*; a process holding `CAP_SYS_CHROOT` escapes with a handful of lines (open a directory fd, chroot elsewhere, chdir up past the root). **Inside a user namespace you hold `CAP_SYS_CHROOT` by construction**, so `chroot` is not containment there. `pivot_root` changes the namespace's root mount and lets you unmount the old one, which is why it is the right primitive.
6. **What you did not use:** overlayfs — lower/upper/work layers, copy-up semantics. Worth knowing because "why did you copy the tree instead of overlaying it?" is a fair question with a real answer.

### Primary sources

- `man 7 mount_namespaces` (the propagation section), `man 2 mount`, `man 2 pivot_root`.
- Kernel `Documentation/filesystems/sharedsubtree.rst` — the definitive propagation reference.
- `man 8 mount` for the flag semantics; `man 5 proc` for `mountinfo`, which is how you *observe* propagation state.

### Exercises

1. **Watch propagation happen.** In a new mount namespace without making `/` private, mount a tmpfs and check `/proc/self/mountinfo` from the host. Then add `MS_REC|MS_PRIVATE` and repeat.
2. **Build a root from nothing:** a tmpfs, bind in a few host paths read-only, `pivot_root`, unmount the old root, and exec a shell. Verify the read-only binds really are read-only — then remove the remount step and watch the test that only checks "is it mounted" keep passing.
3. **Escape a chroot** from inside, in ~20 lines. Nothing teaches why `pivot_root` exists faster.

### Self-assessment

- What is a peer group and when would you want `slave` rather than `private`?
- Why does a read-only bind need two calls?
- You are inside a user namespace. Why is `chroot` not a boundary?
- **Project link:** `sandbox.py:build_root` is exercise 2. Its comments already state the three load-bearing details; after this module you should be able to state them first and *then* read.

---

## Module 4 — seccomp and syscall filtering

*The syscall gate: what it can express, and — more importantly for your report — what it structurally cannot.*

**Prerequisites:** Modules 0 (syscall boundary) and 1 (`no_new_privs`).

**Objectives.** Read and write classic BPF by hand; explain `struct seccomp_data` and why the architecture check must come first; choose among the return actions with reasons; and state seccomp's fundamental limitation and the modern answer to it.

### Concept sequence

1. **Classic BPF as a virtual machine.** A tiny accumulator machine: load, jump, return. **No loops** — which is why the verifier can guarantee termination. This is *not* eBPF, and confusing the two is a common and visible error.
2. **`struct seccomp_data`**: `nr`, `arch`, `instruction_pointer`, `args[6]`. Filters see register values only.
3. **Why the architecture check is first.** The same syscall number means different things on different architectures (and x86-64 can issue x32 calls). A filter that checks `nr` before `arch` can be bypassed by making the call under a different ABI. Your filter must therefore refuse any `arch` it was not built for, outright.
4. **Return actions and their consequences:** `ALLOW`, `ERRNO` (lie and continue — often the most compatible), `KILL_THREAD` vs `KILL_PROCESS`, `TRAP` (SIGSYS), `LOG`, `TRACE`, `USER_NOTIF`. Choosing between `ERRNO` and `KILL_PROCESS` is a *policy* decision about whether a blocked call should look like a failure or an execution.
5. **The fundamental limitation.** A filter **cannot dereference pointers**. It sees the address of a path, never the path. So seccomp cannot express "no opening files outside /sandbox" — any check the kernel could do on your behalf would be a TOCTOU race with a thread rewriting the buffer. **This limit is the reason your design needs namespaces and mounts at all**, and saying so explains why the layers compose instead of overlapping.
6. **`SECCOMP_USER_NOTIF`** — the modern mechanism that hands the decision to a userspace supervisor (with `ADDFD` for passing back a file descriptor). It is the "what I would build next" answer to the limitation above, and it rhymes with your mediator's design.
7. **Practical:** `libseccomp` as the normal way to do this, and why writing raw BPF instead is a defensible choice for a dependency-free artifact.

### Primary sources

- Kernel `Documentation/userspace-api/seccomp_filter.rst` — the primary text.
- `man 2 seccomp`, `man 2 prctl`, `man 3 seccomp_rule_add` for the libseccomp model.
- The Chromium sandbox design docs — seccomp-bpf's original driver, and an excellent worked example of layered sandbox reasoning.

### Exercises

1. **Write a filter by hand**, as raw instructions, that kills the process on one syscall. Then add the architecture check and test it does what you think.
2. **Filter on an argument** — allow `socket(AF_UNIX, ...)` and deny `socket(AF_INET, ...)`. This teaches exactly what a filter can see.
3. **Find the wall.** Try to write a filter that allows `open` on one path and denies another. Work out precisely why you cannot, and write that explanation down — it is a viva answer.
4. Verify by **behaviour**, not by reading the filter: make the denied call and check the outcome.

### Self-assessment

- Why can a BPF filter be verified to terminate?
- What breaks if you check `nr` before `arch`?
- When would you prefer `ERRNO` to `KILL_PROCESS`?
- **Project link:** `seccomp.py` builds its program in exactly this shape, with a per-architecture table because there is no portable way to name syscalls numerically. Exercises 3 and 4 are the two claims the report makes about it.

---

## Module 5 — cgroups v2

*The resource dimension. Namespaces answer "what can it see"; cgroups answer "how much can it take".*

**Prerequisites:** Module 1 (delegation is an ownership question).

**Objectives.** Explain the v1→v2 redesign; enable and configure the memory, cpu, pids and io controllers by hand; explain the delegation model and why some controllers cannot be delegated to an unprivileged user; and read the accounting files well enough to know what a number means.

### Concept sequence

1. **Why v2 exists.** v1's per-controller hierarchies made a process's membership ambiguous across controllers; v2 is a **single unified hierarchy**. The **no-internal-process rule**: once controllers are enabled for children, only leaf cgroups may contain processes.
2. **`cgroup.subtree_control`** — a parent *enables controllers for its children*. The distinction between a controller being **present** on the system, **enabled** in a subtree, and **delegated** to you is the whole of this module, and your project found it twice.
3. **Delegation.** What it means to own a cgroup directory; the containment rule (you need write access to the destination's `cgroup.procs` *and* to the common ancestor's); how systemd's user slices set this up; and why an unprivileged supervisor's authority depends on **where it is running**, not on when it places anything.
4. **The controllers, one at a time:**
   - **memory**: `memory.current`, `.high` (throttle+reclaim), `.max` (hard limit, OOM), `.low`/`.min` (protection), and `memory.events`. The difference between `high` and `max` is a real understanding check. What the OOM killer does and what page-cache reclaim means for a limit.
   - **cpu**: `cpu.max` as "quota period", and how that differs from shares/weight.
   - **pids**: the simplest controller, and a real defence against fork bombs.
   - **io**: `io.max` needs device major:minor and block-layer knowledge — a large part of **why it is commonly not delegated**. Non-delegation is a property of the system's configuration, not a matter of effort.
5. **`clone3(CLONE_INTO_CGROUP)`** — placing a child into a cgroup at creation rather than migrating it afterwards, and why it needs the same permissions as migration. If you can't write `cgroup.procs`, changing *when* you write it changes nothing.

### Primary sources

- Kernel `Documentation/admin-guide/cgroup-v2.rst` — read it properly; it is one document and it is the authority.
- `man 7 cgroups` for the v1/v2 comparison and the delegation section.
- systemd's `systemd.resource-control(5)` — how this is done in practice on a real distro.

### Exercises

1. **By hand with `echo`**: create a cgroup under your user slice, enable `memory` and `pids`, move a shell in, and observe `memory.current` change as you allocate.
2. **Make the limit bite.** Set `memory.max` low and allocate past it. Watch `memory.events`. Then set `memory.high` instead and observe the different behaviour — throttling, not killing.
3. **Find the delegation boundary.** Try to enable a controller your user does not have delegated. Read the exact error and work out which rule you hit.
4. `cpu.max` at 25% and verify with a busy loop that you get 25%.

### Self-assessment

- What is the no-internal-process rule for?
- `memory.high` vs `memory.max` — when does each matter?
- Why does `CLONE_INTO_CGROUP` not help an unprivileged process that cannot migrate?
- **Project link:** `cgroup.py`; §6.4.1's "present but not permitted" distinction; R7, which is a standing residual risk that exists *because* `io` is not delegated. That risk is only defensible if you can explain delegation precisely.

---

## Module 6 — Networking, names and addresses

*The largest module, because the egress design touches four independent areas.*

**Prerequisites:** Module 2 (network namespaces). Basic sockets.

**Objectives.** Build and connect network namespaces by hand; explain how a fresh netns differs from a configured one; explain the two DNS resolution paths and why both must be intercepted; describe DNS rebinding and the resolve-then-pin defence; and state what pinning an address does and does not do to TLS.

### Concept sequence

1. **Sockets, properly.** TCP vs UDP semantics, `connect` on a datagram socket, blocking vs non-blocking, and what an fd for a socket refers to (back to Module 0's three-level model).
2. **A network namespace from empty.** A fresh netns has **loopback only, and `lo` starts DOWN**. Interface flags (`IFF_UP`, `IFF_MULTICAST`), addresses, and the routing table. **veth pairs** as the standard way to connect one to another; bridges; NAT. Build this by hand with `ip`.
3. **Two ways to talk to the kernel about interfaces**: `ioctl` (`SIOCGIFFLAGS`, `SIOCSIFFLAGS`, `SIOCADDRT`) — old, simple, limited; and **rtnetlink** — the modern, complete interface that `ip` itself uses. Know which you used and why the other exists.
4. **Multicast**, which is where your best finding lives. Group membership and IGMP; joining a group via `INADDR_ANY` and **how the kernel then selects an interface from the routing table**; why a fresh `lo` without `IFF_MULTICAST` refuses the join; mDNS on 224.0.0.251:5353 and what service discovery actually does on a home network.
5. **Name resolution, and the two seams.** `getaddrinfo` → NSS → `/etc/nsswitch.conf` → files/DNS, all in libc. **Versus** a library resolver such as c-ares (`aiodns`), which speaks DNS over UDP itself and never touches libc. Two seams exist because these are two different code paths, and a mediator that intercepts one has intercepted 4% or 96% of the traffic depending which.
6. **DNS rebinding**, in full: the attacker controls the name; resolution happens twice; the second answer is internal. The defence is **resolve once, pin the address, hand back a connected socket** — the sandbox never holds a name it could re-resolve. Then **RFC 1918** and what "private" means, including the addresses people forget: loopback, link-local, IPv4-mapped IPv6, CGNAT space.
7. **What pinning costs you.** If you connect to a pinned IP, TLS certificate validation and SNI must still be driven by the *name*, or you have broken the thing that authenticates the peer. Be able to say how that is handled.

### Primary sources

- Beej's *Guide to Network Programming* for socket fundamentals if they are rusty.
- `man 8 ip-netns`, `man 8 ip-link`, `man 7 netlink`, `man 7 rtnetlink`.
- `man 3 getaddrinfo`, `man 5 nsswitch.conf`; the c-ares documentation for the contrast.
- OWASP's DNS rebinding material; RFC 1918; RFC 6890 for the full special-purpose address registry.

### Exercises

1. **Two namespaces, one veth pair, by hand.** Ping across it. Add a route. Delete the route and watch it fail.
2. **Reproduce the multicast failure**: in a fresh netns, bring `lo` up, try to join a multicast group, observe the error; then add `IFF_MULTICAST`; then add the `224.0.0.0/4` route and watch the join succeed. Predict each outcome before running.
3. **Watch both resolution seams.** `strace` a program using `getaddrinfo` and one using `aiodns`, and see that one opens `/etc/resolv.conf` through libc while the other sends its own UDP packet.
4. **Build a rebinding demo** against a naive client: a name that resolves to a public address once and a private one the second time.

### Self-assessment

- Why does a fresh network namespace have no connectivity even to itself until you act?
- Two libraries resolve the same hostname. Why might only one be visible to your interception?
- You pinned the IP. What have you *not* defended against?
- **Project link:** `egress.py`, `egress_shim.py`, the §7.24 shape measurement, and the mDNS finding in §7.27 — the strongest story you have, and it needs all of 4, 5 and 6 above to tell properly.

---

## Module 7 — Integrity, authenticity and durability

*The audit log makes a claim about the past. This module is what makes that claim precise.*

**Prerequisites:** None technical; comfort with the idea of a hash function.

**Objectives.** State precisely what a hash chain detects and what it does not; explain why a MAC is a different guarantee; identify the adversary each defends against; explain the anchoring problem; and explain what `fsync` guarantees and at what cost.

### Concept sequence

1. **Hash functions**: preimage, second-preimage, collision resistance — three different properties, and knowing which one a construction depends on is the test of understanding.
2. **Hash chains.** Each record commits to its predecessor. **What this detects:** reordering, deletion and modification *by an adversary who cannot recompute the chain*. **What it does not:** an adversary who can rewrite the file can recompute every subsequent hash, so a bare chain alone stops nobody with write access. This is the distinction to get exactly right.
3. **MACs.** HMAC's construction and why it is not just `hash(key || message)`. A keyed chain resists forgery by anyone lacking the key — **but the key lives on the same machine**, so the defence is against an adversary with file access and not one with process access.
4. **Why two chains, failing independently.** Articulate the adversary each addresses, and be honest about the one neither addresses.
5. **The anchoring problem.** Any purely local log can be truncated wholesale. The real answer is to publish the head somewhere the adversary does not control — which is what certificate-transparency logs do, and what R4 in your register is asking for. **Merkle trees** and why they beat a linear chain when you need efficient proofs.
6. **Durability.** The write path: userspace buffer → page cache → device. `fsync` vs `fdatasync`; what a filesystem journal guarantees about ordering; write barriers and FUA; and why a durable append costs milliseconds while a buffered one costs microseconds. **Durability is a different property from integrity** and the report should never blur them.

### Primary sources

- **Ferguson, Schneier & Kohno, *Cryptography Engineering*** — the hash and MAC chapters. Read for the reasoning, not the constructions.
- RFC 2104 (HMAC); RFC 6962 (Certificate Transparency) for anchoring and Merkle proofs done for real.
- `man 2 fsync`; the Postgres and SQLite durability write-ups are unusually good on what filesystems actually promise.

### Exercises

1. **Forge a hash-chained log.** Edit a record, recompute the chain, and show it verifies. Then do the same against the MAC chain and watch it fail.
2. **Truncate both.** Show that neither detects wholesale truncation of the tail — this is the argument for anchoring, made by demonstration.
3. Measure an append with and without `fsync` on the Pi and reproduce the order of magnitude.

### Self-assessment

- Precisely which adversary does a bare hash chain stop?
- Why does the MAC key's location bound the guarantee?
- Is `fsync` an integrity mechanism?
- **Project link:** `audit.py`, §5.12, R4, and the 3,670.7 µs vs 61.8 µs durability measurement.

---

## Module 8 — The Python runtime as an attack surface

*This module supplies the project's premise. If the premise is shaky, the architecture is unmotivated.*

**Prerequisites:** Fluent Python.

**Objectives.** Explain why in-process isolation of Python code is not achievable; describe the import system precisely; explain what the GC exposes and why; and explain the asyncio execution model well enough to defend a latency number.

### Concept sequence

1. **The object model.** Everything is an object; references; reference counting plus a cycle collector. **`gc.get_objects()` returns every tracked object in the process** — so any code running in the interpreter can walk to any other code's data. No discipline by a library author prevents this. **This is the entire argument for out-of-process confinement**, and it is §2.4.1.
2. **Why the classic in-process approaches fail:** attribute-name blacklists, `__builtins__` stripping, `RestrictedPython`-style rewriting — and the standard escapes (`().__class__.__bases__`, walking `__subclasses__`, frame introspection). Knowing *why each historically failed* is what makes "so I put it in another process" a conclusion rather than a preference.
3. **The import system.** `sys.modules` as a global cache; finders, loaders, meta-path hooks; module-level code executing on import. **Why "import" is already execution** — which is exactly what your compatibility measurement measures, and its limitation.
4. **asyncio.** The event loop, coroutines, tasks; **why a blocking call inside the loop blocks everything** (which is what a synchronous `fsync` on the mediator's path would do); executors; transports and protocols, and `DatagramProtocol` as the shape the UDP relay does not serve.
5. **`ast`**: parsing without executing, and why static analysis over a corpus is sound for imports and unsound in general (dynamic imports, `getattr`).

### Primary sources

- CPython documentation: `gc`, `importlib`, `ast`, `asyncio` — the "developing with asyncio" and import-system reference pages specifically.
- The published literature on Python sandbox escapes — read two or three write-ups; they are short and they are the evidence for point 2.

### Exercises

1. **Walk the heap.** In one process, create an object holding a secret in one module and reach it from another module via `gc.get_objects()`. This is §7.15 in ten lines and you should be able to write it live.
2. **Escape a naive sandbox** you write yourself — strip `__builtins__` and then reach `os` anyway.
3. Write a meta-path hook that logs every import; observe how much runs at import time.
4. Block the event loop with a synchronous sleep and measure what happens to concurrent tasks.

### Self-assessment

- Why is in-process isolation of untrusted Python not a solvable problem?
- What does an import-level compatibility measure *not* tell you?
- **Project link:** the motivation in Chapter 2, the gc attack in §7.15, the `ast` API-surface measurement, and §7.20's latency work.

---

## Module 9 — The platform: Home Assistant's architecture

*You confined something. An examiner may know this platform better than the kernel.*

**Prerequisites:** Module 8.

**Objectives.** Describe the integration lifecycle; explain the `hass` object's role; distinguish the state machine from the entity registry and say why that distinction carries a measurement; and write a working integration from scratch.

### Concept sequence

1. **`hass` as the god object** — the bus, the state machine, `hass.data`, the config entries, and why holding a reference to it is equivalent to holding the whole system. This is the coupling re-derived in `notes/ch5_evidence_ha_coupling.md`.
2. **Integration lifecycle**: `manifest.json`, `async_setup`, `async_setup_entry`, config flows, and why 26 of 37 integrations cannot be set up without a credential.
3. **Entities.** The **state machine** (states published by the API, no registry row, nothing surviving restart) versus the **entity registry** (`unique_id`, config-entry ownership, persistence). `async_add_entities` is the path that creates the registry row, and §5.6.1 measured 83% of the corpus using it. **This is the distinction §8.7 #2 exists to settle.**
4. **The helpers that matter to you**: `async_get_clientsession` and why the platform insists on it; the frame helper; zeroconf/discovery integration.
5. **HACS** and the custom-component distribution model — the supply chain your threat model assumes.

### Primary sources

- The Home Assistant **developer documentation** — architecture and "building your first integration" sections.
- The source at `~/ha-src/core`, pinned at 2026.8.3 — the authority, and the one you already used.

### Exercises

1. **Write an integration from scratch** with a config flow and one sensor; install it into a real instance; watch it appear in the registry.
2. Publish a state directly through the states API instead and diff what the registry shows. (**That diff is §8.7 #2's measurement** — the exercise and the future-work item are the same act.)

### Self-assessment

- What does an integration get from `hass` that it could not get otherwise?
- Registry row vs state — what survives a restart, and why does it matter to a confinement design?
- **Project link:** §5.6.1, §6.10.2, §8.6.3's limit #2.

---

## Module 10 — Security engineering as a discipline

*The frame around everything else, and the part most likely to be probed by an examiner who is not a kernel person.*

**Prerequisites:** None.

**Objectives.** Justify your threat-modelling method rather than merely applying it; situate the work in the sandboxing literature; and defend your risk-rating scheme's limits.

### Concept sequence

1. **Threat modelling as a method.** STRIDE per element; attack trees; data-flow diagrams and trust boundaries; how to know when a model is *done*. Where STRIDE's weaknesses are.
2. **ISO 31000's structure** — establishing context, identification, analysis, evaluation, treatment, monitoring — and why following its clauses is a stronger claim than "I listed some risks".
3. **Ordinal vs cardinal scales.** Impact × likelihood matrices multiply two *orderings*, and the product is not a quantity. You already state this; know the underlying argument (the standard critique of risk matrices) so you can defend it under pressure.
4. **The sandboxing literature you should be able to place yourself against**: OS-level isolation (Chromium's sandbox; gVisor's user-space kernel; Firecracker's microVMs; the seccomp origin story), and IoT/automation-platform work (FlowFence, SandTrap, and the smart-home gateway papers already in `refs/`). For each: what is the trusted computing base, what is the isolation boundary, what does it cost?
5. **The principles**, used precisely rather than decoratively: least privilege, complete mediation, fail-safe defaults, economy of mechanism, defence in depth (Saltzer & Schroeder). Being able to name which principle each of your design decisions serves is a fast, strong viva answer.

### Primary sources

- **Shostack, *Threat Modeling: Designing for Security*** — the standard text.
- Saltzer & Schroeder, *The Protection of Information in Computer Systems* (1975) — short, and the origin of the principles everyone cites.
- The Chromium sandbox design docs; the gVisor architecture guide.
- Your own `refs/` — plus FlowFence and SandTrap.

### Exercises

1. Threat-model something you did not build — a password manager, say — with STRIDE, in one sitting. Applying the method to unfamiliar material proves you hold the method and not a memory.
2. **Write a one-page comparison** of your design against gVisor and against a plain container, on TCB, boundary and cost. This is very likely to be asked in some form.

### Self-assessment

- Why is a risk matrix's product not a number?
- What is your TCB, precisely, and what is in it that you wish were not?
- Where does your design sit between "a container" and "a VM", and what did you give up?

---

# Part 2 — Assessment

Each module's self-assessment questions are the first gate. The real gate is this:

| Level | Test |
|---|---|
| **1 — Recognise** | You read `namespaces.py` and follow it |
| **2 — Explain** | You describe, without the file open, what each call does and why it is in that order |
| **3 — Derive** | Given man pages and a blank editor, you rebuild it and defend every flag |
| **4 — Critique** | You can say what is wrong with it, what you would do differently, and what the design costs |

**Level 3 is the standard.** Level 4 is what distinguishes a strong defence, and it is reachable because the project already documented its own mistakes.

**The final proof, worth a weekend:** rebuild a minimal `namespaces.py` + `sandbox.py` + `seccomp.py` from scratch in a clean directory, without opening the originals. Then diff. Every difference is either something you learned or something worth asking about the original.

---

# Part 3 — Two tracks

## The 3-week critical path (viva-essential)

For each item: read the primary source, do the one starred exercise, answer the self-assessment aloud.

| Week | Modules | Starred exercises |
|---|---|---|
| **1** | 0 (fd model, PSS), 1 (capabilities, `no_new_privs`), 2 (user namespaces) | Container from scratch (2.2) |
| **2** | 3 (propagation, `pivot_root`), 4 (seccomp), 5 (cgroup delegation) | Chroot escape (3.3); find seccomp's wall (4.3); delegation boundary (5.3) |
| **3** | 6 (netns, two DNS seams, rebinding), 7 (chains and anchoring), 8 (gc premise) | Multicast reproduction (6.2); forge a chain (7.1); heap walk (8.1) |

Modules 9 and 10 are read-only in this track — you already hold most of their content.

## The full 6-week curriculum

Weeks 1–3 as above but with **all** exercises; then:

| Week | Modules |
|---|---|
| **4** | 6 in full — veth, rtnetlink, TLS-vs-pinning |
| **5** | 7 and 8 in full, including Merkle trees and the asyncio work |
| **6** | 9 (write an integration from scratch) and 10 (the comparison paper) |

**Run this in parallel with the figures.** Drawing a mechanism is a forcing function for understanding it — pair Module 2 with the sandbox-structure figure, Module 6 with the resolve-then-pin figure, Module 7 with the audit-chain figure. If a diagram is hard to draw, the understanding is not there yet, and that is useful information rather than a setback.

---

# Part 4 — The core library

If the whole list is too much, these five carry most of it:

1. **Kerrisk, *The Linux Programming Interface*** — Modules 0–4. The single most valuable book here.
2. **Kernel documentation**: `cgroup-v2.rst`, `seccomp_filter.rst`, `sharedsubtree.rst`. Primary sources, free, and the authority when a blog post disagrees.
3. **`man 7 capabilities`, `man 7 user_namespaces`, `man 7 mount_namespaces`** — read fully, not searched.
4. **Rice, *Container Security*** — the same material assembled the way your project assembles it.
5. **Shostack, *Threat Modeling*** — Module 10, and Chapter 4's method.

---

# A note on the premise

You directed this work with a methodology and the code was written with AI assistance. The gap you are feeling is real, and it is also **narrower than it feels**, for a reason visible in the artifact: the code already carries its own reasoning. `sandbox.py:174` explains why a bind mount needs a second remount and says that skipping it "is a failure that looks exactly like success". `seccomp.py:133` explains why the architecture check must come first. `namespaces.py:61` explains the `setgroups` rule.

That reasoning was recorded because the work was directed by someone asking *why*. This curriculum is the other half of the same act: it converts recorded reasoning into derivable reasoning. **Work the exercises in a clean directory, not in `framework/` — build first, read second.**