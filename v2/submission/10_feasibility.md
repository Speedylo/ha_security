# 10. Feasibility Study

This section assesses whether the project could be carried out and whether its result could be used, under four headings: technical, economic, legal and ethical, and operational.

## 10.1 Technical feasibility

The design depends on features of the Linux kernel, so the reference device was tested for them before the architecture was fixed. On the Raspberry Pi 5, an ordinary user could create the isolated environments from which a sandbox is built, and the kernel could restrict which system calls a process may make (Linux man-pages project, n.d.-b, n.d.-d). The framework therefore needs no administrative privilege, which matters for security, because a confinement tool that must run with full privileges enlarges the attack surface it exists to reduce. Two findings of the test changed the design. The device's default settings switch off the kernel's memory limits, which must be enabled once at boot; rather than run without them and imply a protection it cannot give, the framework refuses to start, and says why, when they are missing. The kernel's means of limiting how fast a process reads and writes the disk is not available to an ordinary user (systemd, n.d.), so that rate is not bounded and is stated as a remaining risk. Memory then decides how many integrations fit, and the device holds at least 17 sandboxes, about four times what an average household needs (Section 12.3). Confinement is therefore technically feasible on the kind of device the project targets.

## 10.2 Economic feasibility

The framework adds no licence, service or hardware cost. It runs on the device the household already owns, and its supervisor and mediator use only Python's standard library. Avoiding outside packages is also a security choice, because each one adds code and maintainers that must be trusted, which is the supply-chain exposure this project addresses (Ladisa et al., 2023). The real costs are memory and maintenance: the sandbox starts Home Assistant's core in a way the platform does not document, so a new release may require the framework to be updated.

## 10.3 Legal and ethical feasibility

The project needed no one else's consent, because it involved only its own device, test installations and accounts. The attacks were reproduced with integrations written for the evaluation rather than against real integrations or their users, so no third party was exposed to them. Section 8.6 describes these safeguards.

## 10.4 Operational feasibility

Once installed, the framework asks nothing technical of a householder. Installation needs one change to the device's boot settings and a restart, and every later decision, including approving an integration's permissions, is made in Home Assistant's own interface. Neither Home Assistant nor any integration has to be changed. Each confined integration does, however, need a manifest before it can act through the mediator, and none ships one today; every manifest in the evaluation was written by the project. An integration without one still loads, confined and refused every mediated action, so the main open question for adoption is who would write manifests at scale: their authors, automated analysis or curators.
