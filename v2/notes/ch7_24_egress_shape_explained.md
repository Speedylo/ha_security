# §7.24 explained from the ground up — what an integration does when it uses the internet

**Written 2026-09-03**, after the measurement in `experiments/egress_shape/`.
Companion to §7.24. This note is for defending the finding aloud, not for the report.

The report says three of §5.10.3's assumptions failed. This note builds up enough of how
networking actually works that the failures are obvious rather than technical, then gives you
the sentences to say and the questions to check yourself against.

---

## Part 0 — The problem this measurement solves

Integrations run in a sealed box. The box has no route to anywhere, which is safe and useless:
most integrations exist to talk to a weather service or a device on the shelf.

So the design's answer is a **doorman**. The integration asks to reach a place; the doorman checks
the integration's permission slip; if the place is listed, the doorman makes the connection itself
and hands the open line back. The integration never touches the network directly.

§5.10.3 wrote down what a permission slip looks like back in Chapter 5, before any of it was
built. The question this measurement asks is narrow and practical: **if we build that doorman
exactly as Chapter 5 describes, does it work?**

The answer is no, in three ways, and knowing that before writing the code is the entire point.

---

## Part 1 — Four ideas you need

### 1.1 Names and numbers are different things

You type `api.weather.com`. Your computer cannot use that. It has to turn the name into a number
— an address like `104.18.1.18` — before anything can happen. That translation is a lookup in
what is effectively a phone book, and it is a separate step from actually dialling.

Two steps, in order:

1. **Look up** — "what is the number for `api.weather.com`?" → `104.18.1.18`
2. **Dial** — "connect me to `104.18.1.18`"

Hold on to this: **the name exists at step 1 and is gone by step 2.** Step 2 sees a number and
nothing else.

### 1.2 There is more than one phone book

Python programs can look up a name in more than one way. The old, ordinary way is a function
called `getaddrinfo` — it blocks the program until the answer comes back. Modern programs that
juggle many things at once don't like waiting, so they use an asynchronous library instead.
Home Assistant uses one called **`aiodns`**.

They do the same job. They are completely separate pieces of code. **Watching one tells you
nothing about the other.**

### 1.3 A machine has many doors

An address gets you to a machine. It does not say *which service* on that machine. That is the
**port** — a number from 1 to 65,535. Web traffic normally uses 443. A database might use 5432.
A device on your shelf might use anything at all.

So a full destination is really two things: **which machine**, and **which door**.

### 1.4 Encryption happens between the two ends, not in the middle

When you see a padlock in a browser, the encryption is set up directly between your program and
the far-away server. Anything in the middle — a doorman included — carries sealed bytes it cannot
read.

That is normally a security *feature*. Here it is a constraint on what the doorman can ever know:
it can know **where** you went, never **what you said**.

---

## Part 2 — What the measurement did

Twelve of the most-installed community integrations were run in an ordinary, unconfined Home
Assistant with real internet access, and driven through their own setup screens while a recorder
watched every lookup, connection, datagram and encryption handshake.

### 2.1 The obstacle everyone assumed was fatal

Most of these need a login before they do anything. §7.18 concluded from exactly this that
egress behaviour simply could not be observed.

**That conclusion was too strong, and the reason is worth having ready.** Checking a password
*requires making the connection first*. There is no way for an integration to find out that your
API key is wrong without going and asking. So a deliberately wrong key still produces:

> look up the name → dial the number → set up encryption → send the request → **get refused**

Every step the doorman would have to handle has already happened by the time the refusal arrives.
The login wall stops you learning **how much** the ecosystem uses the network. It does not stop
you learning **what the traffic looks like**, and that second thing is what the doorman has to be
designed against.

This is a distinction worth being able to make quickly, because it looks like a contradiction
with §7.18 until you say which question each one answers.

---

## Part 3 — The three failures

### 3.1 We planned to listen at a door almost nobody uses

The plan was to catch integrations at step 1 — the lookup — because that is the only moment the
*name* is visible, and the permission slip is written in names.

Across all twelve integrations, **96% of lookups (3,073 of 3,193) went through `aiodns`**, not
through the `getaddrinfo` we were planning to watch. It was 93–97% for every single one, with no
outlier — which is the important part. A uniform number is not twelve integrations coincidentally
agreeing; it is the platform. Home Assistant hands every integration a pre-built internet
connection kit, and that kit has `aiodns` in it.

**A doorman listening only at `getaddrinfo` would see about one request in twenty-five.**

### 3.2 And the name doesn't survive to the moment of connection

This is the deeper half, and it is the one to lead with.

We might have hoped to skip the lookup and just watch the dialling instead. You cannot, because of
1.1: **at the moment of dialling there is no name, only a number.** The recorder caught
`pirateweather` connecting to `108.157.98.116:443`, and nothing in that call says
`api.pirateweather.net`.

Worse, looking up and dialling are done by **two different libraries** that don't share what they
know. So an enforcement point at the lookup has a name it cannot connect; an enforcement point at
the dial has a number it cannot judge. Neither alone can do the job.

### 3.3 Why that finding makes the design *stronger*

Here is the move, and it is the best thing to come out of the measurement.

There is a classic attack against any permission checker: get a *good* address approved, then
swap in a *bad* one before the connection actually happens. Check the name, then change the thing.
§5.10.5 already worried about this and called the answer "resolve then pin."

