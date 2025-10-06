"""
Service for all interactions with the OpenAI API.
"""

import logging
import json
from openai import OpenAI
from config import OPENAI_API_KEY
from logic.prompt_builder import (
    VALIDATION_PROMPT_TEMPLATE,
    MOOD_ANALYSIS_PROMPT_TEMPLATE,
    FACT_UPDATE_PROMPT,
    ROLLING_SUMMARY_PROMPT,
    DAILY_RECAP_PROMPT
)

class AIService:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in config")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        logging.info("AI Service initialized successfully")

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a given text."""
        try:
            response = self.client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            logging.error(f"Failed to generate embedding: {e}")
            return None

    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a chat completion response from the AI."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=120
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI response generation failed: {e}")
            return "Sorry, I'm having trouble thinking right now."

    async def analyze_fact_changes(self, user_message: str, existing_facts: dict) -> str:
        """
        Analyzes the user message in the context of existing facts to determine
        if any facts should be added, updated, or deleted.
        """
        try:
            system_prompt = FACT_UPDATE_PROMPT
            
            # Format the user prompt with the existing facts and the new message
            facts_for_prompt = [{ "fact_type": f, "value": v} for f, v in existing_facts.items()]
            facts_json_str = json.dumps(facts_for_prompt, indent=2, ensure_ascii=False)
            user_prompt = f"Existing Facts: {facts_json_str}\n\nUser's Message: \"{user_message}\""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2, # Lower temperature for more deterministic JSON output
            )

            ai_response = response.choices[0].message.content
            return ai_response.strip()
        except Exception as e:
            logging.error(f"Failed to analyze fact changes with AI: {e}")
            # Return an empty JSON array on error
            return "[]"

    async def validate_goal_completion(self, user_message: str, fact_type: str, goal_variants: list = None, conversation_history: list = None) -> tuple[bool, str]:
        """Use GPT to validate if user response answers the goal with confidence scoring"""
        history_context = "\n".join([
            f"{'User' if msg.get('role') == 'user' else 'Lisa'}: {msg.get('text', '')}"
            for msg in conversation_history[-5:]
        ])
        variants_context = ""
        if goal_variants:
            variants_context = f"Goal variants (any of these could be relevant):\n{chr(10).join(f'- {variant}' for variant in goal_variants[:3])}"

        prompt = VALIDATION_PROMPT_TEMPLATE.format(
            fact_type=fact_type,
            variants_context=variants_context,
            history_context=history_context,
            user_message=user_message
        )

        try:
            response = self.client.responses.create(
                model="gpt-5-nano",
                input=[
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}]
                    }
                ],
                max_output_tokens=20,
                reasoning={"effort": "minimal"},
            )
            result = getattr(response, "output_text", None) or response.output[0].content[0].text
            result = result.strip()
            answer = result.strip().upper()

            if answer in ['YES', 'MAYBE', 'NO']:
                return answer == "YES", answer
            else:
                return False, "NO"
        except (ValueError, IndexError, AttributeError) as e:
            logging.error(f"Failed to parse goal validation response: {e}")
            return False, "NO"

    async def analyze_conversation_mood(self, conversation_history: list) -> tuple[str, float]:
        """Use AI to analyze if it's a good time to ask a personal question."""
        system_prompt = MOOD_ANALYSIS_PROMPT_TEMPLATE
        user_prompt = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('text', '')}" for msg in conversation_history[-5:]])

        try:
            response = self.client.responses.create(
                model="gpt-5-nano",
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}]
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_prompt}]
                    }
                ],
                max_output_tokens=32,
                reasoning={"effort": "minimal"},
            )
            result = getattr(response, "output_text", None) or response.output[0].content[0].text
            result = result.strip().upper()
            confidence = 0.8 if result in ["ASK", "SKIP"] else 0.3
            return result, confidence
        except Exception as e:
            logging.error(f"Failed to analyze conversation mood: {e}")
            return "SKIP", 0.0

    async def generate_rolling_summary(self, conversation_text: str) -> str:
        """Generates a rolling summary for a conversation."""
        try:
            system_prompt = ROLLING_SUMMARY_PROMPT
            user_prompt = f"Please summarize this conversation:\n\n{conversation_text}"

            response = self.client.responses.create(
                model="gpt-5-nano",
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}]
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_prompt}]
                    }
                ],
                max_output_tokens=150,
                reasoning={"effort": "minimal"},
            )

            summary_text = getattr(response, "output_text", None) or response.output[0].content[0].text
            return summary_text.strip()
        except Exception as e:
            logging.error(f"Failed to generate rolling summary: {e}")
            return None

    async def generate_daily_recap(self, summaries_context: str) -> str:
        """Generates a daily recap from a context of summaries."""
        system_prompt = DAILY_RECAP_PROMPT
        user_prompt = f"""Consolidate these conversation summaries into one comprehensive daily recap:\n\n{summaries_context}\n\nPlease provide a cohesive daily summary:"""
        try:
            response = self.client.responses.create(
                model="gpt-5-nano",
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}]
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_prompt}]
                    }
                ],
                max_output_tokens=400,
                reasoning={"effort": "minimal"},
            )
            summary_text = getattr(response, "output_text", None) or response.output[0].content[0].text
            return summary_text.strip()
        except Exception as e:
            logging.error(f"Failed to create daily summary from summaries: {e}")
            return None
