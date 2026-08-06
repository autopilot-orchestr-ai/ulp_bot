import structlog

SYMBOLS = {"start": "⏳", "ok": "✅", "error": "❌"}


_logging_configured = False


def configure_logging() -> None:
    global _logging_configured
    if _logging_configured:
        return
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.dev.ConsoleRenderer(),
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
    get_logger().info(f"{symbol} {event}", **kwargs)