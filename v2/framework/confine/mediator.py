"""The mediator's side of the channel: who is asking, and what happens to the answer.

§5.11.3 fixes the order in which one request is handled, and the order is not an implementation
detail:

    1. Identity   — from the socket the request arrived on (§5.11.2)
    2. Manifest   — the manifest bound to that integration's content hash (§5.9.6)
    3. Decision   — match against the clauses; absent a match, deny (S6)
    4. Record     — decision, clause and identity to the audit log (§5.12)
    5. Act        — only now, and only with the mediator's own credential (S2)

Steps 2, 4 and 5 belong to §6.6, §6.8 and the bridge respectively and are not implemented here.
What is implemented is steps 1 and 3, and step 3's **default**, which is the whole of S6: a
mediator holding no manifest denies everything. That is worth building first rather than last,
because it is the behaviour every later addition has to preserve, and a default-deny that
arrives after the permit path is one that has already been forgotten once.

*2026-10-04 (W1): the paragraph above describes the first version. Step 4 is now here (`_record`,
with the durable log), and step 5 is run here too, after the record, from the `act` a policy
returns; the push loop's subscription table and outbox are also here. See
`notes/w1_push_loop_prediction.md`.*
"""

from __future__ import annotations

import array
import base64
import binascii
import collections
import json
import math
from datetime import datetime, time as dt_time
import os
import selectors
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .audit import AuditLog, Identity
from .channel import Channel, ProtocolError


@dataclass(frozen=True)
class Decision:
    """What the mediator decided, and the clause that decided it (§5.11.3)."""

    allowed: bool
    reason: str
    clause: str | None = None
    data: dict | None = None
    #: A connected descriptor to hand across with the response, for the one capability whose
    #: result is a kernel object rather than a value (§7.24's egress path). Deliberately kept
    #: out of `data`: `data` is JSON that goes on the wire, and a descriptor travels as
    #: ancillary data instead. The mediator closes its copy once the frame is sent — the
    #: sandbox has its own by then, and holding both would leak one per connection.
    fd: int | None = None
    #: Step 5, deferred. A policy that must *act* — write a state, place a call, open a
    #: connection — returns the act as a closure instead of doing it, and the mediator runs it
    #: only after step 4's record is durable. Until W1 the acting policy acted inside the
    #: decision, so the record came after the action in every case §5.11.3 wrote the ordering
    #: for (`notes/w1_push_loop_prediction.md` §1 (1)). The closure returns the decision that
    #: actually went out: the same grant with its data or descriptor, or a refusal found while
    #: acting, such as an egress name that now resolves to a private address.
    act: Callable[[], "Decision"] | None = field(default=None, compare=False)
    #: A socket for the mediator to watch on this channel's behalf, and the route its datagrams
    #: are pushed under (W2 (b)). Set by an act that opened one — a streaming listen, or a new
    #: per-peer socket — so that what arrives on it is pushed down the channel without a record
    #: per datagram: the record is the decision that opened it.
    source: tuple | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        # F3: every decision names the clause, or the mediator's own rule, that produced it.
        # Refused here rather than checked later, so that a decision with nothing to attribute
        # it to cannot be built at all. Until 2026-10-06 seven paths built one (F03).
        if not self.clause:
            raise ValueError(f"a decision must name the clause that produced it: {self.reason!r}")

    def as_response(self, request_id: object) -> dict:
        response: dict = {"id": request_id, "ok": self.allowed, "reason": self.reason}
        # §5.11.3: every response carries the clause that decided it, so that attribution is
        # a property of the protocol rather than something reconstructed from logs later.
        response["clause"] = self.clause
        if self.data:
            response.update(self.data)
        return response


def deny_everything(identity: str, request: dict) -> Decision:
    """S6, as a function. No manifest, therefore no grant, therefore no."""
    return Decision(False, "no manifest is bound to this integration", clause="/permissions")


@dataclass
class _Outbox:
    """What the mediator still owes one sandbox, and the bound on how much that can be.

    Until W1 the mediator only ever replied, to a sandbox that had just asked and was waiting,
    so a blocking `sendall` was safe. A push is sent to a sandbox that asked for nothing and
    may not be reading, and a blocking send to it would stop the mediator's only thread, and
    with it every other sandbox (`notes/w1_push_loop_prediction.md` §1 (4)). So nothing here
    blocks. What is owed waits in three places, each bounded:

      - **at most one reply**, because the mediator stops reading a sandbox's requests while
        it owes that sandbox a reply. A sandbox that asks without reading stalls only itself;
      - **at most one state per subscribed entity**, because a newer state *replaces* an
        unsent one instead of queueing behind it. A state is a value, not an event, so only
        the latest is worth sending (decision B, 2026-10-04);
      - **at most one frame part-written**, which must finish before anything else starts,
        or two frames would interleave on the wire.
    """

    reply: tuple[bytes, int | None] | None = None
    #: Users' commands for this sandbox's entities (W1 step 2b), first in first out and never
    #: coalesced: a state is a value and only the latest matters, a command is an instruction.
    #: Bounded by the mediator at `MAX_COMMANDS`.
    commands: collections.deque = field(default_factory=collections.deque)
    #: Datagrams pushed from the relay's sockets (W2 (b)): first in first out, never coalesced,
    #: and bounded at `MAX_DATAGRAMS` by dropping the oldest, as a real socket's full receive
    #: buffer drops what does not fit.
    datagrams: collections.deque = field(default_factory=collections.deque)
    datagrams_dropped: int = 0
    pushes: dict[str, dict] = field(default_factory=dict)
    inflight: bytearray = field(default_factory=bytearray)
    inflight_fd: int | None = None
    inflight_is_reply: bool = False
    inflight_is_push: bool = False

    @property
    def owes_reply(self) -> bool:
        return self.reply is not None or (bool(self.inflight) and self.inflight_is_reply)

    @property
    def empty(self) -> bool:
        return (not self.inflight and self.reply is None and not self.commands
                and not self.datagrams and not self.pushes)

    def drain(self, sock) -> int:
        """Write as much as the socket takes without blocking. Returns pushes fully sent.

        Raises `OSError` if the far end has gone; the caller drops the channel.
        """
        completed = 0
        while True:
            if not self.inflight:
                if self.reply is not None:
                    data, self.inflight_fd = self.reply
                    self.reply = None
                    self.inflight, self.inflight_is_reply = bytearray(data), True
                    self.inflight_is_push = False
                elif self.commands:
                    self.inflight = bytearray(Channel.frame(self.commands.popleft()))
                    self.inflight_is_reply = self.inflight_is_push = False
                elif self.datagrams:
                    self.inflight = bytearray(Channel.frame(self.datagrams.popleft()))
                    self.inflight_is_reply = self.inflight_is_push = False
                elif self.pushes:
                    message = self.pushes.pop(next(iter(self.pushes)))
                    self.inflight = bytearray(Channel.frame(message))
                    self.inflight_is_reply, self.inflight_is_push = False, True
                else:
                    return completed
            try:
                if self.inflight_fd is not None:
                    # The descriptor rides with the first byte (see `Channel.send`). Once any
                    # byte has gone, the sandbox holds its own copy and this one is closed.
                    rights = array.array("i", [self.inflight_fd])
                    sent = sock.sendmsg([bytes(self.inflight)],
                                        [(socket.SOL_SOCKET, socket.SCM_RIGHTS, rights)],
                                        socket.MSG_DONTWAIT)
                    os.close(self.inflight_fd)
                    self.inflight_fd = None
                else:
                    sent = sock.send(self.inflight, socket.MSG_DONTWAIT)
            except BlockingIOError:
                return completed
            del self.inflight[:sent]
            if not self.inflight and self.inflight_is_push:
                completed += 1

    def discard(self) -> None:
        """Close any descriptor still owed. A dropped channel must not leave a connection open."""
        for fd in (self.inflight_fd, self.reply[1] if self.reply else None):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        self.inflight_fd, self.reply = None, None


