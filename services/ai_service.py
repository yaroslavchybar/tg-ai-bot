"""
Service for all interactions with the OpenAI API.
"""

import logging
import json
from openai import OpenAI
from config import OPENAI_API_KEY
from logic.prompt_builder import (
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


    async def analyze_fact_changes(self, user_message: str, existing_facts: dict) -> str:
        """
        Analyzes the user message in the context of existing facts to determine
        if any facts should be added, updated, or deleted.
        """
        try:
            facts_for_prompt = [{ "fact_type": f, "value": v} for f, v in existing_facts.items()]
            facts_json_str = json.dumps(facts_for_prompt, indent=2, ensure_ascii=False)
            user_prompt = f"Existing Facts: {facts_json_str}\n\nUser's Message: '{user_message}'"

            response = self.client.responses.create(
                model="gpt-5-nano",
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": FACT_UPDATE_PROMPT}]},
                    {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]}
                ],
                max_output_tokens=256,
                reasoning={"effort": "minimal"}
            )

            result = getattr(response, "output_text", None) or response.output[0].content[0].text
            return result.strip()
        except Exception as e:
            logging.error(f"Failed to analyze fact changes with AI: {e}")
            # Return an empty JSON array on error
            return "[]"



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
