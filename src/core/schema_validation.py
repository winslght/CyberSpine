"""Fail-closed data-only validators for the seven G1 window payload schemas."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .gateway_errors import GatewayRejected, GatewayRejectionCode

PayloadValidator = Callable[[Mapping[str, Any]], None]
_SENSITIVE = {
    "windowtitle",
    "title",
    "path",
    "text",
    "clipboard",
    "keystroke",
    "mousecoordinates",
    "screenpixels",
    "typedtext",
    "password",
    "content",
}


def _bad(detail: str = "payload does not match registered schema") -> None:
    raise GatewayRejected(GatewayRejectionCode.SCHEMA_INVALID, detail)


def _map(v: Any, keys: set[str], req: set[str] = frozenset()) -> Mapping[str, Any]:
    if not isinstance(v, Mapping):
        _bad()
    for k in v:
        n = "".join(c for c in k.lower() if c.isalnum()) if isinstance(k, str) else ""
        if not isinstance(k, str):
            _bad("payload keys must be strings")
        if n != "hastitle" and any(s in n for s in _SENSITIVE):
            raise GatewayRejected(
                GatewayRejectionCode.PRIVACY_EXCEEDED, "payload includes prohibited field"
            )
    if set(v) - keys or not req.issubset(v):
        _bad()
    return v


def _scalar(v: Any, types: tuple[type, ...], nullable: bool = False) -> None:
    if v is None and nullable:
        return
    if type(v) not in types:
        _bad()


def _str(v: Any) -> None:
    _scalar(v, (str,))


def _int(v: Any) -> None:
    _scalar(v, (int,))


def _num(v: Any) -> None:
    _scalar(v, (int, float))


def _bool(v: Any) -> None:
    _scalar(v, (bool,))


def _list(v: Any, item: Callable[[Any], None]) -> None:
    if not isinstance(v, list):
        _bad()
    for x in v:
        item(x)


def _bounds(v: Any) -> None:
    x = _map(v, {"left", "top", "width", "height"}, {"left", "top", "width", "height"})
    for a in x.values():
        _int(a)


def _display(v: Any) -> None:
    if v is None:
        return
    x = _map(v, {"id", "bounds"}, {"id", "bounds"})
    _str(x["id"])
    _bounds(x["bounds"])


def _interaction(v: Any) -> None:
    x = _map(
        v,
        {
            "period_seconds",
            "event_count",
            "events_per_minute",
            "is_high_frequency",
            "last_interaction_monotonic",
        },
        {
            "period_seconds",
            "event_count",
            "events_per_minute",
            "is_high_frequency",
            "last_interaction_monotonic",
        },
    )
    _num(x["period_seconds"])
    _int(x["event_count"])
    _num(x["events_per_minute"])
    _bool(x["is_high_frequency"])
    _scalar(x["last_interaction_monotonic"], (int, float), True)


def _window(v: Any) -> None:
    keys = {
        "window_id",
        "application",
        "pid",
        "bounds",
        "z_order",
        "is_foreground",
        "is_minimized",
        "is_maximized",
        "is_topmost",
        "display",
        "has_title",
        "presentation",
        "window_state",
        "geometry_activity",
        "focus_dwell_seconds",
        "interaction",
    }
    x = _map(v, keys, {"window_id", "application", "pid", "bounds"})
    _str(x["window_id"])
    _str(x["application"])
    _scalar(x["pid"], (int,), True)
    _bounds(x["bounds"])
    if "z_order" in x:
        _int(x["z_order"])
    for k in {"is_foreground", "is_minimized", "is_maximized", "is_topmost", "has_title"} & set(x):
        _bool(x[k])
    if "display" in x:
        _display(x["display"])
    if "presentation" in x:
        p = _map(
            x["presentation"],
            {"state", "is_screen_present", "is_user_presented", "display_bounds_known"},
            {"state", "is_screen_present", "is_user_presented", "display_bounds_known"},
        )
        _str(p["state"])
        _bool(p["is_screen_present"])
        _bool(p["is_user_presented"])
        _bool(p["display_bounds_known"])
    if "window_state" in x:
        s = _map(
            x["window_state"],
            {
                "is_maximized",
                "is_topmost",
                "is_fullscreen_candidate",
                "fullscreen_detection",
                "display",
            },
            {
                "is_maximized",
                "is_topmost",
                "is_fullscreen_candidate",
                "fullscreen_detection",
                "display",
            },
        )
        _bool(s["is_maximized"])
        _bool(s["is_topmost"])
        _bool(s["is_fullscreen_candidate"])
        _str(s["fullscreen_detection"])
        _display(s["display"])
    if "geometry_activity" in x:
        g = _map(
            x["geometry_activity"],
            {"state", "is_in_progress_candidate", "detection_basis"},
            {"state", "is_in_progress_candidate", "detection_basis"},
        )
        _str(g["state"])
        _bool(g["is_in_progress_candidate"])
        _str(g["detection_basis"])
    if "focus_dwell_seconds" in x:
        _num(x["focus_dwell_seconds"])
    if "interaction" in x:
        _interaction(x["interaction"])


def _current(p: Mapping[str, Any]) -> None:
    x = _map(
        p,
        {
            "foreground",
            "window_count",
            "foreground_status",
            "foreground_confidence",
            "foreground_resolution_reason",
            "last_confirmed_foreground_age_seconds",
            "interaction_observation",
            "input_monitor_callback_errors",
            "event_observation",
            "event_source_callback_errors",
            "window_inventory_read_errors",
            "event_diagnostics",
        },
        {"window_count", "foreground_status"},
    )
    _int(x["window_count"])
    _str(x["foreground_status"])
    if x.get("foreground") is not None:
        _window(x["foreground"])
    for k in {
        "foreground_confidence",
        "foreground_resolution_reason",
        "interaction_observation",
        "event_observation",
    } & set(x):
        _str(x[k])
    if "last_confirmed_foreground_age_seconds" in x:
        _scalar(x["last_confirmed_foreground_age_seconds"], (int, float), True)
    for k in {
        "input_monitor_callback_errors",
        "event_source_callback_errors",
        "window_inventory_read_errors",
    } & set(x):
        _int(x[k])
    if "event_diagnostics" in x:
        d = _map(
            x["event_diagnostics"],
            {"source", "ticket_count", "kinds", "window_identifiers_included"},
            {"source", "ticket_count", "kinds", "window_identifiers_included"},
        )
        _str(d["source"])
        _int(d["ticket_count"])
        _list(d["kinds"], _str)
        _bool(d["window_identifiers_included"])


def _catalog(p: Mapping[str, Any]) -> None:
    x = _map(
        p,
        {
            "windows",
            "window_count",
            "screen_present_window_count",
            "screen_present_user_window_count",
            "screen_present_user_window_ids",
        },
        {"windows", "window_count"},
    )
    _list(x["windows"], _window)
    _int(x["window_count"])
    for k in {"screen_present_window_count", "screen_present_user_window_count"} & set(x):
        _int(x[k])
    if "screen_present_user_window_ids" in x:
        _list(x["screen_present_user_window_ids"], _str)


def _focus(p: Mapping[str, Any]) -> None:
    x = _map(p, {"previous", "current"}, {"previous", "current"})
    if x["previous"] is not None:
        _window(x["previous"])
    if x["current"] is not None:
        _window(x["current"])


def _activity(p: Mapping[str, Any]) -> None:
    x = _map(
        p,
        {"previous_window_ids", "current_window_ids", "period_seconds"},
        {"previous_window_ids", "current_window_ids", "period_seconds"},
    )
    _list(x["previous_window_ids"], _str)
    _list(x["current_window_ids"], _str)
    _num(x["period_seconds"])


def _segment(v: Any) -> None:
    x = _map(
        v,
        {"window_id", "application", "pid", "duration_seconds", "is_active"},
        {"window_id", "application", "pid", "duration_seconds", "is_active"},
    )
    _str(x["window_id"])
    _str(x["application"])
    _scalar(x["pid"], (int,), True)
    _num(x["duration_seconds"])
    _bool(x["is_active"])


def _summary(v: Any) -> None:
    x = _map(
        v,
        {
            "window_id",
            "application",
            "pid",
            "focus_seconds",
            "focus_segment_count",
            "focus_ratio",
            "interaction",
        },
        {
            "window_id",
            "application",
            "pid",
            "focus_seconds",
            "focus_segment_count",
            "focus_ratio",
            "interaction",
        },
    )
    _str(x["window_id"])
    _str(x["application"])
    _scalar(x["pid"], (int,), True)
    _num(x["focus_seconds"])
    _int(x["focus_segment_count"])
    _num(x["focus_ratio"])
    _interaction(x["interaction"])


def _time(p: Mapping[str, Any]) -> None:
    keys = {
        "period_seconds",
        "elapsed_seconds",
        "observed_seconds",
        "unattributed_seconds",
        "coverage_ratio",
        "focus_switch_count",
        "segments",
        "windows",
        "foreground_window_id",
        "foreground_status",
        "time_accounting_invariant",
    }
    x = _map(p, keys, {"period_seconds", "segments", "windows", "foreground_status"})
    _num(x["period_seconds"])
    _list(x["segments"], _segment)
    _list(x["windows"], _summary)
    _str(x["foreground_status"])
    for k in {
        "elapsed_seconds",
        "observed_seconds",
        "unattributed_seconds",
        "coverage_ratio",
    } & set(x):
        _num(x[k])
    if "focus_switch_count" in x:
        _int(x["focus_switch_count"])
    if "foreground_window_id" in x:
        _scalar(x["foreground_window_id"], (str,), True)
    if "time_accounting_invariant" in x:
        _str(x["time_accounting_invariant"])


def _availability(p: Mapping[str, Any]) -> None:
    x = _map(
        p,
        {"previous_status", "current_status", "reason", "recovered_foreground"},
        {"previous_status", "current_status", "reason", "recovered_foreground"},
    )
    _str(x["previous_status"])
    _str(x["current_status"])
    _str(x["reason"])
    if x["recovered_foreground"] is not None:
        _window(x["recovered_foreground"])


def _change(v: Any) -> None:
    x = _map(
        v,
        {
            "window",
            "previous_bounds",
            "current_bounds",
            "change",
            "previous_display",
            "current_display",
            "is_in_progress_candidate",
            "detection_basis",
        },
        {
            "window",
            "previous_bounds",
            "current_bounds",
            "change",
            "previous_display",
            "current_display",
            "is_in_progress_candidate",
            "detection_basis",
        },
    )
    _window(x["window"])
    _bounds(x["previous_bounds"])
    _bounds(x["current_bounds"])
    _str(x["change"])
    _display(x["previous_display"])
    _display(x["current_display"])
    _bool(x["is_in_progress_candidate"])
    _str(x["detection_basis"])


def _geometry(p: Mapping[str, Any]) -> None:
    x = _map(p, {"changes"}, {"changes"})
    _list(x["changes"], _change)


WINDOW_PAYLOAD_VALIDATORS: dict[str, PayloadValidator] = {
    "window.current_state@3": _current,
    "window.catalog@1": _catalog,
    "window.focus_changed@2": _focus,
    "window.high_interaction_changed@1": _activity,
    "window.time_window_summary@1": _time,
    "window.foreground_availability_changed@1": _availability,
    "window.geometry_changed@1": _geometry,
}


def validate_payload(schema: str, payload: Mapping[str, Any]) -> None:
    validator = WINDOW_PAYLOAD_VALIDATORS.get(schema)
    if validator is None:
        _bad("payload schema has no registered validator")
    validator(payload)
