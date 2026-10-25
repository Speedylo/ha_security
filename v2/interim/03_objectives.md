# 3 Project Objectives

The aim of the project is to give the owner of a Home Assistant installation control over what each community integration may do, without asking integration authors or the platform's developers to change anything. This aim has an engineering half, building the mechanism, and a research half, measuring whether it can be used on integrations that already exist. It breaks down into four objectives:

1. **Design and build a confinement framework** in which each community integration runs in its own sandbox, its permissions are declared and approved by the owner in the platform's own interface, every action it takes on the home is checked against those permissions, and every action is recorded.
2. **Evaluate its security** by running two published attack techniques, and attacks derived from the project's own threat model, against the same integration with and without confinement.
3. **Measure its compatibility** by loading real community integrations, unmodified, with and without confinement, and checking that those that work normally still work.
4. **Measure its cost** in memory and delay on a Raspberry Pi 5, a device typical of the small computers on which households run the platform.

The project deliberately leaves some questions aside. Add-ons, a different kind of extension, already run in separate containers and are out of scope. So are flaws in the platform itself, such as authentication bypasses: the threat considered is a hostile or exploitable integration, not a vulnerable platform. The framework limits what an integration may do but does not decide whether its author is malicious, and an integration that misuses a permission the owner granted it is acting within its approval. Whether the code downloaded can be trusted at all, the question of software supply-chain security, is a separate field with its own literature (Ladisa et al., 2023).

The expected outcome was stated before any measurement as a claim that the evaluation could disprove: that unmodified community integrations can be confined at a cost worth paying. Each of objectives 2 to 4 was given in advance a result that would count against it, so the evaluation could fail as well as succeed. Section 4 reviews what earlier work has achieved towards the same aim.
