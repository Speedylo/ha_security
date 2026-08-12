"""Compatibility shim for the Home Assistant API.

This package deliberately shadows the real ``homeassistant`` distribution. It is
placed first on the sandboxed process's ``sys.path``, so an unmodified HACS
integration's ``import homeassistant...`` resolves here instead of to real HA.

Calls that would normally touch HA's in-memory state go out over a socket to the
supervisor, which enforces the integration's declared manifest.

Nothing in this package is trusted. It runs inside the sandbox alongside the
untrusted integration, which is free to bypass or rewrite any of it. All
enforcement lives in the supervisor on the other end of the socket; the shim is
a convenience layer, not a security boundary.
"""

__version__ = "0.1.0"
