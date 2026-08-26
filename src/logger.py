from datetime import datetime
from zoneinfo import ZoneInfo

import structlog

SYMBOLS = {"start": "⏳", "ok": "✅", "error": "❌"}

# The firm operates on Prague time; structlog's built-in TimeStamper defaults
# to UTC (2h behind Prague in summer, 1h in winter), which reads as wrong in
# the logs. Same ZoneInfo pattern already used for booking emails elsewhere
# in this codebase (agent_rules/strings.py's _PRAGUE_TZ).
_PRAGUE_TZ = ZoneInfo("Europe/Prague")


def _prague_timestamper(logger, method_name, event_dict):
    event_dict["timestamp"] = datetime.now(_PRAGUE_TZ).strftime("%H:%M:%S")
    return event_dict


_logging_configured = False


def configure_logging() -> None:
    global _logging_configured
    if _logging_configured:
        return

    structlog.configure(
        processors=[
            _prague_timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # Using ConsoleRenderer with colors disabled or customized if needed, 
            # but ensure exception and long strings don't drop context:
            structlog.dev.ConsoleRenderer(colors=True, pad_level=8),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    _logging_configured = True


def get_logger():
    return structlog.get_logger()


def log_event(event: str, status: str = "ok", **kwargs) -> None:
    symbol = SYMBOLS.get(status, "")
    # Explicitly force conversion of kwargs values to prevent silent truncations on complex payloads
    safe_kwargs = {k: str(v) if not isinstance(v, (int, float, bool, type(None))) else v for k, v in kwargs.items()}
    get_logger().info(f"{symbol} {event}", **safe_kwargs)