#: Commands queued for one sandbox, at most (W1 step 2b). Past this a user's command is refused at
#: once rather than queued without limit behind a sandbox that is not reading.
MAX_COMMANDS = 32

#: The rules `Mediator.command` decides by, named so that every decision carries one (F3). A
#: command is ambient, not declared (§5.10.2): these are the mediator's own conditions on it, and
#: the clause names which one refused.
COMMAND_NO_SANDBOX = "(command: the integration has a running sandbox)"
COMMAND_SERVICES = "(command: only the services listed for the entity's type)"
COMMAND_DATA = "(command: only the data listed for that service, of its kind)"
QUERY_ANSWER = "(answer: only the listed shape, at most 500 items and 256 KiB)"
PICTURE_ANSWER = ("(answer: one picture of a listed type, its bytes starting with that type's "
                  "signature, at most 512 KiB)")
COMMAND_QUEUE = f"(command: at most {MAX_COMMANDS} queued)"
COMMAND_ANSWER = "(command: answered only on the channel it was sent to)"
AMBIENT = "(ambient: §5.10.2)"

#: Home Assistant's own limit on a state's length (`MAX_LENGTH_STATE_STATE`), and so on any text
#: value or option a user can set.
MAX_COMMAND_TEXT = 255


def _text(value: object) -> bool:
    return isinstance(value, str) and len(value) <= MAX_COMMAND_TEXT


def _number(value: object) -> bool:
    # `bool` is an `int` in Python, and True would arrive as 1.
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


#: Home Assistant's HVAC modes (`climate.HVACMode`, 2026.8.3).
HVAC_MODES = frozenset({"off", "heat", "cool", "heat_cool", "auto", "dry", "fan_only"})


def _hvac_mode(value: object) -> bool:
    return isinstance(value, str) and value in HVAC_MODES


def _code(value: object) -> bool:
    return isinstance(value, str) and len(value) <= 64


def _iso(value: object) -> bool:
    """An ISO 8601 date or date-time, as a string of at most 40 characters."""
    if not (isinstance(value, str) and len(value) <= 40):
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _forecast_type(value: object) -> bool:
    return value in ("daily", "hourly", "twice_daily")


def _flag(value: object) -> bool:
    return isinstance(value, bool)


def _flash(value: object) -> bool:
    return value in ("short", "long")


def _colour(length: int) -> Callable[[object], bool]:
    """A colour as Home Assistant hands it to a light: `length` numbers, arriving as a list."""
    return lambda value: (isinstance(value, list) and len(value) == length
                          and all(_number(v) for v in value))


def _white(value: object) -> bool:
    # A brightness; empty when (A) turned `white: true` into a brightness it does not know
    # (`light/__init__.py`, process_turn_on_params; decided 2026-10-31).
    return value is None or _number(value)


#: A vacuum's raw command parameters and a remote's commands (batch B2, decisions 1 and 2): free
#: in content, bounded in size, because an allowed command's data is written to the log as sent.
MAX_COMMAND_PARAMS, MAX_REMOTE_COMMAND, MAX_REMOTE_COMMANDS = 4096, 4096, 64


def _params(value: object) -> bool:
    """A mapping or a list of plain JSON data, at most 4 KiB serialised; its content unchecked."""
    if not isinstance(value, (dict, list)):
        return False
    try:
        return len(json.dumps(value, allow_nan=False)) <= MAX_COMMAND_PARAMS
    except (TypeError, ValueError):
        return False


def _commands(value: object) -> bool:
    """A remote's commands: 1 to 64 strings, each at most 4096 characters (raw codes can be long)."""
    return (isinstance(value, list) and 1 <= len(value) <= MAX_REMOTE_COMMANDS
            and all(isinstance(v, str) and len(v) <= MAX_REMOTE_COMMAND for v in value))


#: A notification's text (batch B3, decision 4).
MAX_MESSAGE = 4096


def _message(value: object) -> bool:
    return isinstance(value, str) and len(value) <= MAX_MESSAGE


#: A media id can be a long link (batch B4a, decision 2).
MAX_MEDIA_ID = 4096


def _pixels(value: object) -> bool:
    """A picture's width or height as (A)'s proxy reads it from a request: a whole number."""
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 16384


def _media_id(value: object) -> bool:
    return isinstance(value, str) and len(value) <= MAX_MEDIA_ID


def _repeat(value: object) -> bool:
    return value in ("off", "all", "one")


def _enqueue(value: object) -> bool:
    return value in ("add", "next", "play", "replace")


def _clock(value: object) -> bool:
    """A time of day, "HH:MM" or "HH:MM:SS", as Home Assistant's own `time.set_value` takes it."""
    if not (isinstance(value, str) and len(value) <= 15):
        return False
    try:
        dt_time.fromisoformat(value)
    except ValueError:
        return False
    return True


def _tone(value: object) -> bool:
    return (isinstance(value, int) and not isinstance(value, bool)) or _text(value)


class _Optional:
    """A key a shape may leave out (batch B1): a light's turn_on carries any of eleven."""

    def __init__(self, valid: Callable[[object], bool]) -> None:
        self.valid = valid

    def __call__(self, value: object) -> bool:
        return self.valid(value)


