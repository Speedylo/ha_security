"""The confinement framework's supervisor-side code.

Layout follows Chapter 6 rather than convenience, so that a section of the report and the
module it describes can be read together:

    cgroup.py      §6.4.1  where a sandbox may be placed, and by whom
    namespaces.py  §5.7.3  the seven namespaces, and whether this host grants them
    preflight.py   §6.4.2  what is checked before anything is confined, and the N3 refusal
"""
