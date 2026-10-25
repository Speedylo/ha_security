"""Calendars published by confined integrations (bridge step 4, 2026-10-25).

The current event comes from the published attributes, as Home Assistant's own calendar writes them
(`message`, `start_time`, `end_time`, `all_day`, `location`, `description`); Home Assistant derives
the state from it. A calendar view's events are a **question** to the integration: `get_events`,
which the mediator forwards and whose answer it checks before it reaches this entity.
"""

from __future__ import annotations

import datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .entity import BridgedEntity, setup_platform


def _moment(value: str) -> datetime.date | datetime.datetime:
    """An ISO date, or an ISO date-time (given a time zone if it has none)."""
    if len(value) == 10:
        return datetime.date.fromisoformat(value)
    moment = datetime.datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt_util.get_default_time_zone())
    return moment


class BridgedCalendar(BridgedEntity, CalendarEntity):

    _described = frozenset({"message", "start_time", "end_time", "all_day", "location",
                            "description", "offset_reached"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._bridged_event: CalendarEvent | None = None
        if not attributes.get("message") or not attributes.get("start_time"):
            return
        try:
            start, end = _moment(attributes["start_time"]), _moment(attributes["end_time"])
            if attributes.get("all_day"):
                start, end = _date(start), _date(end)
            self._bridged_event = CalendarEvent(
                start=start, end=end, summary=str(attributes["message"]),
                description=attributes.get("description") or None,
                location=attributes.get("location") or None)
        except (KeyError, TypeError, ValueError):
            self._bridged_event = None

    @property
    def event(self) -> CalendarEvent | None:
        return self._bridged_event

    def _restorable_empty(self) -> bool:
        return False   # the state is derived from the event, which the roster restores

    def _restore(self, state: str) -> None:
        pass

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime.datetime,
                               end_date: datetime.datetime) -> list[CalendarEvent]:
        answer = await self._data.command(self._integration, self._published_id, "get_events",
                                          {"start": start_date.isoformat(),
                                           "end": end_date.isoformat()})
        return [CalendarEvent(start=_moment(item["start"]), end=_moment(item["end"]),
                              summary=item["summary"], description=item.get("description"),
                              location=item.get("location"))
                for item in answer or []]


def _date(moment: datetime.date | datetime.datetime) -> datetime.date:
    return moment.date() if isinstance(moment, datetime.datetime) else moment


async_setup_entry = setup_platform("calendar", BridgedCalendar)