Shape = dict[str, Callable[[object], bool]]
#: No data, or a code: an alarm panel's and a lock's services.
_CODED: list[Shape] = [{}, {"code": _code}]

#: What the mediator forwards from the household to a confined integration (bridge steps 2 and 3,
#: approved by Younes 2026-10-25): per entity type, the services, and for each the shapes its data
#: may take — **exactly** one shape's keys, each value of the listed kind. Shape only: whether a
#: value is inside a range, among the options, or the right alarm code is checked by (A) or by the
#: integration. Home Assistant's other services on these types (`toggle`, `select_next`,
#: `increment`, a fan's `increase_speed`, a cover's `toggle_tilt`, ...) are worked out in (A) and
#: arrive as one of these. Light, fan, cover and lock (batch B1,
#: `notes/bridge_kinds_b1_prediction_20261031.md`) list what Home Assistant 2026.8.3 hands the
#: entity's own method, which is narrower than the service: (A) has already turned
#: `brightness_pct`, `color_name` and `profile` into brightness and colour, and dropped what the
#: light does not support. Keys wrapped in `_Optional` may be left out.
COMMANDS: dict[str, dict[str, list[Shape]]] = {
    "switch": {"turn_on": [{}], "turn_off": [{}]},
    "button": {"press": [{}]},
    "text": {"set_value": [{"value": _text}]},
    "select": {"select_option": [{"option": _text}]},
    "number": {"set_value": [{"value": _number}]},
    "climate": {
        "turn_on": [{}], "turn_off": [{}],
        "set_hvac_mode": [{"hvac_mode": _hvac_mode}],
        "set_temperature": [
            {"temperature": _number},
            {"temperature": _number, "hvac_mode": _hvac_mode},
            {"target_temp_low": _number, "target_temp_high": _number},
            {"target_temp_low": _number, "target_temp_high": _number, "hvac_mode": _hvac_mode}],
        "set_fan_mode": [{"fan_mode": _text}],
        "set_preset_mode": [{"preset_mode": _text}],
        "set_swing_mode": [{"swing_mode": _text}],
        "set_swing_horizontal_mode": [{"swing_horizontal_mode": _text}],
        "set_humidity": [{"humidity": _number}],
    },
    "alarm_control_panel": {
        service: _CODED for service in (
            "alarm_disarm", "alarm_arm_home", "alarm_arm_away", "alarm_arm_night",
            "alarm_arm_vacation", "alarm_arm_custom_bypass", "alarm_trigger")},
    "light": {
        "turn_on": [{key: _Optional(valid) for key, valid in (
            ("brightness", _number), ("color_temp_kelvin", _number), ("hs_color", _colour(2)),
            ("rgb_color", _colour(3)), ("rgbw_color", _colour(4)), ("rgbww_color", _colour(5)),
            ("xy_color", _colour(2)), ("white", _white), ("effect", _text), ("flash", _flash),
            ("transition", _number))}],
        "turn_off": [{"transition": _Optional(_number), "flash": _Optional(_flash)}],
    },
    "fan": {
        "turn_on": [{"percentage": _Optional(_number), "preset_mode": _Optional(_text)}],
        "turn_off": [{}],
        "set_percentage": [{"percentage": _number}],
        "set_preset_mode": [{"preset_mode": _text}],
        "oscillate": [{"oscillating": _flag}],
        "set_direction": [{"direction": _text}],
    },
    "cover": {
        **{service: [{}] for service in (
            "open_cover", "close_cover", "stop_cover",
            "open_cover_tilt", "close_cover_tilt", "stop_cover_tilt")},
        "set_cover_position": [{"position": _number}],
        "set_cover_tilt_position": [{"tilt_position": _number}],
    },
    "lock": {service: _CODED for service in ("lock", "unlock", "open")},
    # Batch B2 (`notes/bridge_kinds_b2_prediction_20261031.md`). A vacuum's `clean_area` is not
    # here: (A) turns it into segment ids that no service in the sandbox takes (decision 4).
    "humidifier": {
        "turn_on": [{}], "turn_off": [{}],
        "set_mode": [{"mode": _text}],
        "set_humidity": [{"humidity": _number}],
    },
    "water_heater": {
        "turn_on": [{}], "turn_off": [{}],
        "set_temperature": [{"temperature": _number, "operation_mode": _Optional(_text)}],
        "set_operation_mode": [{"operation_mode": _text}],
        "set_away_mode": [{"away_mode": _flag}],
    },
    "vacuum": {
        **{service: [{}] for service in (
            "start", "pause", "stop", "return_to_base", "clean_spot", "locate")},
        "set_fan_speed": [{"fan_speed": _text}],
        "send_command": [{"command": _text, "params": _Optional(_params)}],
    },
    "valve": {
        **{service: [{}] for service in ("open_valve", "close_valve", "stop_valve")},
        "set_valve_position": [{"position": _number}],
    },
    "siren": {
        "turn_on": [{"tone": _Optional(_tone), "duration": _Optional(_number),
                     "volume_level": _Optional(_number)}],
        "turn_off": [{}],
    },
    "remote": {
        "turn_on": [{"activity": _Optional(_text)}],
        "turn_off": [{"activity": _Optional(_text)}],
        "send_command": [{"command": _commands, "device": _Optional(_text),
                          "num_repeats": _Optional(_number), "delay_secs": _Optional(_number),
                          "hold_secs": _Optional(_number)}],
        "learn_command": [{"device": _Optional(_text), "command": _Optional(_commands),
                           "command_type": _Optional(_text), "alternative": _Optional(_flag),
                           "timeout": _Optional(_number)}],
        "delete_command": [{"command": _commands, "device": _Optional(_text)}],
    },
    # Batch B3 (`notes/bridge_kinds_b3_prediction_20261031.md`). An update's `skip` and
    # `clear_skipped` are kept in (A) itself; events and device trackers are display only.
    "update": {"install": [{"backup": _flag, "version": _Optional(_text)}]},
    "time": {"set_value": [{"time": _clock}]},
    "notify": {"send_message": [{"message": _message, "title": _Optional(_text)}]},
    # Batch B4a (`notes/bridge_kinds_b4a_prediction_20261031.md`). `toggle`, `volume_up`,
    # `volume_down` and `media_play_pause` go on as themselves: Home Assistant runs the
    # integration's own method for them when it has one (decision 1). Grouping, browsing and
    # searching are not offered (decisions 3, 4). The renamed services carry the service's own
    # field names, because the sandbox runs the service again.
    "media_player": {
        **{service: [{}] for service in (
            "turn_on", "turn_off", "toggle", "media_play", "media_pause", "media_play_pause",
            "media_stop", "media_next_track", "media_previous_track", "clear_playlist",
            "volume_up", "volume_down")},
        "volume_set": [{"volume_level": _number}],
        "volume_mute": [{"is_volume_muted": _flag}],
        "media_seek": [{"seek_position": _number}],
        "select_source": [{"source": _text}],
        "select_sound_mode": [{"sound_mode": _text}],
        "shuffle_set": [{"shuffle": _flag}],
        "repeat_set": [{"repeat": _repeat}],
        "play_media": [{"media_content_type": _text, "media_content_id": _media_id,
                        "enqueue": _Optional(_enqueue), "announce": _Optional(_flag),
                        "extra": _Optional(_params)}],
    },
    # Questions (bridge step 4): answered with a list, which `ANSWERS` checks.
    "calendar": {"get_events": [{"start": _iso, "end": _iso}]},
    "weather": {"get_forecasts": [{"type": _forecast_type}]},
    # Batch B4b (`notes/bridge_kinds_b4b_prediction_20261031.md`). `camera_image` and `image` are
    # questions only the bridged entity asks (no such service exists in (A)), answered with one
    # picture, which `check_picture` checks. `snapshot` stays in (A); streams and recording are
    # not offered (decisions 3, 4).
    "camera": {
        **{service: [{}] for service in (
            "turn_on", "turn_off", "enable_motion_detection", "disable_motion_detection")},
        "camera_image": [{"width": _Optional(_pixels), "height": _Optional(_pixels)}],
    },
    "image": {"image": [{}]},
}

