import asyncio

from src.config import settings
from src.logger import configure_logging, get_logger, log_event
from src.bots.tgbot.bot import start_tgbot

async def main():
    configure_logging()
    logger = get_logger()
    
    log_event(
        event=f"Starting bot worker for client: {settings.CLIENT_ID}", 
        status="start"
    )

    try:
        await start_tgbot()
        
        # log_event(event="Initializing multi-platform bots...", status="start")
        # await asyncio.gather(
        #     start_tgbot(),
        #     start_instabot()
        # )
        
    except Exception as e:
        log_event(event="Bot worker crashed", status="error")
        logger.error("Critical error during bot execution", error=str(e), exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        configure_logging() 
        log_event(event="Bot stopped properly", status="ok")