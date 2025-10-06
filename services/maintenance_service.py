"""
Service to handle scheduled maintenance tasks like daily recaps and summaries.
"""

import logging
import asyncio
from datetime import datetime, timedelta

class MaintenanceService:
    def __init__(self, ai_service, user_repo, message_repo, summary_repo):
        self.ai_service = ai_service
        self.user_repo = user_repo
        self.message_repo = message_repo
        self.summary_repo = summary_repo

    async def trigger_daily_maintenance(self):
        """Run all daily maintenance tasks for all active users."""
        logging.info("--- Starting Daily Maintenance Cycle ---")
        try:
            active_users = await self.user_repo.get_active_users()
            if not active_users:
                logging.info("MAINTENANCE: No active users found to process.")
                return

            logging.info(f"MAINTENANCE: Found {len(active_users)} active users: {[u['user_id'] for u in active_users]}")
            for user in active_users:
                user_id = user['user_id']
                logging.info(f"MAINTENANCE: Processing user {user_id} for daily recap...")
                await self.run_daily_recap_for_user(user_id)

            logging.info("--- Daily Maintenance Cycle Completed ---")
        except Exception as e:
            logging.error(f"MAINTENANCE ERROR: An error occurred during the daily maintenance cycle: {e}", exc_info=True)

    async def run_daily_recap_for_user(self, user_id: int):
        """
        Generates a daily recap for the user by summarizing the day's summaries.
        """
        logging.info(f"MAINTENANCE: Running daily recap for user {user_id}")
        try:
            # 1. Fetch all of the day's summaries
            daily_summaries = await self.summary_repo.get_daily_summaries_for_recap(user_id)
            if not daily_summaries or len(daily_summaries) < 2:
                logging.info(f"MAINTENANCE: Not enough summaries to create a daily recap for user {user_id}.")
                return

            # 2. Combine them into a single context
            summaries_context = "\n\n".join([s['summary_text'] for s in daily_summaries])
            
            # 3. Generate the daily recap from the combined context
            daily_recap_text = await self.ai_service.generate_daily_recap(summaries_context)
            if not daily_recap_text:
                logging.error(f"MAINTENANCE: AI failed to generate daily recap for user {user_id}.")
                return

            # 4. Save the new daily recap
            await self.summary_repo.save_summary(user_id, daily_recap_text, is_daily_recap=True)
            logging.info(f"MAINTENANCE: Successfully created and saved daily recap for user {user_id}.")

            # 5. Delete the individual summaries that have been processed
            await self.summary_repo.delete_summaries_batch(user_id, daily_summaries)
            logging.info(f"MAINTENANCE: Deleted {len(daily_summaries)} individual summaries for user {user_id}.")

        except Exception as e:
            logging.error(f"MAINTENANCE: Error during daily recap for user {user_id}: {e}", exc_info=True)