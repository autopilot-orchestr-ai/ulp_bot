import sys
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
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # Using ConsoleRenderer with colors disabled or customized if needed, 
            # but ensure exception and long strings don't drop context:
            structlog.dev.ConsoleRenderer(colors=True, pad_level=8),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
    )
    _logging_configured = True


def get_logger():
    return structlog.get_logger()


def log_event(event: str, status: str = "ok", **kwargs) -> None:
    symbol = SYMBOLS.get(status, "")
    # Explicitly force conversion of kwargs values to prevent silent truncations on complex payloads
    safe_kwargs = {k: str(v) if not isinstance(v, (int, float, bool, type(None))) else v for k, v in kwargs.items()}
    get_logger().info(f"{symbol} {event}", **safe_kwargs)