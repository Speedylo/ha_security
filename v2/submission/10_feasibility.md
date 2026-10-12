# 10. Feasibility Study

Feasibility was assessed before the work that depended on it, across technical, economic, legal and ethical, operational and scheduling dimensions. The technical assessment was the decisive one, because the design rests on kernel features that a householder's device may not provide, and two of its findings changed the design.

## 10.1 Technical feasibility

The reference device was probed before the architecture was fixed, because a design that assumes kernel features is only as sound as the kernel it runs on. On the Raspberry Pi 5, running Raspberry Pi OS with kernel 6.12.47, an ordinary user could create user, network and process-identifier namespaces, all seven namespace types the design uses were present [33], and system-call filtering with seccomp was available [34]. The supervisor therefore needs no privilege, which matters for security as well as convenience: a confinement tool that must run as root enlarges the attack surface it exists to reduce.

Two findings of the probe changed the design. The distribution's default kernel command line disables the control-group memory controller, so bounding an integration's memory requires a one-time change at boot. Rather than start without the control and so imply a protection it cannot give, the framework refuses to start, with a stated reason, when the controller is missing. The second finding is that the input and output controller, although present in the kernel, is not delegated to an unprivileged user's service manager [48], so I/O bandwidth became a stated residual risk instead of a feature that could be built.

The second question was whether Home Assistant could run inside a sandbox at all. Its own entry point loads the web frontend and the recorder, the weight a sandbox exists to avoid, so the sandbox constructs the platform's core object directly and sets up only what the integration needs. An ordinary polling integration loaded and published its sensor against this reduced instance.

The third question was whether confinement fits, and memory decides it. Measured as proportional set size [49], a sandbox costs 56.5 MB without platform components and 135.6 MB with all ten, so 60% of the device's 4 GB holds 17 to 43 sandboxes against a mean of 4.02 community integrations per installation [1]. The design is therefore technically feasible on the hardware that requirement C4 names, with a margin of at least four times the mean.

## 10.2 Economic feasibility

The framework adds no licence, service or hardware cost: it runs on the device the householder already owns, and its supervisor and mediator use only the Python standard library. Avoiding dependencies is also a security decision, because each one adds code and maintainers that must be trusted, the supply-chain exposure this project addresses [23]. The real costs are memory, quantified above, and maintenance: the sandbox builds the platform's core object outside its documented entry point, so a Home Assistant release may require the framework to be updated.

## 10.3 Legal and ethical feasibility

No personal data about anyone other than the author was collected, and every measurement ran on the author's own device and test installation. Six integrations contacted live third-party services at their normal polling rates: four public services without credentials, and two through free accounts the author created for the purpose. Two further integrations that control devices on the home network were tested against simulated devices rather than real ones. The adversarial work reproduces the attack patterns of published disclosures and research [6], [9] with integrations written for the evaluation, not against the vulnerable versions of real integrations, so no third party's software or users were attacked. The cost of this choice is that the adversary exercises classes of attack rather than their historical instances. One class, an escape through a shared terminal found by code review, was described and fixed but deliberately not developed into a working exploit.

## 10.4 Operational feasibility

The framework is operable by a householder once installed, and installation is the step that demands most. Enabling the memory controller requires a one-line change to the boot configuration and a restart, the only step that needs administrative access to the device. After installation, every decision a user makes, including approving an integration's permissions, is taken in Home Assistant's own interface, with no terminal step.

The framework also fits the existing ecosystem without asking anything of it. It requires no change to any integration or to Home Assistant's code, and adds only one integration of its own, the bridge, to the household's installation. A 2026 request for comment proposes running integrations on separate machines, motivated mainly by reliability and scale [11]. Relocation changes where untrusted code runs but not what it may do, so if that proposal is adopted it would be a substrate for the enforcement described here rather than a substitute for it.

## 10.5 Scheduling feasibility

The work was staged so that each risky question was answered before the work that depended on it: the probe preceded the architecture, and the memory budget preceded the evaluation. Engineering stopped at a declared cut-off on 8 October 2026, and the report was written afterwards, with one full rerun of every measurement at the final version of the code. Reproduction on a freshly imaged device awaits a spare memory card and remains open.
