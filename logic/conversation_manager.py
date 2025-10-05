"""
Orchestrates the bot's logic by coordinating between the AI service and database repositories.
"""

import logging
import json
import asyncio

from logic.prompt_builder import build_lisa_prompt

class ConversationManager:
    def __init__(self, ai_service, user_repo, message_repo, fact_repo, goal_repo, persona_repo, summary_repo):
        self.ai_service = ai_service
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
            await self.goal_repo.initialize_user_goals(user_id, self.user_repo, self.fact_repo) # Ensure user has goals
            await self.user_repo.update_user_last_interaction(user_id)

            # Check if all goals for the day are completed
            day_stage = await self.user_repo.get_user_day_stage(user_id)
            all_goals_completed = await self.goal_repo.are_all_goals_completed_for_day(user_id, day_stage)

            if not all_goals_completed:
                await self.user_repo.increment_conversation_counters(user_id)

            # Asynchronously trigger summary generation if needed, without blocking
            message_count = await self.message_repo.get_message_count_for_summary(user_id)
            if message_count > 25:
                asyncio.create_task(self._trigger_batch_summary(user_id))

            # 2. Extract facts from the message and save them
            extracted_facts_json = await self.ai_service.extract_facts(message)
            try:
                extracted_facts = json.loads(extracted_facts_json)
                if extracted_facts:
                    await self.fact_repo.save_facts(user_id, extracted_facts)
            except json.JSONDecodeError:
                logging.error(f"Failed to parse facts JSON: {extracted_facts_json}")

            # 3. Gather all context for the prompt
            persona_facts = await self.persona_repo.get_persona_facts()
            user_facts = await self.fact_repo.get_user_facts_dict(user_id)
            recent_messages = await self.message_repo.get_recent_messages(user_id, 5)
            relevant_summaries = await self.summary_repo.get_relevant_summaries(user_id, message, 3)
            
            # 4. Handle goal-oriented logic
            # This part can be further simplified, but for now, we adapt the existing logic
            goal_text, goals_for_prompt = await self._get_goal_context(user_id)

            # 5. Build the prompt
            system_prompt = build_lisa_prompt(
                goal_text=goal_text,
                persona_facts=persona_facts,
                user_facts=user_facts,
                recent_messages=recent_messages,
                relevant_summaries=relevant_summaries,
                pending_goals=goals_for_prompt
            )

            # 6. Generate AI response
            ai_response = await self.ai_service.generate_response(system_prompt, message)

            # 7. Save bot response
            await self.message_repo.save_message(user_id, ai_response, is_user=False)

            # 8. Post-response processing (like goal completion)
            # This can be added back if needed, for now focusing on the main flow

            return ai_response

        except Exception as e:
            logging.error(f"ConversationManager failed: {e}", exc_info=True)
            return "I'm feeling a bit overwhelmed right now. Let's talk later."

    async def _get_goal_context(self, user_id: int) -> tuple[str, list]:
        """Determine the current goal and which goals to include in the prompt."""
        # A simplified version of the original complex goal logic
        day_stage = await self.user_repo.get_user_day_stage(user_id)
        day_goals = await self.goal_repo.get_master_goals_for_day(day_stage)
        pending_goals = await self.goal_repo.get_pending_user_goals(user_id)

        # Default goal is the first for the day
        goal_text = day_goals[0]['goal_text'] if day_goals else "General conversation."
        goals_for_prompt = []

        conversation_state = await self.user_repo.get_conversation_state(user_id)
        messages_since_last = conversation_state.get('messages_since_last_goal', 0)

        if pending_goals and messages_since_last >= 5:
            mood_result, mood_confidence = await self.ai_service.analyze_conversation_mood(await self.message_repo.get_recent_messages(user_id, 5))
            if mood_result == "ASK" and mood_confidence >= 0.7:
                # It's a good time to ask a question
                askable_goal = pending_goals[0]
                goal_text = askable_goal['master_goals']['goal_text']
                goals_for_prompt = pending_goals
                await self.user_repo.reset_goal_counters(user_id)
                logging.info(f"AI decided to ask goal: {goal_text}")
            else:
                # Not a good time, reset counter
                await self.user_repo.increment_skip_counter(user_id)
                logging.info("AI decided to skip asking a goal.")
        
        return goal_text, goals_for_prompt

    async def _trigger_batch_summary(self, user_id: int):
        """
        Summarizes messages in full batches of 20 and deletes only the summarized messages.
        Triggered when message count > 25.
        """
        try:
            all_messages = await self.message_repo.get_all_messages(user_id)
            num_messages = len(all_messages)

            if num_messages < 20:
                return

            # Calculate how many messages are in full batches
            num_messages_to_process = (num_messages // 20) * 20
            
            # Get the actual messages to be processed
            messages_to_process = all_messages[:num_messages_to_process]

            logging.info(f"User {user_id} has {num_messages} messages. Processing {len(messages_to_process)} messages in batches.")

            # Loop through the messages_to_process in batches of 20 and create summaries
            for i in range(0, len(messages_to_process), 20):
                batch = messages_to_process[i:i+20]
                if not batch:
                    continue
                
                conversation_text = "\n".join([f"{m['role']}: {m['text']}" for m in batch])
                summary_text = await self.ai_service.generate_rolling_summary(conversation_text)
                
                if summary_text:
                    await self.summary_repo.save_summary(user_id, summary_text)

            # Delete only the messages that were processed
            if messages_to_process:
                await self.message_repo.delete_messages_batch(user_id, messages_to_process)
                logging.info(f"Batch summary complete for user {user_id}. Deleted {len(messages_to_process)} messages.")

        except Exception as e:
            logging.error(f"Error during async batch summary for user {user_id}: {e}", exc_info=True)
