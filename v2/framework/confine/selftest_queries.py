"""Questions from the household to a confined integration, and the answers it gives.

Bridge step 4 (`notes/bridge_types_step4_prediction_20261025.md`). A calendar view or a forecast
card asks the integration for events or a forecast. The question travels the command path; the
answer comes back from the **untrusted** side, so the mediator relays it only if it has the listed
shape, within 500 items and 256 KiB, and records it by its shape, never its content.

    Q1   the listed questions are pushed exactly
    Q2   any other question, or data, is refused
    Q3   a well-formed answer is relayed unchanged
    Q4   a malformed answer is refused under QUERY_ANSWER and not relayed
    Q5   no answer's content reaches the durable log
    Q6   an answer attached to an ordinary command is not relayed
    Q7   a picture of a listed type, its bytes starting with that type's signature, is relayed
    Q8   a picture of exactly 512 KiB is relayed
    Q9   any other picture answer is refused under PICTURE_ANSWER and not relayed
    Q10  no picture reaches the durable log; each record gives its type and size

Run:  python3 -m confine.selftest_queries
"""

from __future__ import annotations

import base64
import math
import sys
import tempfile
import threading
import time
from pathlib import Path

from .audit import AuditLog
from .channel import Channel, ProtocolError
from .mediator import AMBIENT, COMMAND_DATA, COMMAND_SERVICES, Mediator, deny_everything
from .selftest_push import component

try:
    from .mediator import QUERY_ANSWER
except ImportError:  # before step 4 there is no such rule
    QUERY_ANSWER = "(no QUERY_ANSWER rule)"
try:
    from .mediator import PICTURE_ANSWER
except ImportError:  # before batch B4b there is no such rule
    PICTURE_ANSWER = "(no PICTURE_ANSWER rule)"

results: list[bool] = []
CAL, WEATHER = "calendar.demo_bins", "weather.demo_home"
DOOR, MAP = "camera.demo_door", "image.demo_map"
OWNED = {CAL: "demo", WEATHER: "demo", "sensor.demo_value": "demo", "switch.demo_power": "demo",
         DOOR: "demo", MAP: "demo"}
START, END = "2026-10-26T00:00:00+01:00", "2026-11-02T00:00:00+01:00"
EVENTS = [{"summary": "Dentist, Dr Example", "start": "2026-10-27T09:00:00+01:00",
           "end": "2026-10-27T10:00:00+01:00", "location": "Darmstadt"},
          {"summary": "Bio bin", "start": "2026-10-28", "end": "2026-10-29",
           "description": "Put it out the night before"}]
FORECAST = [{"datetime": "2026-10-26T12:00:00+00:00", "condition": "rainy", "temperature": 12.5,
             "templow": 6.0, "precipitation": 3.2, "precipitation_probability": 80,
             "wind_bearing": 225, "is_daytime": True},
            {"datetime": "2026-10-27T12:00:00+00:00", "condition": "cloudy", "temperature": 11,
             "templow": None, "wind_bearing": "SW"},
            {"datetime": "2026-10-28T12:00:00+00:00", "condition": "sunny", "temperature": 14.0,
             "humidity": 55, "uv_index": 2.5}]


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(bool(condition))
    print(f"{'  ok  ' if condition else '  FAIL'}  {claim}{f'  — {detail}' if detail else ''}")


