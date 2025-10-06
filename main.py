"""
Main entry point for the bot.
Initializes the Telegram client and starts the scheduler and bot.
"""

import asyncio
import logging

from config import telegram_client
from bot import conversation_manager # Import the initialized manager
from scheduler import MaintenanceScheduler
from services.maintenance_service import MaintenanceService
from bot import (
    ai_service,
    user_repo,
    message_repo,
    summary_repo
)

async def main():
    """Main function to start the bot with scheduler."""
    logging.info("Starting AI-powered bot...")

    # Initialize the maintenance service and scheduler
    maintenance_service = MaintenanceService(ai_service, user_repo, message_repo, summary_repo)
    maintenance_scheduler = MaintenanceScheduler(maintenance_service)
    maintenance_scheduler.start()

    logging.info("Bot is starting...")
    try:
        await telegram_client.start()
        logging.info("Bot client started successfully")
        await telegram_client.run_until_disconnected()
    finally:
        logging.info("Shutting down gracefully...")
        maintenance_scheduler.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
