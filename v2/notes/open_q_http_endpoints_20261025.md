# Open question (2026-10-25, to come back to): integrations' own web endpoints under confinement

Raised while rereading elttam's PwnAssistant article (final report [4]; interim "elttam (2023)").
An integration can add HTTP endpoints to Home Assistant's web server (`hass.http.register_view`) and
opt out of the login check (`requires_auth = False`); CVE-2023-27482 was an authentication bypass of
this kind in the built-in Supervisor integration. Table 2.1 now lists it as the "Web endpoints" row.

**Question:** what happens to such an endpoint when the integration is confined? Expectation, not
checked: it is registered on the sandbox's own minimal platform copy, so it is not reachable on (A)'s
real web server on 8123. Appendix G / F63 already records that the `http.register` clause is validated
but matched against no request. To settle: read the sandbox/supervisor code for how the minimal copy's
HTTP server is exposed (if at all), then test with an integration that registers a `requires_auth =
False` view, confined and unconfined (prediction note first). Likely examiner question at the defence.