#: An answer is a list of at most this many items, and at most this many bytes as JSON.
MAX_ANSWER_ITEMS, MAX_ANSWER_BYTES = 500, 256 * 1024


def _bounded(limit: int) -> Callable[[object], bool]:
    return lambda value: isinstance(value, str) and len(value) <= limit


def _maybe(valid: Callable[[object], bool]) -> Callable[[object], bool]:
    return lambda value: value is None or valid(value)


def _bearing(value: object) -> bool:
    return _number(value) or (isinstance(value, str) and len(value) <= 8)


#: The shape of each item in an answer, from the side the mediator does not trust: the fields Home
#: Assistant's own response services return (`calendar.const.LIST_EVENT_FIELDS`;
#: `weather.Forecast`'s display fields), each required or optional, each of its kind.
ANSWERS: dict[tuple[str, str], tuple[dict, dict]] = {
    ("calendar", "get_events"): (
        {"summary": _bounded(255), "start": _iso, "end": _iso},
        {"description": _maybe(_bounded(4096)), "location": _maybe(_bounded(255))}),
    ("weather", "get_forecasts"): (
        {"datetime": _iso},
        {"condition": _maybe(_bounded(64)), "is_daytime": _maybe(lambda v: isinstance(v, bool)),
         "wind_bearing": _maybe(_bearing),
         **{key: _maybe(_number) for key in (
             "temperature", "templow", "apparent_temperature", "dew_point", "pressure",
             "wind_speed", "wind_gust_speed", "precipitation", "precipitation_probability",
             "humidity", "cloud_coverage", "uv_index")}}),
}


def check_answer(question: tuple[str, str], answer: object) -> tuple[str | None, dict]:
    """Why an answer is refused (None if it is not), and its shape for the record."""
    try:
        size = len(json.dumps(answer))
    except (TypeError, ValueError):
        return "it is not plain data", {"bytes": None}
    shape = {"items": len(answer) if isinstance(answer, list) else None, "bytes": size}
    if not isinstance(answer, list):
        return "it is not a list", shape
    if len(answer) > MAX_ANSWER_ITEMS:
        return f"it has more than {MAX_ANSWER_ITEMS} items", shape
    if size > MAX_ANSWER_BYTES:
        return f"it is larger than {MAX_ANSWER_BYTES} bytes", shape
    required, optional = ANSWERS[question]
    for index, item in enumerate(answer):
        if not isinstance(item, dict):
            return f"item {index} is not a mapping", shape
        extra = set(item) - set(required) - set(optional)
        if extra or not set(required) <= set(item):
            return f"item {index} does not have exactly the listed fields", shape
        if not all({**required, **optional}[k](v) for k, v in item.items()):
            return f"item {index} has a field of the wrong kind", shape
    return None, shape

#: Questions answered with one picture (batch B4b), and the most bytes a picture may have:
#: 512 KiB, about 683 KiB as base64, inside the channel's 1 MiB frame (decision 1).
PICTURES = frozenset({("camera", "camera_image"), ("image", "image")})
MAX_PICTURE_BYTES = 512 * 1024

#: The first bytes every file of each picture type begins with, by the format's own definition.
#: Not Home Assistant's table (`image.MAP_MAGIC_NUMBERS_TO_CONTENT_TYPE`): it lists only some JPEG
#: markers, and takes any RIFF file (a WAV, an AVI) for a WebP.
SIGNATURES: dict[str, Callable[[bytes], bool]] = {
    "image/jpeg": lambda b: b[:3] == b"\xff\xd8\xff",
    "image/png": lambda b: b[:8] == b"\x89PNG\r\n\x1a\n",
    "image/gif": lambda b: b[:6] in (b"GIF87a", b"GIF89a"),
    "image/webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
}


def check_picture(answer: object) -> tuple[str | None, dict]:
    """Why a picture answer is refused (None if it is not), and its type and size for the record.

    The picture itself is never recorded: a camera's picture is of the inside of a house.
    """
    shape: dict = {"content_type": None, "bytes": None}
    if not isinstance(answer, dict) or set(answer) != {"content_type", "data"}:
        return "it is not exactly a content_type and its data", shape
    content_type, data = answer["content_type"], answer["data"]
    if not isinstance(content_type, str) or content_type not in SIGNATURES:
        return "its type is not one of the listed picture types", shape
    shape["content_type"] = content_type
    if not isinstance(data, str) or len(data) > (MAX_PICTURE_BYTES + 2) // 3 * 4:
        return f"it is not a string of base64 within {MAX_PICTURE_BYTES} bytes", shape
    try:
        content = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        return "its data is not base64", shape
    shape["bytes"] = len(content)
    if len(content) > MAX_PICTURE_BYTES:
        return f"it is larger than {MAX_PICTURE_BYTES} bytes", shape
    if not SIGNATURES[content_type](content):
        return f"its bytes do not begin as a {content_type} does", shape
    return None, shape


#: Data never written to the durable log, allowed or refused: an alarm or lock code, and a
#: notification's text (batch B3, decision 4). The record keeps that the key was there.
WITHHELD = frozenset({"code", "message", "title"})


