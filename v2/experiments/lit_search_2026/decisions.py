"""Screening decisions for screening.csv (protocol §5). Every record not named here was excluded on
its title as not about third-party code running on a smart-home hub or gateway. Re-running this file
rewrites only the stage/decision/reason columns."""
import csv

T = "title"
A_ = "abstract"
F = "full text"
FA = "abstract (full text not obtained)"

DECISIONS = {
    # --- B: adjacent (cited in §7 where it changes what §7 says) ---
    "R0226": (F, "B", "P3CRID threat model (2026): names Home Assistant integrations as an attack vector; its only mitigation for integration code from GitHub is the owner reviewing it. No run-time confinement proposed. Supports the gap."),
    "R0497": (FA, "B", "TAPShield (Euro S&P 2025): SGX + language-level sandboxes (vm2, SandTrap) for apps on Node-RED and IFTTT; abstract reports security, performance and compatibility trade-offs on real-world apps. Not Home Assistant. Full text not obtained (IEEE paywall; Younes's institution has no access; no repository copy at KTH DiVA, Lund, ResearchGate, 2026-10-15). Judged on the abstract (Younes, 2026-10-15): §7's claim is narrowed so that it holds whatever its compatibility evaluation measured."),
    "R0057": (FA, "B", "SHERLOC (2026): cryptographic enforcement of app permissions on a pub/sub smart-home platform; a new system that apps are written for, not confinement of existing extensions; not Home Assistant."),
    "R0003": (F, "B", "Home Assistant work at the network layer: ESPHome Native API vs MQTT over TLS 1.3. Does not concern integration code; does not change §7."),
    # --- C after abstract or full text ---
    "R0007": (A_, "C", "AI-generated podcast episode on Zenodo (Gemini + TTS), record deleted by Zenodo 2026-06-26; container-level advice, not scholarly."),
    "R0008": (A_, "C", "AI-generated podcast episode on Zenodo, record deleted; opinion on Home Assistant stability, not scholarly."),
    "R0011": (A_, "C", "White paper on a LAN-only Tuya to Apple Home bridge; no confinement of third-party code."),
    "R0012": (A_, "C", "AI-generated podcast episode on LLM agents in Home Assistant; not scholarly."),
    "R0014": (A_, "C", "Podcast episode on workflow automation at scale; not about hub extensions."),
    "R0017": (A_, "C", "Home security device built on Home Assistant; no confinement."),
    "R0021": (A_, "C", "LLM repair of Home Assistant YAML configuration; user configuration, not integration code."),
    "R0031": (A_, "C", "MQTT fuzzers evaluated by mutation testing on Home Assistant; testing, not confinement."),
    "R0032": (A_, "C", "Survey of multi-user access control preferences in dementia care; users, not third-party code."),
    "R0033": (A_, "C", "Security of CI plugins (GitHub Actions etc.); not a smart-home hub."),
    "R0037": (A_, "C", "Port-forwarding services; network exposure, not extensions."),
    "R0039": (A_, "C", "Matter device security measurement; device and network layer."),
    "R0048": (F, "C", "Thesis on cross-program privacy flows in mobile and IoT ecosystems; Home Assistant mentioned once in passing; no hub confinement."),
    "R0144": (A_, "C", "Conflict resolution between user automation rules; not third-party code."),
    "R0175": (A_, "C", "IFTTT applet safety framework (no abstract; title only); vendor-cloud applets, no evidence of confining existing code."),
    "R0182": (A_, "C", "Vulnerability scanning framework for devices; device layer."),
    "R0209": (A_, "C", "General survey of smart-home security in smart cities."),
    "R0229": (A_, "C", "Zero-trust review for smart environments; network and identity layer."),
    "R0231": (FA, "C", "Community-driven variability in software ecosystems (Bitcoin as example); not security or confinement."),
    "R0240": (A_, "C", "Book chapter on Raspberry Pi privacy hacks; not hub extensions."),
    "R0243": (A_, "C", "User dashboard for device security settings across vendors."),
    "R0248": (A_, "C", "Zero trust vs perimeter under DDoS on devices; network layer."),
    "R0261": (F, "C", "Information-flow analysis of users' trigger-action automations (PETS 2026); user rules, not third-party code."),
    "R0267": (A_, "C", "Penetration testing of an IoT testbed; network layer."),
    "R0271": (A_, "C", "LLM analysis of Amazon reviews for security concerns."),
    "R0278": (A_, "C", "Empirical study of tests in open-source IoT software; testing, not confinement."),
    "R0281": (FA, "C", "Systematic mapping of smart-home security research 2000-2025 (6,313 papers); maps themes, builds nothing."),
    "R0289": (A_, "C", "Scoping review of human-centred smart-home security."),
    "R0322": (A_, "C", "Local browser-to-device control protocol; device layer."),
    "R0351": (A_, "C", "Exposed MQTT deployments; network exposure."),
    "R0393": (A_, "C", "STRIDE/LINDDUN analysis of network filtering in smart homes; network layer."),
    "R0465": (A_, "C", "Multi-protocol gateway simulated in ns-3; connectivity, not extensions."),
    "R0004": (A_, "C", "Cross-vendor device authentication (Atlas); device identity."),
    "R0492": (A_, "C", "Hardware air-gap gateway for audio privacy; not extensions."),
    "R0529": (A_, "C", "Knowledge graph of security standards."),
    "R0541": (A_, "C", "Automated VAPT for smart-home devices; device and network layer."),
    "R0608": (A_, "C", "MUD + software-defined perimeter for residential IoT; network layer (cites [15])."),
    "R0611": (FA, "C", "Survey of post-Matter mesh security (cites [5], [15], [25]); protocol and mesh layer."),
    "R0612": (A_, "C", "Security gateway for generative AI applications; not smart home (cites [15])."),
    "R0613": (A_, "C", "Methodology for designing a secure smart home; no confinement (cites [5])."),
    "R0614": (A_, "C", "RBAC flaws in vendor-cloud sharing features; users, not third-party code."),
    "R0609": (A_, "C", "Energy management model (cites [15]); not security of extensions."),
    "R0610": (A_, "C", "Network reliability by redundancy (cites [15]); not extensions."),
    # --- Google Scholar, S1 by hand (2026-10-15 19:19); judged on Scholar's snippet ---
    "R0627": ("abstract (Scholar snippet)", "C", "Behavioural privacy prediction built with Flask and Home Assistant; user privacy, not integration code."),
    "R0628": ("abstract (Scholar snippet)", "C", "Edge-IoT health architecture feeding Home Assistant over MQTT; system integration."),
    "R0629": ("abstract (Scholar snippet)", "C", "Controller-less consumer IoT architecture compared qualitatively with Matter and Home Assistant."),
    "R0633": ("abstract (Scholar snippet)", "C", "Review of a home-automation product (qToggle) against openHAB, Home Assistant and others."),
    "R0639": ("abstract (Scholar snippet)", "B", "Thesis (2026) on the security of home-automation communication protocols, using Home Assistant's Bluetooth proxy; network layer, does not change §7."),
}


# Younes's review, 2026-10-15: of the B rows only P3CRID stays B; the others are dropped to C. TAPShield's
# full text could not be read, so nothing in the submission rests on it.
YOUNES = "Younes's review 2026-10-15: dropped (only P3CRID kept as B). My first call: B. "
for _rid in ("R0003", "R0057", "R0497", "R0639"):
    _stage, _dec, _why = DECISIONS[_rid]
    DECISIONS[_rid] = (_stage, "C", YOUNES + _why)


def apply():
    rows = list(csv.DictReader(open("screening.csv")))
    for r in rows:
        stage, decision, reason = DECISIONS.get(
            r["id"], (T, "exclude", "title: not about third-party code on a smart-home hub or gateway"))
        r.update(stage=stage, decision=decision, reason=reason)
    with open("screening.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(Counter((r["stage"].split(" (")[0], r["decision"]) for r in rows))


if __name__ == "__main__":
    apply()
