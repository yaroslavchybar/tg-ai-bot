"""
Scheduler for running automated maintenance tasks.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class MaintenanceScheduler:
    def __init__(self, maintenance_service):
        self.maintenance_service = maintenance_service
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Set up all scheduled maintenance jobs."""
        self.scheduler.add_job(
            func=self.maintenance_service.trigger_daily_maintenance,
            trigger=CronTrigger(minute='*/50'),  # Every 50 minutes for testing
            id='daily_maintenance',
            name='Daily Maintenance',
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