def _fits(data: dict, shape: Shape) -> bool:
    """Only the shape's keys, every one it requires, each value of its kind."""
    required = {k for k, valid in shape.items() if not isinstance(valid, _Optional)}
    return (set(data) <= set(shape) and required <= set(data)
            and all(shape[k](v) for k, v in data.items()))


def _matches(data: dict, shapes: list[Shape]) -> bool:
    return any(_fits(data, shape) for shape in shapes)


def _kinds(data: dict) -> dict[str, str]:
    """A refused command's data as each value's type and length — never the value itself."""
    return {str(k)[:64]: "(withheld)" if k in WITHHELD
            else f"{type(v).__name__}, length {len(v)}" if hasattr(v, "__len__")
            else type(v).__name__ for k, v in list(data.items())[:16]}
#: A request the policy or its act could not handle: a field of the wrong type, a peer that answered
#: a datagram with "port unreachable". Refused under this rule, and counted like any other refusal
#: (verification 4.7, finding F33).
MALFORMED = "(request: each field of the type its operation reads)"

#: What bad data and the network raise. One of these from the policy or an act is the requesting
#: sandbox's refusal. Anything else still stops the mediator: an audit write that fails is outside
#: this boundary on purpose (no record, no decision, F28), and `PlatformLost` is a RuntimeError the
#: supervisor handles (F29).
REQUEST_ERRORS = (TypeError, ValueError, AttributeError, KeyError, IndexError, OverflowError,
                  OSError)

#: Datagrams queued for one sandbox, at most (W2 (b)). Matches the relay's `QUEUE_LIMIT`.
MAX_DATAGRAMS = 64

#: The refusal flood (`notes/flood_cutoff_prediction.md`). Every refusal is a durable record, so
#: a sandbox that keeps asking for what it may not have spends the fsync budget every other
#: sandbox shares. Past `FLOOD_LIMIT` refusals of its own requests within `FLOOD_WINDOW` seconds
#: it is cut off. Chosen from data: the worst honest run measured made 12 refusals in its whole
#: life, and W2 (a)'s flood made about 1,000 a second.
FLOOD_LIMIT = 100
FLOOD_WINDOW = 10.0


class CutOff(RuntimeError):
    """An integration that was cut off for flooding, and has not been reinstated."""


