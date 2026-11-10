# 6. Logic Model Framework

This section traces the project from the people it serves, through what it assumed and used, to what it produced and what that may change.

## 6.1 Target population

The primary population is the households that run community integrations: 379,326 of the 669,743 installations that report analytics run the Community Store, each with a mean of 4.02 community integrations (Home Assistant, n.d.-d). They carry the risk without any means of acting on it. The second population is the authors of the 4,220 community integrations, most of them volunteers; the framework leaves their code unchanged and asks only for a manifest declaring what an integration needs. The third is the Home Assistant project, which would have to own any lasting fix.

## 6.2 Underlying assumptions

The project rests on five assumptions. An integration can run in a sandbox without any change to its code, and a home device has enough memory to confine the integrations a household typically runs; the evaluation tested both, and both held. A manifest can be written for a real integration, which held for each of the fifteen run from start to finish, although the project wrote every one of them. The Linux kernel's isolation features are sound, and the person approving a grant understands what it allows; neither could be tested, so both are stated as limits.

## 6.3 Resources and challenges

### 6.3.1 Resources

The project used one device, one fixed platform release and public data. The device is a Raspberry Pi 5 with 4 GB of memory, at the small end of the hardware households run Home Assistant on, and every measurement was taken on it. Home Assistant 2026.8.3 was fixed so that every result can be reproduced. The framework's supervisor and mediator use only Python's standard library, because a security tool that brings its own dependencies adds code that must itself be trusted. The code was written with AI assistance, as Section 13 describes.

### 6.3.2 Challenges

Four challenges shaped the work. Neither the integrations nor the platform could be changed, so confinement had to be imposed from outside. The platform changes with every release, so the results describe only the release measured. Most integrations need an account or a physical device before they can do anything, which limited how many could be run from start to finish. Finally, the project tested its own work, and no independent adversary has attacked the framework.

## 6.4 Activities

The activities followed the method of Section 8: requirements, then the threat model, then an architecture chosen against alternatives, then the implementation with its test suites and a hostile integration to attack it. The evaluation compared every result with the same integrations run unconfined, and a verification campaign then tested the evidence itself. After the interim report, the bridge was extended to 29 kinds of device, fifteen integrations were run against a real installation, and the whole evaluation was repeated on the finished code.

## 6.5 Outputs

The outputs are the deliverables of Table 3.3: the framework and its bridge integration, 35 test suites and the 92 planted defects that test them, two samples of real integrations with the harness that runs them, and a verification record that links each claim in this report to its evidence.

## 6.6 Outcomes

### 6.6.1 Short-term outcomes

The short-term outcomes are achieved and measured (Section 12). The two published attack techniques that motivated the project succeed without confinement and find nothing with it. Confinement stopped no integration from loading, fifteen worked from start to finish while confined, and the reference device holds at least 17 sandboxes, about four times what an average household needs.

### 6.6.2 Intermediate outcomes

The intermediate outcomes are plausible but not yet shown. Integrations beyond the evaluation would need manifests, written by their authors or supplied with the installation; the framework would have to run a household's integrations for months; limits on disk and network bandwidth would need a step with administrator rights at installation; and an independent adversary would have to attack it. None of these needs a new research result.

### 6.6.3 Long-term outcomes

The long-term outcome lies with the platform. Because a check inside the platform's process can be reached by the code it restricts (Corno & Mannella, 2022), a lasting fix would require Home Assistant to place community integrations behind a process boundary itself, and to let administrators limit a user to some devices, so that the mediator's own access could be narrowed. The project cannot make that change, but it supplies the evidence a proposal would need: what confinement costs, what a declaration must express, and which threats it closes and which it leaves open.
