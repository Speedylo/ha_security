# F45, option 2 — the mediator as a restricted user: design, criteria and predictions, before the code

**2026-10-06.** Younes chose option 2: correct R3's wording, and test whether the mediator can run
without admin.

## What R3 says, and what the release shows

§8.8 and §5.15.3 say Home Assistant has "no read-only variant and no per-domain variant" of a
long-lived token, so the mediator must hold full authority. Read in 2026.8.3, permissions belong to
users and a token carries its user's. There are three built-in groups. *Admin* can do everything.
*User* (`system-users`) controls every entity but is refused the admin-only commands and services.
*Read-only* can read every entity and nothing else. Underneath is an entity policy (read, control,
edit; by entity, domain, device, area), enforced in `get_states`, `subscribe_entities` and entity
service calls. A custom group with a per-domain policy has no settings screen. It can only be
written into `.storage/auth` by hand.

The mediator calls `get_config`, `config/entity_registry/list`, `get_states`, `subscribe_entities`,
`call_service` and the bridge's five commands. All but the bridge's are open to a non-admin user.
The bridge's are admin-only by this project's choice (`require_admin`), which is why the mediator
holds an admin token today.

## The change

1. **The bridge's gate** becomes: an admin, **or the one user designated as the mediator**. The
   designation is stored in the bridge's config entry, written only by a new admin-only command,
   `confine_bridge/designate_mediator`. So naming the mediator's account is an admin's act, and no
   other non-admin user can publish as a confined integration.
2. **`house_a`** creates a user `confine-mediator` in the built-in `system-users` group (non-admin,
   local only), mints a long-lived token for it through Home Assistant's own login flow, and
   designates it. The token is written to `~/.config/capstone/house_a_mediator.token`, mode 600,
   never printed.
3. **`RealPlatform`** connects with the mediator's token by default. The owner's admin token stays
   with `house_a`, for setup only.

## Criteria

**Arm R: the mediator as a regular user.**
- The mediator works unchanged as `confine-mediator`: `selftest_real_platform --restart` and all
  suites twice; `drive_demo` (flood, Repairs issue, restart); FI1 and FI4.
- A new section in `selftest_real_platform` checks, with the mediator's own connection, that the
  token is not an admin's. Each of these must be refused:
  - listing users (`config/auth/list`);
  - creating a user;
  - listing config entries' admin view;
  - restarting Home Assistant (`homeassistant.restart`, an admin service);
  - subscribing to a non-allowlisted event type.
- A non-admin user who is not the designated one is refused every bridge command.
- These checks fail against today's code, where the mediator's token is the owner's.

**Arm P: a per-domain policy, written by hand** (`verify/f45_policy.py`, run against a scratch copy of
(A)'s configuration, never the live one). A group whose policy grants read and control on one domain
(`sensor`) only:
- its user's `get_states` returns only `sensor.*`;
- its `call_service` on a `switch` entity is refused (Unauthorized);
- the same call on a sensor entity's domain service is accepted.

This shows whether the per-domain variant R3 says is missing is enforced when configured. It does
not make it supported: there is no screen for it.

## Predictions

- **Arm R works as is.** Everything the mediator does, other than the bridge, is open to a regular
  user, and `subscribe_entities` is filtered by read permission, which a regular user has for every
  entity. The admin-refusal checks all hold.
- **Arm P is enforced for reads and entity service calls**, and not for services with no entity
  target, which the entity policy does not cover. `config/entity_registry/list` is not filtered by
  policy, so a per-domain user still sees every registry row (ids and names, not states).
- **What the report can then say:** the mediator no longer needs admin. A compromised mediator gets
  a regular user's power, which is control of every entity, not the house's configuration, users or
  integrations. Narrowing it to declared domains is enforced by the platform's own policy engine,
  but only through an unsupported hand-written group. R3 becomes that, precisely, with the residual
  stated.

## Regression

A new tag; suites twice; `selftest_real_platform --restart`; `drive_demo`; `faults_pi_fixed.sh`;
`review_pi.sh`; `nordpool` end to end (the stand-in path, as a control that nothing else moved).