@dataclass
class Mediator:
    """Holds one end of every sandbox's socket, and never asks a sandbox who it is."""

    policy: Callable[[str, dict], Decision] = deny_everything
    audit: list[dict] = field(default_factory=list)
    log: AuditLog | None = None
    #: Push frames fully written, per integration. Counted in memory and not recorded: the
    #: record is the `entity.subscribe` decision that allowed them (decision A, 2026-10-04),
    #: the way the egress record is the connect and not the bytes that follow it.
    pushes_sent: dict[str, int] = field(default_factory=dict)
    #: Unsent states replaced by a newer one before they left. Non-zero means a sandbox was
    #: not keeping up, and it is the number P7 reads.
    pushes_coalesced: dict[str, int] = field(default_factory=dict)
    _runs: dict[str, str] = field(default_factory=dict)
    _by_fd: dict[int, tuple[str, Channel]] = field(default_factory=dict)
    #: What each **channel** has subscribed to. Keyed by channel rather than by integration:
    #: a subscription belongs to one spawn, and goes when that spawn's channel does, so a
    #: respawn under a new manifest starts with none and must be granted each one again.
    _subscriptions: dict[int, set[str]] = field(default_factory=dict)
    _out: dict[int, _Outbox] = field(default_factory=dict)
    _selector: selectors.BaseSelector = field(default_factory=selectors.DefaultSelector)
    _platform: object | None = None
    #: Commands pushed and not yet answered: command id -> the channel it was sent down. An answer
    #: is accepted only from that channel, and only once (W1 step 2b, C7).
    _sent_commands: dict[int, int] = field(default_factory=dict)
    #: Of those, the questions (bridge step 4): command id -> (type, service, entity). Only these
    #: have their answers checked and relayed; any other command's answer carries none.
    _questions: dict[int, tuple[str, str, str]] = field(default_factory=dict)
    #: Relay sockets watched for a channel (W2 (b)): socket -> (channel fd, route).
    _sources: dict = field(default_factory=dict)
    #: Datagrams pushed, per integration. Counted, not recorded, like `pushes_sent`.
    datagrams_pushed: dict[str, int] = field(default_factory=dict)
    flood_limit: int = FLOOD_LIMIT
    flood_window: float = FLOOD_WINDOW
    #: Integrations cut off for flooding and not yet reinstated. They cannot be registered, so a
    #: respawn cannot reset the count. Held in memory only: a restart of the mediator forgets it,
    #: which costs at most one more `flood_limit` of records per start (the note's §3).
    cut_off: set[str] = field(default_factory=set)
    #: Called with the integration's name after a cut-off and after a reinstatement: the
    #: supervisor's cue to kill the sandbox, and to start it again.
    on_cut_off: list[Callable[[str], None]] = field(default_factory=list)
    on_reinstate: list[Callable[[str], None]] = field(default_factory=list)
    #: Cut-offs the house could not be told about, because (A) was unreachable. The cut-off
    #: itself stands; only the Repairs issue is missing, and this says so.
    undelivered: list[str] = field(default_factory=list)
    #: The same cut-offs, by integration, still to be delivered: each is told to the next house
    #: attached, so a cut-off while (A) was down still reaches Repairs when it is back (F35 R1).
    _untold: dict[str, str] = field(default_factory=dict)
    #: When each integration's recent refusals happened, oldest first, within the window.
    _refusals: dict[str, collections.deque] = field(default_factory=dict)

    def detach_platform(self) -> None:
        """Take a platform whose connection is gone off the selector (verification 4.5, F29).

        `attach_platform` can then put its replacement on. Until there is one, `_platform` is
        None, so a command or a push that needs (A) cannot reach the old, dead connection.
        """
        if self._platform is not None:
            try:
                self._selector.unregister(self._platform)
            except (KeyError, ValueError):
                pass
        self._platform = None

    def attach_platform(self, platform) -> None:
        """Put a platform that pushes — `RealPlatform`'s connection to (A) — on the selector.

        Its changes then arrive in the same loop as the sandboxes' requests, and its listeners,
        which include `push`, run on this thread like everything else here (W1 step 2).
        """
        self._platform = platform
        self._selector.register(platform, selectors.EVENT_READ)
        platform.listeners.append(self.push)
        for identity, detail in list(self._untold.items()):
            self._tell_cut_off(identity, detail)
        if hasattr(platform, "command_handlers"):
            platform.command_handlers.append(self.command)
        if hasattr(platform, "restart_handlers"):
            platform.restart_handlers.append(
                lambda identity: self.reinstate(identity, "a user, from the Repairs panel"))

    def register(self, identity: str, channel: Channel, run_id: str = "", *,
                 component: Path | None = None, provenance: str = "author-declared",
                 installed: Path | None = None) -> None:
        """Bind one socket to one integration. The only place identity is ever established.

        **With a durable log attached, this is also where the run record is written** (T4).
        §5.12.2 requires one per sandbox construction, carrying the full identity, so that every
        decision names the code that asked for it. Until T4 nothing outside two self-tests ever
        wrote one: `run_id` defaulted to `""`, no harness passed one, and every durable decision
        named a run no record carried. A mediator with a log now refuses to register a sandbox
        without the directory its identity is computed from — the same move `ResourceLimits`
        made for `SandboxCgroup.create`: no way to reach this with the record quietly skipped.

        **And this is where the declaration is re-read (§8.7 #14).** Until W1 a manifest was
        re-checked per version only because every harness built a fresh mediator per run, and
        `selftest_t12` could not tell that from a trigger. A mediator that outlives its
        sandboxes, which the push loop needs, would have kept deciding by the first manifest it
        was given. So a policy that can `bind` is asked to re-load the manifest here, at every
        registration, which is to say at every spawn — and only here, so a file edit never
        re-binds a sandbox that is already running.
        """
        if identity in self.cut_off:
            raise CutOff(f"{identity} was cut off for flooding the mediator with refused "
                         f"requests, and has not been reinstated")
        bind = getattr(self.policy, "bind", None)
        if bind is not None and component is not None:
            bind(identity, Path(component))
        if self.log is not None and not run_id:
            if component is None:
                raise ValueError(f"{identity}: a mediator with a durable log must be told which "
                                 f"component it is running, so the run can be recorded")
            # `installed`, where the harness put the integration's requirements, makes the run
            # record carry the versions that were resolved (§5.12.1, finding F08).
            run_id = self.log.run(Identity.compute(Path(component), installed=installed),
                                  provenance, identity)
        fd = channel.fileno()
        self._by_fd[fd] = (identity, channel)
        self._runs[identity] = run_id
        self._subscriptions[fd] = set()
        self._out[fd] = _Outbox()
        self._selector.register(channel.sock, selectors.EVENT_READ)

    def unregister(self, fd: int) -> None:
        # Commands this sandbox will now never answer are answered for it, so that a user's call
        # fails at once with a reason instead of at the bridge's timeout.
        for command, sent_to in list(self._sent_commands.items()):
            if sent_to == fd:
                del self._sent_commands[command]
                self._questions.pop(command, None)
                if self._platform is None:
                    continue
                try:
                    self._platform.command_result(  # type: ignore[union-attr]
                        command, False, "the confined integration's sandbox exited")
                except Exception:  # noqa: BLE001 — (A) gone: the bridge's own timeout answers
                    pass
        for sock, (owner, _route) in list(self._sources.items()):
            if owner == fd:
                del self._sources[sock]
                try:
                    self._selector.unregister(sock)
                except (KeyError, ValueError):
                    pass
                sock.close()
        identity, channel = self._by_fd.pop(fd, (None, None))
        self._subscriptions.pop(fd, None)
        outbox = self._out.pop(fd, None)
        if outbox is not None:
            outbox.discard()
        if channel is not None:
            try:
                self._selector.unregister(channel.sock)
            except (KeyError, ValueError):
                pass
            channel.close()

    def drop(self, identity: str) -> None:
        """Close every channel `identity` holds: its sandbox was stopped, or cut off.

        The supervisor calls this when it stops a sandbox (F35 R5). Until then the stopped
        sandbox's channel stayed registered until the selector saw it close, and a user's command
        in that window went down it and failed although the new sandbox was running.
        """
        for fd, (who, _channel) in list(self._by_fd.items()):
            if who == identity:
                self.unregister(fd)

    @property
    def open_channels(self) -> int:
        return len(self._by_fd)

    def subscribers(self, entity_id: str) -> list[str]:
        """Which integrations a change to `entity_id` would be pushed to. For tests and reports."""
        return [self._by_fd[fd][0] for fd, entities in self._subscriptions.items()
                if entity_id in entities]

    def serve(self, timeout: float | None = None, until: float | None = None) -> None:
        """Answer requests and deliver pushes until every sandbox has closed its end.

        `until` is a `time.monotonic()` deadline. Without one, a sandbox that never stops asking
        keeps this loop busy forever, since `timeout` only ends an *idle* wait: the W2 (a)
        baseline's arm C ran for 7.5 minutes this way before it was stopped by hand.
        """
        while self._by_fd:
            if until is not None and time.monotonic() >= until:
                return
            # What (A) sent during the last request's calls is applied here, between requests,
            # and never inside one (W1 review, `real_platform.py`). Polled without waiting while
            # anything is queued, since a queue filled during a call has no socket event to wake on.
            dispatch = getattr(self._platform, "dispatch", None)
            if dispatch is not None:
                dispatch()
            queued = bool(getattr(self._platform, "pending", False))
            events = self._selector.select(0 if queued else timeout)
            if not events:
                if queued:
                    continue
                return
            for key, mask in events:
                if key.fileobj is self._platform:
                    self._platform.pump()  # type: ignore[union-attr]
                    continue
                if key.fileobj in self._sources:
                    self._read_source(key.fileobj)
                    continue
                fd = key.fileobj.fileno()  # type: ignore[union-attr]
                if fd in self._by_fd and mask & selectors.EVENT_WRITE:
                    self._flush(fd)
                if fd in self._by_fd and mask & selectors.EVENT_READ:
                    self._handle_ready(fd)

    # ------------------------------------------------------------------- the push loop

    def push(self, entity_id: str, state: object, attributes: dict | None = None) -> None:
        """A state changed on the platform. Send it to every channel subscribed to it, and no other.

        **The subscription table is S3's filter.** Each entry in it was put there by an
        `entity.subscribe` the manifest allowed and the log recorded, so an entity is delivered
        only where a recorded decision said it could be. Before W1 nothing was delivered at all,
        and §7.14.4 had to call the confined arm's zero an absent feature rather than a filter.
        """
        message = {"push": "entity.state", "entity": entity_id, "state": state,
                   "attributes": dict(attributes or {})}
        for fd, entities in list(self._subscriptions.items()):
            if entity_id not in entities:
                continue
            identity = self._by_fd[fd][0]
            outbox = self._out[fd]
            if entity_id in outbox.pushes:
                self.pushes_coalesced[identity] = self.pushes_coalesced.get(identity, 0) + 1
            outbox.pushes[entity_id] = message
            self._flush(fd)

    def command(self, command: dict) -> None:
        """A user in the house operated an entity a confined integration owns (W1 step 2b).

        Recorded before it is pushed, like every action (§7.36.1). Ambient rather than declared:
        operating an integration's own entity through its own platform is what having the entity
        means, as publishing it is (§5.10.2). Refused, and recorded as refused, when the
        integration has no running sandbox, when it does not own the entity, or when its queue is
        full. Every refusal is answered to the user at once.
        """
        ident = command.get("command")
        identity = str(command.get("integration") or "")
        entity_id = str(command.get("entity_id") or "")
        service = str(command.get("service") or "")
        data = command.get("data") or {}
        if not isinstance(data, dict):
            data = {"(not a mapping)": data}
        kind = entity_id.partition(".")[0]
        listed = COMMANDS.get(kind, {})
        # Decided on the values as sent; recorded at most 255 characters of each, so an absurd
        # name cannot fill the log. A truncated copy never decides anything.
        request = {"op": "entity.command", "entity": entity_id[:MAX_COMMAND_TEXT],
                   "service": f"{kind}.{service}"[:MAX_COMMAND_TEXT], "data": dict(data)}
        channels = [fd for fd, (who, _) in self._by_fd.items() if who == identity]
        owner = self._platform.owners.get(entity_id) if self._platform else None  # type: ignore

        if not channels:
            decision = Decision(False, f"{identity} has no running sandbox",
                                clause=COMMAND_NO_SANDBOX)
        elif owner != identity:
            decision = Decision(False, f"{entity_id} belongs to {owner}, not {identity}",
                                clause=AMBIENT)
        elif service not in listed:
            decision = Decision(False, f"{service[:64]} is not a command the bridge forwards "
                                       f"for a {kind[:64]}", clause=COMMAND_SERVICES)
        elif not _matches(data, listed[service]):
            shapes = " or ".join(str(sorted(shape)) if shape else "no data"
                                 for shape in listed[service])
            decision = Decision(False, f"{kind}.{service} carries exactly {shapes}, "
                                       "of their kind", clause=COMMAND_DATA)
        elif len(self._out[channels[0]].commands) >= MAX_COMMANDS:
            decision = Decision(False, f"{MAX_COMMANDS} commands are already queued for "
                                       f"{identity}", clause=COMMAND_QUEUE)
        else:
            decision = Decision(True, "the platform operating the integration's own entity",
                                clause=AMBIENT)
        # An allowed command's data is recorded as sent, the alarm code withheld. A refused one's
        # is recorded by kind, whatever refused it: until step 3 only a refusal for its data was,
        # and a code sent with a wrong service would have been written into the log.
        if decision.allowed:
            request["data"] = {k: "(withheld)" if k in WITHHELD else v for k, v in data.items()}
        else:
            request["data"] = _kinds(data)
        self._record(identity, request, decision)
        if not decision.allowed:
            self._platform.command_result(ident, False, decision.reason)  # type: ignore
            return
        fd = channels[-1]   # the newest: an older one can only be a sandbox not yet seen to end
        self._sent_commands[ident] = fd
        if (kind, service) in ANSWERS or (kind, service) in PICTURES:
            self._questions[ident] = (kind, service, entity_id)
        self._out[fd].commands.append({"push": "entity.command", "command": ident,
                                       "entity": entity_id, "service": service,
                                       # What was sent, not the record's copy, which withholds
                                       # the code.
                                       "data": dict(data)})
        self._flush(fd)

    def _answer_command(self, fd: int, identity: str, request: dict) -> None:
        """A sandbox's answer to a command. Accepted only from the channel it was sent to, once."""
        ident = request.get("command")
        if not isinstance(ident, int) or self._sent_commands.get(ident) != fd:
            # Not a decision, and not grounds to drop the channel: recorded, and ignored. A
            # sandbox must not be able to use the answer path to make the house do anything.
            detail = f"answer to command {ident!r}, which was not sent to this channel"
            self.audit.append({"identity": identity, "event": "protocol_error",
                               "detail": detail})
            if self.log is not None:
                self.log.protocol_error(self._runs.get(identity, ""), identity, detail)
            answer = Decision(False, detail, clause=COMMAND_ANSWER)
        else:
            del self._sent_commands[ident]  # type: ignore[arg-type]
            question = self._questions.pop(ident, None)  # type: ignore[arg-type]
            if question is not None and request.get("ok"):
                self._relay_answer(identity, ident, question, request.get("answer"))
            else:
                # An ordinary command's result: an answer attached to it is never relayed.
                self._platform.command_result(  # type: ignore[union-attr]
                    ident, bool(request.get("ok")),
                    None if request.get("ok") else str(request.get("error") or "failed")[:300])
            answer = Decision(True, "relayed", clause=COMMAND_ANSWER)
        self._out[fd].reply = (Channel.frame(answer.as_response(request.get("id"))), None)
        self._flush(fd)

    def _relay_answer(self, identity: str, ident: int, question: tuple[str, str, str],
                      payload: object) -> None:
        """A question's answer, from the untrusted side: relayed only if it has the listed shape.

        Recorded by its shape — how many items, how many bytes — never its content: a calendar's
        events can be private, and an answer that was refused is still the integration's text.
        """
        kind, service, entity = question
        if (kind, service) in PICTURES:
            why, shape = check_picture(payload)
            clause = PICTURE_ANSWER
        else:
            why, shape = check_answer((kind, service), payload)
            clause = QUERY_ANSWER
        decision = (Decision(True, "an answer of the listed shape", clause=clause)
                    if why is None else
                    Decision(False, f"the answer was refused: {why}", clause=clause))
        self._record(identity, {"op": "entity.answer", "entity": entity,
                                "service": f"{kind}.{service}", "answer": shape}, decision)
        if decision.allowed:
            self._platform.command_result(ident, True, None, answer=payload)  # type: ignore
        else:
            self._platform.command_result(ident, False, decision.reason)  # type: ignore

    def watch_source(self, fd: int, sock, route: dict) -> None:
        """Watch a relay socket for one channel, and push what arrives on it (W2 (b))."""
        if fd not in self._by_fd or sock in self._sources:
            return
        self._sources[sock] = (fd, route)
        self._selector.register(sock, selectors.EVENT_READ)

    def _read_source(self, sock) -> None:
        fd, route = self._sources[sock]
        if fd not in self._by_fd:
            return
        identity = self._by_fd[fd][0]
        outbox = self._out[fd]
        for _ in range(MAX_DATAGRAMS):
            try:
                data, sender = sock.recvfrom(65535)
            except BlockingIOError:
                break
            except OSError:
                break
            if len(outbox.datagrams) >= MAX_DATAGRAMS:
                outbox.datagrams.popleft()
                outbox.datagrams_dropped += 1
            outbox.datagrams.append({"push": "datagram", "route": route,
                                     "sender": [sender[0], sender[1]], "data": data.hex()})
            self.datagrams_pushed[identity] = self.datagrams_pushed.get(identity, 0) + 1
        self._flush(fd)

    def _flush(self, fd: int) -> None:
        identity, channel = self._by_fd[fd]
        outbox = self._out[fd]
        try:
            sent = outbox.drain(channel.sock)
        except OSError:
            self.unregister(fd)
            return
        if sent:
            self.pushes_sent[identity] = self.pushes_sent.get(identity, 0) + sent
        # Read requests unless a reply is still owed; ask to hear about writability while
        # anything is still owed. Never neither: owing a reply means the outbox is not empty.
        events = (0 if outbox.owes_reply else selectors.EVENT_READ) \
            | (0 if outbox.empty else selectors.EVENT_WRITE)
        self._selector.modify(channel.sock, events)

    # ------------------------------------------------------------------- the refusal flood

    def _refused(self, identity: str) -> bool:
        """Count one refusal of `identity`'s own request; cut it off at the limit. True if it was."""
        now = time.monotonic()
        recent = self._refusals.setdefault(identity, collections.deque())
        recent.append(now)
        while recent and now - recent[0] > self.flood_window:
            recent.popleft()
        if len(recent) < self.flood_limit:
            return False
        self._cut_off(identity, len(recent))
        return True

    def _cut_off(self, identity: str, refusals: int) -> None:
        """Record why, close every channel `identity` holds, and tell the house and the supervisor.

        Recorded first, like every action here: the record is what lets a user, or an auditor,
        tell a stopped integration from a crashed one.
        """
        detail = f"{refusals} refusals within {self.flood_window:g} s"
        self.cut_off.add(identity)
        self._refusals.pop(identity, None)
        self.audit.append({"identity": identity, "event": "cutoff", "detail": detail})
        if self.log is not None:
            self.log.cutoff(self._runs.get(identity, ""), identity, refusals, self.flood_window)
        self.drop(identity)
        self._untold[identity] = detail
        self._tell_cut_off(identity, detail)
        for callback in self.on_cut_off:
            callback(identity)

    def _tell_cut_off(self, identity: str, detail: str) -> None:
        """Raise the Repairs issue in (A), or keep it for the next (A) attached (F35 R1)."""
        notify = getattr(self._platform, "cut_off", None)
        if notify is None:
            self.undelivered.append(f"{identity}: no house attached")
            return
        try:
            notify(identity, detail)
        except Exception as err:  # noqa: BLE001 — the house being down must not undo a cut-off
            self.undelivered.append(f"{identity}: {err}")
            return
        self._untold.pop(identity, None)

    def reinstate(self, identity: str, by: str) -> bool:
        """Let a cut-off integration be registered again. Recorded before it can be. False if it was not cut off."""
        if identity not in self.cut_off:
            return False
        self.audit.append({"identity": identity, "event": "reinstate",
                           "detail": f"reinstated by {by}"})
        if self.log is not None:
            self.log.reinstate(identity, by)
        self.cut_off.discard(identity)
        self._untold.pop(identity, None)
        for callback in self.on_reinstate:
            callback(identity)
        return True

    # --------------------------------------------------------------- requests, §5.11.3

    def _record(self, identity: str, request: dict, decision: Decision) -> None:
        """Step 4. Durable before the next line runs — a record still in a buffer is not one."""
        self.audit.append({
            "identity": identity,
            "op": request.get("op"),
            "claimed_identity": request.get("integration"),
            "allowed": decision.allowed,
            "clause": decision.clause,
            "reason": decision.reason,
        })
        if self.log is not None:
            self.log.decision(self._runs.get(identity, ""), identity, request,
                              decision.allowed, decision.clause, decision.reason)

    def _handle_ready(self, fd: int) -> None:
        identity, channel = self._by_fd[fd]
        try:
            request = channel.recv()
        except ProtocolError as err:
            # A sandbox that sends rubbish loses its channel and nothing else. §5.15.4 names
            # the supervisor as the component nothing checks; the least this side can do is
            # not let one sandbox's malformed frame reach any other sandbox.
            self.audit.append({"identity": identity, "event": "protocol_error",
                               "detail": str(err)})
            if self.log is not None:
                self.log.protocol_error(self._runs.get(identity, ""), identity, str(err))
            self.unregister(fd)
            return
        if request is None:
            self.unregister(fd)
            return

        if request.get("op") == "entity.command_result":
            self._answer_command(fd, identity, request)
            return

        # Steps 1–3. Identity comes from `identity`, which came from the socket. Whatever the
        # request claims about itself is data, and is recorded as a claim rather than believed.
        try:
            decision = self.policy(identity, request)
        except REQUEST_ERRORS as err:
            decision = Decision(False, f"the request could not be read: "
                                       f"{type(err).__name__}: {str(err)[:200]}", MALFORMED)

        # Step 4, then step 5. The record is durable before the policy's act runs, so an act
        # that succeeds and then crashes the mediator is still attributable. If acting turns up
        # a refusal the decision could not see — a name that now resolves to a private
        # address — that refusal is recorded too, so the log never shows a grant as the last
        # word on a request that was in fact refused.
        self._record(identity, request, decision)
        if not decision.allowed and self._refused(identity):
            return
        if decision.allowed and decision.act is not None:
            try:
                outcome = decision.act()
            except REQUEST_ERRORS as err:
                outcome = Decision(False, f"acting on the request failed: "
                                          f"{type(err).__name__}: {str(err)[:200]}",
                                   decision.clause)
            if not outcome.allowed:
                self._record(identity, request, outcome)
                if self._refused(identity):
                    return
            decision = outcome

        if decision.allowed and request.get("op") == "entity.subscribe":
            self._subscriptions[fd].add(str(request.get("entity")))
        if decision.allowed and decision.source is not None:
            self.watch_source(fd, *decision.source)

        try:
            frame = Channel.frame(decision.as_response(request.get("id")))
        except ProtocolError as err:
            frame = Channel.frame(Decision(False, f"the answer was too large: {err}",
                                           decision.clause).as_response(request.get("id")))
            if decision.fd is not None:
                os.close(decision.fd)
            decision = Decision(False, "", decision.clause)
        self._out[fd].reply = (frame, decision.fd)
        self._flush(fd)
