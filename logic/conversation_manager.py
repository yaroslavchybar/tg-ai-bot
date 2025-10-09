"""
Orchestrates the bot's logic by coordinating between the AI service and database repositories.
"""

import logging
import json
import asyncio
import re

from logic.prompt_builder import build_lisa_prompt
from services.response_service import ResponseService

class ConversationManager:
    def __init__(self, ai_service, response_service, user_repo, message_repo, fact_repo, goal_repo, persona_repo, summary_repo, script_repo):
        self.ai_service = ai_service
        self.response_service = response_service
        self.user_repo = user_repo
        self.message_repo = message_repo
        self.fact_repo = fact_repo
        self.goal_repo = goal_repo
        self.persona_repo = persona_repo
        self.summary_repo = summary_repo
        self.script_repo = script_repo

    async def get_response(self, message: str, user_id: int, is_script_start: bool = False) -> str:
        """Handles incoming messages and generates an AI response."""
        try:
            # 1. Handle message saving and user setup
            if not is_script_start:
                # Normal user message - save it
                await self.message_repo.save_message(user_id, message, is_user=True)
                await self.user_repo.update_user_last_interaction(user_id)
            else:
                # Script start - don't save empty message, just ensure user exists
                await self.user_repo.save_user(user_id) # Ensure user exists

            await self.goal_repo.initialize_user_goals(user_id, self.user_repo) # Ensure user has goals

            # 2. Check if script is completed - if so, don't respond (unless it's script start)
            script_progress = await self.user_repo.get_script_progress(user_id)
            if script_progress == 'completed' and not is_script_start:
                logging.info(f"User {user_id} has completed script, not responding")
                return None

            # 3. Check if all goals for the day are completed
            day_stage = await self.user_repo.get_user_day_stage(user_id)
            all_goals_completed = await self.goal_repo.are_all_goals_completed_for_day(user_id, day_stage)

            if not all_goals_completed and not is_script_start:
                await self.user_repo.increment_conversation_counters(user_id)
            elif all_goals_completed and not is_script_start:
                # If all goals are done, reset the counter to prevent validation triggers.
                await self.user_repo.reset_messages_since_last_goal_only(user_id)

            # 4. Asynchronously trigger summary generation if needed, without blocking
            message_count = await self.message_repo.get_message_count_for_summary(user_id)
            if message_count > 25:
                asyncio.create_task(self._trigger_batch_summary(user_id))

            # 5. Get conversation state for goal tracking
            conversation_state = await self.user_repo.get_conversation_state(user_id)
            messages_since_last = conversation_state.get('messages_since_last_goal', 0)


            # 6. Handle script start or analyze message for fact changes
            fact_actions = []
            if not is_script_start:
                # Normal message processing - analyze for fact changes
                existing_facts = await self.fact_repo.get_user_facts_dict(user_id)
                fact_actions_json = await self.ai_service.analyze_fact_changes(message, existing_facts)
                try:
                    fact_actions = json.loads(fact_actions_json)
                    if fact_actions:
                        await self.fact_repo.execute_fact_actions(user_id, fact_actions)
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse fact actions JSON from AI: {fact_actions_json}")
            # For script starts, fact_actions remains empty (no fact analysis needed)

            # 7. Gather all context for the prompt
            persona_facts = await self.persona_repo.get_persona_facts()
            user_facts = await self.fact_repo.get_user_facts_dict(user_id)
            recent_messages = await self.message_repo.get_recent_messages(user_id, 27)
            relevant_summaries = await self.summary_repo.get_relevant_summaries(user_id, message, 3)

            # 8. Handle goal-oriented logic (this might reset the counter)
            goal_text = await self._get_goal_context(user_id)

            # 9. Build the prompt
            system_prompt = await build_lisa_prompt(
                goal_text=goal_text,
                persona_facts=persona_facts,
                user_facts=user_facts,
                recent_messages=recent_messages,
                relevant_summaries=relevant_summaries,
                user_id=user_id,
                user_repo=self.user_repo,
                script_repo=self.script_repo,
                is_script_start=is_script_start
            )

            # 10. Generate AI response
            # For script starts, use empty message or a trigger phrase
            response_message = "" if is_script_start else message
            ai_response = await self.response_service.generate_response(system_prompt, response_message)

            # 11. Check if this response ends the current script
            current_day = await self.user_repo.get_user_day_stage(user_id)
            current_stage = await self.user_repo.get_user_stage(user_id)
            script_text = await self.script_repo.get_script(current_day, current_stage)

            if script_text:
                last_bot_message = self._extract_last_bot_message(script_text)
                # Check if AI response matches the last bot message in script
                if ai_response.strip() == last_bot_message:
                    # Script has ended, mark as completed and advance stage
                    await self.user_repo.mark_script_completed_and_advance_stage(user_id)
                    # Trigger summary generation for completed script
                    asyncio.create_task(self._trigger_batch_summary(user_id))

            # 12. Check for message splitting by "$" symbol
            if "$" in ai_response:
                message_parts = [part.strip() for part in ai_response.split("$") if part.strip()]
                # Save each part as a separate message for consistency
                for part in message_parts:
                    await self.message_repo.save_message(user_id, part, is_user=False)
                return message_parts
            else:
                # 13. Save bot response
                await self.message_repo.save_message(user_id, ai_response, is_user=False)
                return ai_response

        except Exception as e:
            logging.error(f"ConversationManager failed: {e}", exc_info=True)
            return "I'm feeling a bit overwhelmed right now. Let's talk later."

    def _extract_last_bot_message(self, script_text: str) -> str:
        """Extract the last bot message from script text using regex."""
        # Find all bot messages (lines starting with "Nastya:")
        bot_messages = re.findall(r'^Nastya:\s*(.+)$', script_text, re.MULTILINE)
        # Return the last one, or empty string if none found
        return bot_messages[-1].strip() if bot_messages else ""

    async def _get_goal_context(self, user_id: int) -> str:
        """Determine the current goal text."""
        day_stage = await self.user_repo.get_user_day_stage(user_id)
        day_goals = await self.goal_repo.get_master_goals_for_day(day_stage)
        pending_goals = await self.goal_repo.get_pending_user_goals(user_id)

        goal_text = day_goals[0]['goal_text'] if day_goals else "General conversation."

        conversation_state = await self.user_repo.get_conversation_state(user_id)
        messages_since_last = conversation_state.get('messages_since_last_goal', 0)

        # Simplified goal logic without mood detection
        if pending_goals:
            askable_goal = pending_goals[0]
            goal_text = askable_goal['master_goals']['goal_text']
            logging.info(f"Using goal: {goal_text}")

        return goal_text

    async def _trigger_batch_summary(self, user_id: int):
        """
        Summarizes all available messages when triggered by script completion.
        Processes all messages at once rather than in batches.
        """
        try:
            # Get all available messages for summarization
            messages_to_process = await self.message_repo.get_all_messages(user_id)

            if not messages_to_process:
                logging.info(f"User {user_id} has no messages to summarize.")
                return

            logging.info(f"User {user_id} has {len(messages_to_process)} messages. Processing all for summary.")

            # Process all messages at once (no batching needed for script completion)
            conversation_text = "\n".join([f"{m['role']}: {m['text']}" for m in messages_to_process])
            summary_text = await self.ai_service.generate_rolling_summary(conversation_text)

            if summary_text:
                await self.summary_repo.save_summary(user_id, summary_text)
                logging.info(f"Generated summary for user {user_id} after script completion.")

            # Delete the processed messages
            if messages_to_process:
                await self.message_repo.delete_messages_batch(user_id, messages_to_process)
                logging.info(f"Batch summary complete for user {user_id}. Deleted {len(messages_to_process)} messages.")

        except Exception as e:
            logging.error(f"Error during async batch summary for user {user_id}: {e}", exc_info=True)