The fix the measurement forces is to have the sandbox's phone book hand back a **fake number** —
a placeholder that means nothing to anyone except the doorman, who alone can translate it back to
the real destination.

Follow what that does. The integration asks for a name and gets a placeholder. It dials the
placeholder. The doorman recognises it, looks up the *real* address itself, checks it, and
connects.

**The integration never holds a real address at any point.** So the swap attack isn't blocked —
it is *unavailable*. There's no gap between checking and using, because there is nothing real in
the sandbox to swap. That is the difference between a rule that is enforced and a rule that is
structural, and structural is the kind this project keeps trying to earn.

### 3.4 The permission slip was missing half of every address

§5.10.3's slip lists site names. It has no field for the door (1.3).

The integrations knocked on **8123, 6445 and 20086** as well as the ordinary 443. The slip cannot
express any of those — and, crucially, it cannot express them *in either direction*. It can't
grant door 6445 and it can't withhold it. **Granting a machine grants all 65,535 of its doors.**

That is a much larger permission than anyone writing the slip would think they were giving, and
it is exactly the over-breadth §5.10.4 refuses to allow for service calls. The same mistake had
been made one section later without anyone noticing.

### 3.5 Not all traffic is a conversation

We assumed every connection was a two-way conversation (TCP). `midea_ac_lan` sent **18 one-way
messages** (UDP) while looking for devices — shouting into the room rather than phoning someone.
The permission slip has no way to allow or refuse that either.

---

## Part 4 — What we assumed and got right

**Nothing needed to receive incoming connections.** Every integration in the sample only made
outgoing contact; none set itself up to be contacted. So the absence of an "incoming" permission
in §5.10.3 is fine — and it is now *tested* rather than an untested silence, which is a different
and better thing to be able to say.

**The doorman can never read content.** Every encrypted connection in the sample was set up
directly between the integration and the far end (1.4), with certificate checking on. Chapter 4
had already decided to *accept* the risk that an integration might smuggle data out through a site
it is legitimately allowed to reach (T09), calling it structural. That was an assumption. It is
now a measurement.

---

## Part 5 — The awkward one

`alexa_media` is the fourth most-installed integration in the corpus. During its own normal setup,
it connects to **the home hub itself** — the very machine it is running on.

The design treats "reaching something on the local network or the machine itself" as the dangerous
case, and denies it by default behind a separate, louder permission. That is a defensible position
and it is about to collide with a very popular integration doing something entirely legitimate.

Better to find that now than to ship a rule that breaks it. It also tells you the local-network
permission is not an edge case to be sketched in — it needs real design.

---

## Part 6 — Saying it out loud

**The 30-second version.**

> Before building the network doorman, we let twelve popular integrations actually use the
> internet and watched what they did. Three things in the Chapter 5 design were wrong. The
> biggest: we planned to check permissions at the moment a site name is turned into an address,
> but 96% of the time Home Assistant does that through a library we weren't watching — and by the
> moment of connection the name is gone and only the number is left. The fix is to have the
> sandbox's name lookup return a fake address only the doorman can decode. That turns out to be
> stronger than the original plan, because the integration then never holds a real address at
> all, so there's no window in which to swap a good destination for a bad one.

**If asked "why not just build it and fix it later?"**

> Every one of these would have surfaced inside working code, days in. The measurement took an
> afternoon. And this is the first time in the project that a measurement corrected a design
> *before* the code existed rather than after — the previous four corrections were all
> post-hoc.

**If asked "doesn't this contradict §7.18, which said egress couldn't be observed?"**

> They answer different questions. §7.18 asked how *much* egress the ecosystem needs, and that
> genuinely is blocked by the login wall. This asks what egress *looks like*, and that isn't —
> because checking a password requires making the connection, so a wrong password still shows
> you the whole path. §7.18's claim about demand stands unchanged; §7.24 extends its scope, it
> doesn't correct it.

**If asked "so a malicious integration just avoids your shim?"** — the sharpest question available,
have this ready:

> Yes, and it fails closed. The shim is a compatibility mechanism, not a security one. Security
> comes from the sealed box: the sandbox has no route to anywhere, enforced by the kernel. An
> integration that bypasses the shim doesn't get unfiltered internet — it gets nothing. So the
> shim's coverage determines how many *honest* integrations work, and never how much a *hostile*
> one can reach.

**If asked "what does this depend on that might change?"** — don't dodge this one:

> It depends on which DNS library Home Assistant ships. If they switch, honest integrations stop
> being able to reach the network until the shim is updated. That's a real maintenance cost and
> it belongs in Chapter 8. The consolation is the direction of the failure: it breaks
> compatibility, never containment.

---

## Part 7 — Check yourself

No answers written down. If you can't answer one, re-read the part it comes from.

1. Why can't the doorman check permissions at the moment the connection is made?
2. What is a placeholder address, and why does using one remove a whole class of attack rather
   than blocking it?
3. Why is 96% being uniform across all twelve integrations more informative than 96% on its own?
4. An integration is granted `api.example.com` under the Chapter 5 permission slip. What else has
   it just been granted, without anyone intending it?
5. §7.18 says egress cannot be observed. §7.24 observed it. Why is that not a contradiction?
6. Why can the doorman never see what an integration sends to a site it is allowed to reach — and
   why did Chapter 4 decide that was acceptable?
7. A hostile integration writes its own network code and ignores your shim entirely. What happens,
   and why is that not a security failure?
8. What is the strongest argument *against* this design that the measurement itself produced?
