# 5. Engineering Standards

This section presents the standards the project follows, in risk management, least privilege, audit and network addressing. For each, it states what the standard asks, how the project meets it and, where the project departs from it, why.

## 5.1 Risk management

The threat model follows ISO 31000 (International Organization for Standardization, 2018), which fixes the order of a risk-management process: establish the context, identify risks, analyse and evaluate them, then treat and monitor them. Because the standard prescribes no technique for identifying risks, the project uses STRIDE (Shostack, 2014) for that step, as Section 8 describes. The one departure concerns impact. Instead of a generic scale, impact is rated on the value of the household's assets, because no general scale has a level for defeating a safety function in a home.

## 5.2 Least privilege

The standard closest to the platform's problem is ETSI EN 303 645, the European baseline for consumer IoT security, whose scope names "connected home automation and alarm systems, especially their gateways and hubs" (ETSI, 2024, Section 1). Its provision 5.6-7 states that "software should run with least necessary privileges" (ETSI, 2024, Provision 5.6-7), and NIST SP 800-53 sets the same principle as control AC-6 (Joint Task Force, 2020). Home Assistant's integration model does the opposite, since every integration runs with all of the platform's privileges. The framework meets the provision by giving each integration only what its manifest declares, and applies it to itself, since the mediator acts on the platform as a user without administrator rights. One departure is stated: the filter on system calls blocks the calls that are dangerous rather than allowing only those an integration needs, because the other isolation features have already removed almost everything those calls could reach (Appendix [S].2).

## 5.3 Audit

Audit standards say what a system may do when it can no longer keep its record. Common Criteria component FAU_STG.4 requires a design to choose, for when its record is full, between ignoring audited events, preventing them and overwriting the oldest records (Common Criteria Recognition Arrangement, 2017). NIST SP 800-53 control AU-5 requires an alert when recording fails and leaves further action to the organisation, with shutdown as an optional enhancement, AU-5(4) (Joint Task Force, 2020). The framework chooses to stop, because a decision that cannot be recorded must not be carried out. Every decision is written to disk before it is acted on, and if a write fails the mediator stops, closing every sandbox's channel. A single sandbox that floods the mediator with refused requests is stopped on its own instead, so that the other integrations keep running.

## 5.4 Network addresses

Two address standards define what the network gate refuses. RFC 1918 reserves the private ranges that home routers give the devices in a house (Rekhter et al., 1996), and RFC 6598 reserves a range used by internet providers and by some private overlay networks (Weil et al., 2012). The gate refuses both, together with the device's own and link-local addresses, unless the manifest separately grants the home network. A grant for a public host therefore cannot be turned into a route to the household's router or to the device itself.
