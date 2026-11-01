#!/usr/bin/env python3
"""Mutants of the bridge's new kinds (batches B1–B4a, 2026-10-31): do their tests bite?

M80–M88 (2026-11-01) do the same for F71 and batch B4b (`notes/final_rerun2_prediction_20261101.md`,
D1). Run with names (`mutants_kinds.py M80 M81 ...`) to write only those patches: the others were
written against earlier code and are kept as they ran.

`notes/kinds_tests_bite_prediction_20261031.md`. Same method as `mutants.py` (phase 4.3): each mutant
is one exact `old → new` replacement that must match once, written as `Mxx.patch` beside this file
(applied with `patch -p1` from `v2/`). Kept apart from `mutants.py` so that M01–M50's patches, made
against earlier tags, are not regenerated. Each entry also names the check expected to kill it, or
`survives` where no check is expected to notice: those are the gaps this run is for.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent.parent
MEDIATOR = "framework/confine/mediator.py"
BRIDGE = "framework/ha_bridge/confine_bridge/"

MUTANTS = [
    # The mediator's rule (killed, if at all, by selftest_commands).
    ("M51", "K13", "a command's data may carry keys the shape does not list", MEDIATOR,
     "    return (set(data) <= set(shape) and required <= set(data)",
     "    return (True and required <= set(data)"),
    # M51 crashed both suites (a KeyError on the unlisted key) instead of accepting it; M51b,
    # added after the run, accepts the extra keys and skips them (kinds_tests_bite note, outcome).
    ("M51b", "K13", "a command's data may carry keys the shape does not list, skipped", MEDIATOR,
     "    return (set(data) <= set(shape) and required <= set(data)\n"
     "            and all(shape[k](v) for k, v in data.items()))",
     "    return (True and required <= set(data)\n"
     "            and all(shape[k](v) for k, v in data.items() if k in shape))"),
    ("M52", "K13", "every key of a shape is optional", MEDIATOR,
     "    required = {k for k, valid in shape.items() if not isinstance(valid, _Optional)}",
     "    required = set()"),
    ("M53", "K13", "a colour may have any number of values", MEDIATOR,
     "    return lambda value: (isinstance(value, list) and len(value) == length",
     "    return lambda value: (isinstance(value, list) and len(value) > 0"),
    ("M54", "K13", "a light's flash may be any string", MEDIATOR,
     '    return value in ("short", "long")',
     "    return isinstance(value, str)"),
    ("M55", "K12", "a light's white may not be empty (decision B1-3 undone)", MEDIATOR,
     "    return value is None or _number(value)",
     "    return _number(value)"),
    ("M56", "K7, K13", "an alarm or lock code may be 1024 characters", MEDIATOR,
     "    return isinstance(value, str) and len(value) <= 64",
     "    return isinstance(value, str) and len(value) <= 1024"),
    ("M57", "K19, K30", "vacuum parameters, media extras and remote commands sixteen times larger",
     MEDIATOR,
     "MAX_COMMAND_PARAMS, MAX_REMOTE_COMMAND, MAX_REMOTE_COMMANDS = 4096, 4096, 64",
     "MAX_COMMAND_PARAMS, MAX_REMOTE_COMMAND, MAX_REMOTE_COMMANDS = 65536, 65536, 1024"),
    ("M58", "K26", "a notification's text is written to the log", MEDIATOR,
     'WITHHELD = frozenset({"code", "message", "title"})',
     'WITHHELD = frozenset({"code"})'),
    ("M59", "K24", "a time of day is not parsed", MEDIATOR,
     "        dt_time.fromisoformat(value)\n",
     "        str(value)\n"),
    ("M60", "K14", "a light's toggle is forwarded, though (A) works it out", MEDIATOR,
     '        "turn_off": [{"transition": _Optional(_number), "flash": _Optional(_flash)}],',
     '        "turn_off": [{"transition": _Optional(_number), "flash": _Optional(_flash)}],\n'
     '        "toggle": [{}],'),
    ("M61", "K25", "an update's skip is forwarded, though (A) keeps it", MEDIATOR,
     '    "update": {"install": [{"backup": _flag, "version": _Optional(_text)}]},',
     '    "update": {"install": [{"backup": _flag, "version": _Optional(_text)}],\n'
     '               "skip": [{}]},'),
    ("M62", "K31", "a media player's join is forwarded", MEDIATOR,
     '        "repeat_set": [{"repeat": _repeat}],',
     '        "repeat_set": [{"repeat": _repeat}],\n        "join": [{}],'),
    # The bridge's entities in (A) (killed, if at all, by selftest_bridge_types against (A)).
    ("M63", "T24", "an event republished by the sandbox fires again", BRIDGE + "event.py",
     '        if state in (None, "unknown", "unavailable") or state == self._seen:',
     '        if state in (None, "unknown", "unavailable"):'),
    ("M64", "survives?", "an event type the entity does not list raises in (A)",
     BRIDGE + "event.py",
     "        except ValueError:\n            pass  # an event type",
     "        except KeyError:\n            pass  # an event type"),
    ("M65", "T28", "a media player shows the sandbox's own picture link",
     BRIDGE + "media_player.py",
     '"entity_picture", "entity_picture_local", "supported_features"})',
     '"entity_picture_local", "supported_features"})'),
    ("M66", "T28, T31", "a media player offers browsing, searching and grouping",
     BRIDGE + "media_player.py",
     "            & ~_NOT_OFFERED)",
     "            )"),
    ("M67", "T30", "an id (A) cannot resolve makes play_media fail", BRIDGE + "media_player.py",
     "            except media_source.MediaSourceError:",
     "            except KeyError:"),
    ("M68", "T30", "(A)'s own media is never resolved in (A)", BRIDGE + "media_player.py",
     "        if media_source.is_media_source_id(media_id):",
     "        if False:"),
    ("M69", "T29", "volume_up is worked out in (A) instead of forwarded",
     BRIDGE + "media_player.py",
     "    async def async_volume_up(self) -> None:",
     "    async def _unused_volume_up(self) -> None:"),
    ("M70", "T22", "an update offers release notes", BRIDGE + "update.py",
     "            & ~UpdateEntityFeature.RELEASE_NOTES)",
     "            )"),
    ("M71", "T18", "a siren's tone goes on by key, not by name", BRIDGE + "siren.py",
     '            data["tone"] = tones[data["tone"]]',
     "            pass"),
    ("M72", "T18", "a water heater forwards the whole service data", BRIDGE + "water_heater.py",
     '                                             if k in ("temperature", "operation_mode")})',
     "                                             if True})"),
    ("M73", "T18", "away mode on is sent as off", BRIDGE + "water_heater.py",
     '        await self._send("set_away_mode", {"away_mode": True})',
     '        await self._send("set_away_mode", {"away_mode": False})'),
    ("M74", "T18", "a valve never reports its position", BRIDGE + "valve.py",
     "        self._attr_reports_position = position is not None",
     "        self._attr_reports_position = False"),
    ("M75", "T12", "a fan's speed count is ignored", BRIDGE + "fan.py",
     "        self._attr_speed_count = (max(1, round(100 / step))",
     "        self._attr_speed_count = (100"),
    ("M76", "survives", "a fan's on/off follows Home Assistant's rule, not what was published",
     BRIDGE + "fan.py",
     "    def is_on(self) -> bool | None:",
     "    def _unused_is_on(self) -> bool | None:"),
    ("M77", "survives", "a lock's code format is not checked to compile", BRIDGE + "lock.py",
     "        re.compile(value)",
     "        str(value)"),
    ("M78", "T23", "a GPS tracker shows the sandbox's state, not (A)'s zones",
     BRIDGE + "device_tracker.py",
     "        self._attr_location_name = (str(state) if self._attr_latitude is None",
     "        self._attr_location_name = (str(state) if True"),
    ("M79", "survives", "every tracker is built as a GPS tracker, scanners included",
     BRIDGE + "device_tracker.py",
     '    if source in (None, SourceType.GPS, "gps"):',
     "    if True:"),
    # F71 and batch B4b (2026-11-01).
    ("M80", "T32", "the sandbox's picture link is passed on for every kind", BRIDGE + "entity.py",
     'NOT_PASSED = {"entity_picture", "entity_picture_local"}',
     "NOT_PASSED: set[str] = set()"),
    ("M81", "Q9", "a picture's bytes need not begin as its type does", MEDIATOR,
     "    if not SIGNATURES[content_type](content):",
     "    if False:"),
    ("M82", "Q9", "a picture may be 1 MiB, not 512 KiB", MEDIATOR,
     "MAX_PICTURE_BYTES = 512 * 1024",
     "MAX_PICTURE_BYTES = 1024 * 1024"),
    ("M83", "Q9", "image/svg+xml is a listed picture type", MEDIATOR,
     '    "image/webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",\n}',
     '    "image/webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",\n'
     '    "image/svg+xml": lambda b: True,\n}'),
    ("M84", "T33", "a camera keeps the stream feature", BRIDGE + "camera.py",
     "            int(attributes.get(\"supported_features\") or 0) & CameraEntityFeature.ON_OFF)",
     "            int(attributes.get(\"supported_features\") or 0))"),
    ("M85", "T35", "a camera asks for every picture", BRIDGE + "camera.py",
     "        if kept is not None and now - kept[0] < REUSE_SECONDS:",
     "        if False:"),
    ("M86", "T38", "an image asks again after 2 s even if its published time is the same",
     BRIDGE + "image.py",
     "        if kept is not None and (kept[0] == published\n",
     "        if kept is not None and (False\n"),
    ("M87", "Q10", "an answer is recorded in full, pictures included", MEDIATOR,
     '                                "service": f"{kind}.{service}", "answer": shape}, decision)',
     '                                "service": f"{kind}.{service}", "answer": payload}, decision)'),
    ("M88", "T33", "a camera passes on the sandbox's access token", BRIDGE + "camera.py",
     '    _described = frozenset({"brand", "model_name", "motion_detection", "supported_features",\n'
     '                            "access_token", "frontend_stream_type"})',
     '    _described = frozenset({"brand", "model_name", "motion_detection", "supported_features",\n'
     '                            "frontend_stream_type"})'),
]


def main() -> int:
    only = set(sys.argv[1:])
    for ident, killer, what, path, old, new in MUTANTS:
        if only and ident not in only:
            continue
        source = (V2 / path).read_text()
        count = source.count(old)
        if count != 1:
            print(f"{ident}: the original text occurs {count} times in {path}; expected once")
            return 1
        mutated = source.replace(old, new)
        diff = difflib.unified_diff(source.splitlines(keepends=True),
                                    mutated.splitlines(keepends=True),
                                    fromfile=f"a/{path}", tofile=f"b/{path}", n=2)
        (HERE / f"{ident}.patch").write_text(f"# {ident} (expected: {killer}): {what}\n"
                                             + "".join(diff))
        print(f"{ident:<5} {killer:<10} {path.rsplit('/', 1)[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
