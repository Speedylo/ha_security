# Where Home Assistant is installed: analytics snapshot (2026-11-09), NOT for the report

Source: https://analytics.home-assistant.io/data.json, `current`, last_updated 2026-11-09 12:51 UTC (opt-in analytics only).
Younes, 2026-11-09: for background and the defence; do not put the percentages in the report.

Active installations reporting: 725,532.

Installation type: OS 576,613 (79.5%), Container 129,255 (17.8%), Supervised 7,343 (1.0%), Core 7,047 (1.0%), other 0.8%.
Only OS installations report a board (481,593 do); Container and Core give no hardware, so a Pi running Container is not counted below.

Boards (share of the 481,593 OS installations that report one):
- Virtual machine (`ova`) 152,483 (31.7%); generic x86-64 94,411 (19.6%) → x86 / VM together 51.3%
- Raspberry Pi 4: 78,040 (16.2%); Pi 5: 47,571 (9.9%); Pi 3: 10,123 (2.1%) → Raspberry Pi together 135,734 (28.2%; 18.7% of all 725,532)
- Home Assistant Green 78,411 (16.3%); Yellow (Pi Compute Module) 9,351 (1.9%); ODROID/Khadas 5,182 (1.1%); generic aarch64 6,021 (1.3%)
- All small ARM boards together ≈ 234,700 (48.7% of reporting OS installs; 32.3% of all installations, a lower bound)

Reading: the Raspberry Pi is the largest single board family but not where most installations run; the Pi 5 is about one OS installation in ten.
Small ARM boards as a class (Pi + Green + Yellow + others) are about half of the OS installations that report a board.
