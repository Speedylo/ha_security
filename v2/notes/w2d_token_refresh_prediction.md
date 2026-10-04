# W2 (d) — an OAuth token refreshed inside a sandbox: design and prediction

**Written 2026-10-04, before the confined runs.** §4 is never revised; outcomes are appended below it.

## 1. What has been established already

The subject is `trakt_tv` 0.17.0 (uniform corpus), unmodified. It authenticates through Home
Assistant's standard helper, `OAuth2Session.async_ensure_token_valid` over
`LocalOAuth2Implementation`, so its refresh is the one most OAuth integrations perform. It is the only
free OAuth integration in either corpus. The others need LG, Amazon, Xiaomi, Octopus Energy or
Enphase accounts, or a device.

Feasibility, checked 2026-10-04 with Younes's own Trakt account:
- Trakt now issues only **public (PKCE) clients, with no client secret**. `trakt_tv`'s setup form
  requires a secret, but the helper sends `client_secret` only when it is non-empty, so an entry with
  an empty secret refreshes as a public client.
- Trakt's device-code login works for a public client.
- A refresh sent **exactly** as the helper sends it (form-encoded `grant_type`, `client_id`,
  `refresh_token`) is accepted, and **the refresh token rotates**: it is single-use.
- A first attempt got HTTP 403 because it carried Python's default `User-Agent`. Cloudflare, in
  front of Trakt, filters that; Home Assistant's own `User-Agent` passes. Inside the sandbox, the
  integration uses (B)'s own client session, so it sends Home Assistant's.

The credentials live in `~/.config/capstone/trakt.json` on the Pi (mode 600). They are never
printed, logged or committed, and every run's output is scrubbed of them before it is written.

## 2. The question

`async_ensure_token_valid` refreshes a token that is about to expire and then calls
`hass.config_entries.async_update_entry` with the new pair. Confined, that write lands in **(B)**,
the sandbox's private instance, and is persisted only in the sandbox's data directory
(`/sandbox/data/.storage`). Neither (A) nor the mediator ever holds the token: it travels inside the
integration's own TLS connection. Because the refresh token is single-use, **whether the
integration stays logged in across a respawn depends entirely on whether that data directory
persists**. That is a phase nobody has observed, because no credentialed confined run so far has
outlived a token.

## 3. Design

The harness builds the config entry directly (no flow): `auth_implementation`, `client_id`, an
empty `client_secret`, and the stored token, with `expires_at` set in the past so that the first poll
refreshes. Egress is declared for `api.trakt.tv:443`, which serves both the API and the token
endpoint. Before the sandbox's root is removed, the harness reads (B)'s stored config entry from the
data directory and keeps the new token aside, in a mode-600 file, so the account stays usable.

| Run | Token given to the sandbox | Stands for |
|---|---|---|
| **1** | the stored token, marked expired | a sandbox whose token expires while it runs |
| **2** | the same original token again, now spent by run 1 | a respawn **without** a persistent data directory |
| **3** | the token run 1's sandbox stored in (B) | a respawn **with** a persistent data directory |
| **C** | as run 3, with no egress declared | the control |

## 4. Predictions

| | Prediction | Confidence |
|---|---|---|
| **K1** | Run 1: the refresh happens inside the sandbox, through one granted egress to `api.trakt.tv:443`; the entry loads and its sensors publish | medium — Cloudflare and the integration's own API calls are the risks |
| **K2** | The new pair exists only in (B)'s storage in the sandbox's data directory. The durable log records the egress decision and never the token | high |
| **K3** | Run 2, the spent token: the refresh is refused, the entry does not load, and the integration's own setup reports an authentication failure | high |
| **K4** | Run 3, the token (B) stored: the entry loads again | high |
| **K5** | Arm C: the egress is refused with its clause, the refresh cannot happen, and the entry does not load | high |
| **K6** | Something not listed is found | medium |
