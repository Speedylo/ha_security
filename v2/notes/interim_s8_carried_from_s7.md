# Material moved from interim §7 to §8 Discussion (2026-10-25)

Younes agreed (after the comparison with the six past capstones): §7 keeps results only; the evaluation's own
check and the defects found by the end-to-end runs go to §8 as "how far the results can be trusted".
Text as drafted in §7, to be reworked for §8.

## The defects found by running real integrations (was §7.2)

These runs were also where the most useful defects were found. The platform's recommended way of making web
requests turned out to need a network feature that a new sandbox does not provide, so the first real
integration tested could not make a single request, although every purpose-built test had passed; the feature
was enabled inside the sandbox without opening any route out. In another case, a command from `scheduler`
reached the platform without its target device, a defect in the framework that was fixed with a test that
failed before the fix.

## The evaluation checked against itself (was §7.4)

A fourth falsifier was fixed for the evaluation itself: it would fail if it reported a requirement as met
without demonstrating it, or an overall figure that hid a breakdown it possessed. It fired twice during
development, both times found by reading the report as a whole. In response, every claim in the report, 153
in all, was registered with its evidence and a pass criterion and then re-measured on one fixed version of the
code. Of the 153, 119 held as stated, 27 held only in a narrower form, 5 rested on argument rather than
measurement, and 2 were withdrawn; the report states each claim in the form its evidence supports.

The same campaign tested the instruments. Faults were injected into the running system, the mediator was sent
4,864 malformed requests, and 53 deliberate defects were introduced into the code to check that the test
suites detect them, of which all but one were caught, the remaining one being equivalent to the original code.
Across the campaign and the work that followed, 63 findings were recorded, one of them critical: the terminal
route described in Section 7.1. None changed the verdict on any of the three assertions. A final rerun of every
experiment from a fresh copy of the code at the submitted version confirmed the results reported here, with
one timing faster than its stated band, which is why that figure is given as a range.

## Also planned for §8

- Comparison with the literature of §4 (as Ait Achour compares with his baseline): Corno & Mannella's
  threat model and their heap-walk result; SandTrap (confining unmodified Node-RED nodes); permission systems
  for browser extensions and SmartThings apps.
- The bounds of each assertion: no independent adversary; named set limited by accounts and devices; a mean
  rather than a distribution, memory at rest; one platform release.
