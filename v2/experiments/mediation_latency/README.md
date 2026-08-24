# Experiment — what does one mediated request cost?

**Run:** 2026-08-24 · **Target:** Raspberry Pi 5, aarch64, Python 3.14.7 · **Feeds:** §5.11.4

§5.11 routes every mediated request over a Unix domain socket between the sandbox and the
mediator. N1 requires the overhead be small enough not to change how the platform is used,
and "small" is not a claim a design chapter should make without a number.

## Result

| Shape | median | mean | p95 | p99 | max |
|---|---|---|---|---|---|
| Request / response | **30.0 µs** | 30.0 µs | 30.4 µs | 33.9 µs | 564 µs |
| Push (receive only) | 6.4 µs | 6.4 µs | 6.6 µs | 6.9 µs | 24 µs |

*20,000 iterations, first 200 discarded as warm-up. Raw output in `results/pi5.json`.*

- About **33,000 mediated requests per second** at the median.
- A polling integration reading ten entities every thirty seconds spends **0.30 ms per cycle**
  in mediation — a factor of 10⁵ against its period.
- The distribution is tight: p99 within 13% of the median, which for an unattended system
  matters more than the median does.

## What was measured

A request/response round trip over `socketpair(AF_UNIX, SOCK_STREAM)` — not a bound path,
because §5.11.2's channel is an **inherited file descriptor** and measuring the thing the
design actually uses is worth the small extra effort.

Messages are realistic rather than empty: a length-prefixed JSON `entity.read` request and a
reply carrying state, attributes and the deciding clause pointer. Framing and parsing cost is
therefore included rather than measured away.

## Limits

- **This is a floor.** It excludes evaluating the manifest and writing the audit record. The
  real mediated path adds both, and Chapter 6 measures that. What this establishes is that
  the *channel* is not the bottleneck — worth knowing before building on it.
- **Idle machine, one sandbox.** No contention from other sandboxes or from Home Assistant
  itself. §5.6.3 measured up to six concurrent sandboxes for memory; latency under
  concurrency is not measured here.
- **Synthetic peer.** The mediator side is a stand-in that replies immediately. A real
  mediator does work between receiving and replying, which is the point of the first limit.
- **Python on both ends**, matching the design. A different implementation language would
  move these numbers, most likely downward.

## Reproducing

```bash
python3 measure.py --iterations 20000 --json results/pi5.json
```

Needs only the standard library.