class House:
    """Enough of a platform: who owns what, and what each question's asker was told."""

    def __init__(self) -> None:
        self.owners = dict(OWNED)
        self.results: dict[int, dict] = {}

    def command_result(self, command: int, ok: bool, error: str | None = None,
                       answer: list | None = None) -> None:
        self.results[command] = {"ok": ok, "error": error, "answer": answer}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        house = House()
        mediator = Mediator(policy=deny_everything, log=AuditLog(path=root / "queries.jsonl"))
        mediator._platform = house  # type: ignore[assignment]
        mine, theirs = Channel.pair()
        mediator.register("demo", Channel(mine), component=component(root, "demo", []))
        sandbox = Channel(theirs)
        ids = iter(range(1, 10_000))

        def ask(entity: str, service: str, data: dict | None) -> tuple[dict, dict | None]:
            before = len(mediator.log.records())
            question = {"command": next(ids), "integration": "demo", "entity_id": entity,
                        "service": service, "data": data or {}}
            mediator.command(question)
            sandbox.sock.settimeout(0.5)
            records = [r for r in mediator.log.records()[before:]
                       if r.get("kind") == "decision" and r.get("op") == "entity.command"]
            try:
                pushed = sandbox.recv()
            except (TimeoutError, OSError, ProtocolError):
                pushed = None
            return (records[0] if records else {}), pushed

        def answer(pushed: dict, payload: object) -> tuple[dict, dict]:
            """The sandbox answers; what the platform was told, and the answer's own record."""
            if not pushed:
                return {}, {}   # never asked, so nothing to answer (before step 4)
            sandbox.sock.settimeout(10)
            before = len(mediator.log.records())
            frame = {"id": next(ids), "op": "entity.command_result",
                     "command": pushed.get("command"), "ok": True, "answer": payload}
            # From a thread, while the mediator serves: a large answer does not fit the socket
            # pair's buffer, and a send that waits for a reader that is not running never ends.
            sending = threading.Thread(target=sandbox.send, args=(frame,))
            sending.start()
            deadline = time.monotonic() + 3
            while (sending.is_alive() or pushed.get("command") not in house.results) \
                    and time.monotonic() < deadline:
                mediator.serve(timeout=0.02)
            sending.join(1)
            sandbox.sock.settimeout(0.5)
            try:
                sandbox.recv()
            except (TimeoutError, OSError, ProtocolError):
                pass
            told = house.results.get(pushed.get("command"), {})
            records = [r for r in mediator.log.records()[before:] if r.get("kind") == "decision"]
            return told, (records[-1] if records else {})

        print("\nQ1 — the listed questions\n")
        for entity, service, data in ((CAL, "get_events", {"start": START, "end": END}),
                                      (WEATHER, "get_forecasts", {"type": "daily"}),
                                      (WEATHER, "get_forecasts", {"type": "hourly"}),
                                      (WEATHER, "get_forecasts", {"type": "twice_daily"})):
            record, pushed = ask(entity, service, data)
            check(f"Q1 {entity.partition('.')[0]}.{service} {data}: allowed and pushed exactly",
                  record.get("allowed") is True and record.get("clause") == AMBIENT
                  and pushed is not None and pushed.get("data") == data,
                  f"{record.get('clause')} {pushed}")

        print("\nQ2 — any other question, or data\n")
        for label, entity, service, data, clause in (
                ("get_events with an extra key", CAL, "get_events",
                 {"start": START, "end": END, "limit": 5}, COMMAND_DATA),
                ("get_events with a non-ISO start", CAL, "get_events",
                 {"start": "next tuesday", "end": END}, COMMAND_DATA),
                ("get_events with a 41-character start", CAL, "get_events",
                 {"start": START + "x" * (41 - len(START)), "end": END}, COMMAND_DATA),
                ("get_forecasts monthly", WEATHER, "get_forecasts", {"type": "monthly"},
                 COMMAND_DATA),
                ("get_forecasts on a calendar", CAL, "get_forecasts", {"type": "daily"},
                 COMMAND_SERVICES),
                ("get_events on a weather", WEATHER, "get_events", {"start": START, "end": END},
                 COMMAND_SERVICES),
                ("get_events on a sensor", "sensor.demo_value", "get_events",
                 {"start": START, "end": END}, COMMAND_SERVICES)):
            record, pushed = ask(entity, service, data)
            check(f"Q2 {label}: refused, not pushed",
                  record.get("allowed") is False and record.get("clause") == clause
                  and pushed is None, f"{record.get('clause')} {pushed}")

        print("\nQ3 — a well-formed answer is relayed unchanged\n")
        for entity, service, data, payload in (
                (CAL, "get_events", {"start": START, "end": END}, EVENTS),
                (WEATHER, "get_forecasts", {"type": "daily"}, FORECAST)):
            _, pushed = ask(entity, service, data)
            told, record = answer(pushed or {}, payload)
            check(f"Q3 {entity.partition('.')[0]}: {len(payload)} items relayed unchanged",
                  told.get("ok") is True and told.get("answer") == payload,
                  f"{told.get('error') or ''} {str(told.get('answer'))[:60]}")

        print("\nQ4 — a malformed answer is refused and not relayed\n")
        big = [{"summary": f"event {i}", "start": "2026-10-27", "end": "2026-10-28",
                "description": "x" * 900} for i in range(300)]
        for label, entity, service, data, payload in (
                ("an event with no summary", CAL, "get_events", {"start": START, "end": END},
                 [{"start": "2026-10-27", "end": "2026-10-28"}]),
                ("an event with an extra key", CAL, "get_events", {"start": START, "end": END},
                 [{**EVENTS[1], "script": "alert(1)"}]),
                ("a 256-character summary", CAL, "get_events", {"start": START, "end": END},
                 [{**EVENTS[1], "summary": "s" * 256}]),
                ("a 4,097-character description", CAL, "get_events",
                 {"start": START, "end": END}, [{**EVENTS[1], "description": "d" * 4097}]),
                ("a non-ISO start", CAL, "get_events", {"start": START, "end": END},
                 [{**EVENTS[1], "start": "tomorrow"}]),
                ("501 events", CAL, "get_events", {"start": START, "end": END},
                 [EVENTS[1]] * 501),
                ("300 events over 256 KiB", CAL, "get_events", {"start": START, "end": END}, big),
                ("a forecast entry with no datetime", WEATHER, "get_forecasts", {"type": "daily"},
                 [{"condition": "sunny", "temperature": 14.0}]),
                ("a string temperature", WEATHER, "get_forecasts", {"type": "daily"},
                 [{**FORECAST[2], "temperature": "hot"}]),
                ("a NaN temperature", WEATHER, "get_forecasts", {"type": "daily"},
                 [{**FORECAST[2], "temperature": math.nan}]),
                ("a forecast entry with an extra key", WEATHER, "get_forecasts",
                 {"type": "daily"}, [{**FORECAST[2], "html": "<b>"}]),
                ("an answer that is not a list", WEATHER, "get_forecasts", {"type": "daily"},
                 {"forecast": FORECAST})):
            _, pushed = ask(entity, service, data)
            told, record = answer(pushed or {}, payload)
            check(f"Q4 {label}: refused under QUERY_ANSWER, not relayed",
                  told.get("ok") is False and told.get("answer") is None
                  and record.get("clause") == QUERY_ANSWER and record.get("allowed") is False,
                  f"{told} {record.get('clause')}")

        print("\nQ5 — no answer's content reaches the durable log\n")
        log_text = (root / "queries.jsonl").read_text()
        check("Q5 no event title, description or forecast value is in the log",
              "Dentist, Dr Example" not in log_text and "Put it out" not in log_text
              and "alert(1)" not in log_text and "x" * 900 not in log_text)
        answered = [r for r in mediator.log.records() if r.get("clause") == QUERY_ANSWER]
        check("Q5 each answer's record gives its item count and size",
              len(answered) == 14 and all("items" in str(r.get("requested"))
                                          and "bytes" in str(r.get("requested"))
                                          for r in answered),
              f"{len(answered)} records; {answered[0].get('requested') if answered else ''}")

        print("\nQ6 — an answer attached to an ordinary command is not relayed\n")
        _, pushed = ask("switch.demo_power", "turn_on", None)
        told, _ = answer(pushed or {}, EVENTS)
        check("Q6 a switch's result carrying an answer: the platform receives no answer",
              told.get("ok") is True and told.get("answer") is None, str(told))

        # Batch B4b (`notes/bridge_kinds_b4b_prediction_20261031.md`): a picture is a question
        # whose answer is one picture, checked by its type's signature and its size.
        def picture(content_type: str, content: bytes) -> dict:
            return {"content_type": content_type, "data": base64.b64encode(content).decode()}

        body = bytes(range(256)) * 8   # 2 KiB that is no type's signature
        jpeg = b"\xff\xd8\xff\xe1" + body + b"\xff\xd9"
        riff = lambda form: b"RIFF" + (4 + len(body)).to_bytes(4, "little") + form + body
        pictures = (("a JPEG with Exif (FF D8 FF E1)", picture("image/jpeg", jpeg)),
                    ("a JPEG starting FF D8 FF E8", picture("image/jpeg",
                                                            b"\xff\xd8\xff\xe8" + body)),
                    ("a PNG", picture("image/png", b"\x89PNG\r\n\x1a\n" + body)),
                    ("a GIF89a", picture("image/gif", b"GIF89a" + body)),
                    ("a WebP", picture("image/webp", riff(b"WEBP"))))
        print("\nQ7 — a picture of a listed type, matching its signature, is relayed\n")
        for label, payload in pictures:
            _, pushed = ask(DOOR, "camera_image", {"width": 640, "height": 360})
            told, record = answer(pushed or {}, payload)
            check(f"Q7 {label}: relayed unchanged",
                  told.get("ok") is True and told.get("answer") == payload
                  and record.get("clause") == PICTURE_ANSWER,
                  f"{told.get('error') or ''} {record.get('clause')}")
        _, pushed = ask(MAP, "image", None)
        told, _ = answer(pushed or {}, pictures[2][1])
        check("Q7 an image entity's PNG: relayed unchanged",
              told.get("ok") is True and told.get("answer") == pictures[2][1],
              f"{told.get('error') or ''}")

        print("\nQ8 — exactly 512 KiB\n")
        cap = 512 * 1024
        _, pushed = ask(DOOR, "camera_image", None)
        told, record = answer(pushed or {}, picture("image/jpeg", jpeg[:4] + b"j" * (cap - 4)))
        check("Q8 a 512 KiB JPEG is relayed", told.get("ok") is True and told.get("answer"),
              f"{told.get('error') or ''} {record.get('clause')}")

        print("\nQ9 — any other picture answer is refused\n")
        html = b"<html><script>alert(1)</script></html>"
        for label, payload in (
                ("an HTML page labelled image/png", picture("image/png", html)),
                ("JPEG bytes labelled image/png", picture("image/png", jpeg)),
                ("image/svg+xml", picture("image/svg+xml", b"<svg onload='alert(1)'/>")),
                ("image/tiff", picture("image/tiff", b"II*\x00" + body)),
                ("a RIFF WAVE labelled image/webp", picture("image/webp", riff(b"WAVE"))),
                ("512 KiB + 1", picture("image/jpeg", jpeg[:4] + b"j" * (cap - 3))),
                ("data that is not base64", {"content_type": "image/jpeg", "data": "@@not64@@"}),
                ("an extra key", {**pictures[0][1], "url": "http://example.org/x.jpg"}),
                ("no content_type", {"data": pictures[0][1]["data"]}),
                ("a list", [pictures[0][1]]),
                ("empty data", picture("image/jpeg", b""))):
            _, pushed = ask(DOOR, "camera_image", None)
            told, record = answer(pushed or {}, payload)
            check(f"Q9 {label}: refused under PICTURE_ANSWER, not relayed",
                  bool(pushed) and told.get("ok") is False and told.get("answer") is None
                  and record.get("clause") == PICTURE_ANSWER and record.get("allowed") is False,
                  f"{told} {record.get('clause')}")

        print("\nQ10 — no picture reaches the durable log\n")
        log_text = (root / "queries.jsonl").read_text()
        check("Q10 no picture's base64 is in the log",
              pictures[0][1]["data"][:200] not in log_text
              and base64.b64encode(html).decode() not in log_text)
        pictured = [r for r in mediator.log.records() if r.get("clause") == PICTURE_ANSWER]
        check("Q10 each picture's record gives its type and size",
              len(pictured) == 18 and all("content_type" in str(r.get("requested"))
                                          and "bytes" in str(r.get("requested"))
                                          for r in pictured),
              f"{len(pictured)} records; {pictured[0].get('requested') if pictured else ''}")
        check("every chain verifies", mediator.log.verify() == [])

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
