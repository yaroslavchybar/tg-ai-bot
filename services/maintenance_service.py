"""
Service to handle scheduled maintenance tasks like daily recaps and summaries.
"""

import logging
import asyncio
from datetime import datetime, timedelta

class MaintenanceService:
    def __init__(self, ai_service, user_repo, message_repo, summary_repo, conversation_manager, telegram_client):
        self.ai_service = ai_service
        self.user_repo = user_repo
        self.message_repo = message_repo
        self.summary_repo = summary_repo
        self.conversation_manager = conversation_manager
        self.telegram_client = telegram_client

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

    async def reset_evening_script_progress(self):
        """
        Reset script_progress to 'not_started' for all users with stage='evening' and script_progress='completed'.
        Then automatically start their evening scripts by sending the first bot message.
        Runs daily at 8 PM Kyiv time to prepare for the next day.
        """
        logging.info("--- Starting Evening Script Progress Reset ---")
        try:
            # Get all users with evening stage and completed script
            users_to_reset = await self.user_repo.get_users_with_evening_stage_completed_script()

            if not users_to_reset:
                logging.info("SCRIPT RESET: No users found with evening stage and completed script.")
                return

            logging.info(f"SCRIPT RESET: Found {len(users_to_reset)} users to reset: {[u['user_id'] for u in users_to_reset]}")

            reset_count = 0
            started_count = 0
            for user in users_to_reset:
                user_id = user['user_id']
                try:
                    # Reset script progress to not_started
                    success = await self.user_repo.set_script_progress(user_id, 'not_started')
                    if success:
                        reset_count += 1
                        logging.info(f"SCRIPT RESET: Reset user {user_id} script_progress to 'not_started'")

                        # Start evening script automatically
                        try:
                            # Use conversation manager to start script (empty message, script_start=True)
                            # This will generate the first bot message and save it to database
                            ai_response = await self.conversation_manager.get_response("", user_id, is_script_start=True)

                            # Now send the message via Telegram
                            if ai_response:
                                await self.telegram_client.send_message(user_id, ai_response)
                                started_count += 1
                                logging.info(f"SCRIPT RESET: Started evening script for user {user_id} - sent message via Telegram")
                            else:
                                logging.warning(f"SCRIPT RESET: No response generated for user {user_id}")
                        except Exception as e:
                            logging.error(f"SCRIPT RESET: Failed to start evening script for user {user_id}: {e}")
                    else:
                        logging.error(f"SCRIPT RESET: Failed to reset script_progress for user {user_id}")
                except Exception as e:
                    logging.error(f"SCRIPT RESET: Error processing user {user_id}: {e}")

            logging.info(f"--- Evening Script Progress Reset Completed: {reset_count} reset, {started_count} scripts started ---")

        except Exception as e:
            logging.error(f"SCRIPT RESET ERROR: An error occurred during evening script progress reset: {e}", exc_info=True)