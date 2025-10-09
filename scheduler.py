"""
Scheduler for running automated maintenance tasks.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

class MaintenanceScheduler:
    def __init__(self, maintenance_service):
        self.maintenance_service = maintenance_service
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Set up all scheduled maintenance jobs."""
        # Daily maintenance - every 50 minutes for testing
        self.scheduler.add_job(
            func=self.maintenance_service.trigger_daily_maintenance,
            trigger=CronTrigger(minute='*/10'),
            id='daily_maintenance',
            name='Daily Maintenance',
            replace_existing=True
        )

        # Evening script progress reset - daily at 8 PM Kyiv time
        self.scheduler.add_job(
            func=self.maintenance_service.reset_evening_script_progress,
            trigger=CronTrigger(hour=18, minute=20, timezone=ZoneInfo("Europe/Kiev")),  # 8 PM Kyiv time
            id='evening_script_reset',
            name='Evening Script Progress Reset',
            replace_existing=True
        )

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logging.info("Maintenance scheduler started.")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logging.info("Maintenance scheduler stopped.")