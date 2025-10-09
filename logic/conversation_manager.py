"""
Orchestrates the bot's logic by coordinating between the AI service and database repositories.
"""

import logging
import json
import asyncio

from logic.prompt_builder import build_lisa_prompt
from services.response_service import ResponseService

class ConversationManager:
    def __init__(self, ai_service, response_service, user_repo, message_repo, fact_repo, goal_repo, persona_repo, summary_repo):
        self.ai_service = ai_service
        self.response_service = response_service
        self.user_repo = user_repo
        self.message_repo = message_repo
        self.fact_repo = fact_repo
        self.goal_repo = goal_repo
        self.persona_repo = persona_repo
        self.summary_repo = summary_repo

    async def get_response(self, message: str, user_id: int) -> str:
        """Handles incoming messages and generates an AI response."""
        try:
            # 1. Save user message and update user interaction time
            await self.message_repo.save_message(user_id, message, is_user=True)
            await self.user_repo.save_user(user_id) # Ensure user exists
            await self.goal_repo.initialize_user_goals(user_id, self.user_repo) # Ensure user has goals
            await self.user_repo.update_user_last_interaction(user_id)

            # Check if all goals for the day are completed
            day_stage = await self.user_repo.get_user_day_stage(user_id)
            all_goals_completed = await self.goal_repo.are_all_goals_completed_for_day(user_id, day_stage)

            if not all_goals_completed:
                await self.user_repo.increment_conversation_counters(user_id)
            else:
                # If all goals are done, reset the counter to prevent validation triggers.
                await self.user_repo.reset_messages_since_last_goal_only(user_id)

            # Asynchronously trigger summary generation if needed, without blocking
            message_count = await self.message_repo.get_message_count_for_summary(user_id)
            if message_count > 25:
                asyncio.create_task(self._trigger_batch_summary(user_id))

            # Get conversation state for goal tracking
            conversation_state = await self.user_repo.get_conversation_state(user_id)
            messages_since_last = conversation_state.get('messages_since_last_goal', 0)


            # 2. Analyze message for fact changes (add, update, delete)
            existing_facts = await self.fact_repo.get_user_facts_dict(user_id)
            fact_actions_json = await self.ai_service.analyze_fact_changes(message, existing_facts)
            try:
                fact_actions = json.loads(fact_actions_json)
                if fact_actions:
                    await self.fact_repo.execute_fact_actions(user_id, fact_actions)
            except json.JSONDecodeError:
                logging.error(f"Failed to parse fact actions JSON from AI: {fact_actions_json}")

            # 3. Gather all context for the prompt
            persona_facts = await self.persona_repo.get_persona_facts()
            user_facts = await self.fact_repo.get_user_facts_dict(user_id)
            recent_messages = await self.message_repo.get_recent_messages(user_id, 27)
            relevant_summaries = await self.summary_repo.get_relevant_summaries(user_id, message, 3)

            # 4. Handle goal-oriented logic (this might reset the counter)
            goal_text = await self._get_goal_context(user_id)

            # 5. Build the prompt
            system_prompt = build_lisa_prompt(
                goal_text=goal_text,
                persona_facts=persona_facts,
                user_facts=user_facts,
                recent_messages=recent_messages,
                relevant_summaries=relevant_summaries
            )

            # 6. Generate AI response
            ai_response = await self.response_service.generate_response(system_prompt, message)

            # 7. Save bot response
            await self.message_repo.save_message(user_id, ai_response, is_user=False)

            # 8. Post-response processing (no more goal completion here since it was done early)

            return ai_response

        except Exception as e:
            logging.error(f"ConversationManager failed: {e}", exc_info=True)
            return "I'm feeling a bit overwhelmed right now. Let's talk later."

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
        Summarizes messages in full batches of 20 and deletes only the summarized messages.
        Triggered when message count > 25.
        """
        try:
            # More efficient implementation
            message_count = await self.message_repo.get_message_count_for_summary(user_id)
            if message_count < 20:
                return

            # Calculate how many messages to fetch (only full batches of 20)
            num_to_process = (message_count // 20) * 20
            
            # Fetch only the required messages
            messages_to_process = await self.message_repo.get_messages_for_summary_batch(user_id, num_to_process)

            logging.info(f"User {user_id} has {message_count} messages. Processing {len(messages_to_process)} in batches.")

            for i in range(0, len(messages_to_process), 20):
                batch = messages_to_process[i:i+20]
                if not batch:
                    continue
                
                conversation_text = "\n".join([f"{m['role']}: {m['text']}" for m in batch])
                summary_text = await self.ai_service.generate_rolling_summary(conversation_text)
                
                if summary_text:
                    await self.summary_repo.save_summary(user_id, summary_text)

            # Delete the processed messages
            if messages_to_process:
                await self.message_repo.delete_messages_batch(user_id, messages_to_process)
                logging.info(f"Batch summary complete for user {user_id}. Deleted {len(messages_to_process)} messages.")

        except Exception as e:
            logging.error(f"Error during async batch summary for user {user_id}: {e}", exc_info=True)




