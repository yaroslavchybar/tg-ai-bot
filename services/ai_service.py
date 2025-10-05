"""
Service for all interactions with the OpenAI API.
"""

import logging
from openai import OpenAI
from config import OPENAI_API_KEY
from logic.prompt_builder import (
    VALIDATION_PROMPT_TEMPLATE,
    MOOD_ANALYSIS_PROMPT_TEMPLATE,
    FACT_EXTRACTION_PROMPT,
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
                model="text-embedding-ada-002"
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

    async def extract_facts(self, message: str) -> str:
        """Extract facts from a user message."""
        try:
            system_prompt = FACT_EXTRACTION_PROMPT
            user_prompt = f"Analyze this message and extract any personal information: '{message}'"

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
                max_output_tokens=200,
                reasoning={"effort": "minimal"},
            )

            ai_response = getattr(response, "output_text", None) or response.output[0].content[0].text
            return ai_response.strip()
        except Exception as e:
            logging.error(f"Failed to extract facts with AI: {e}")
            return "{}"

    async def validate_goal_completion(self, user_message: str, fact_type: str, goal_variants: list = None, conversation_history: list = None) -> tuple[bool, float]:
        """Use GPT to validate if user response answers the goal."""
        history_context = "\n".join([f"User: {msg.get('text', '')}" for msg in conversation_history[-5:] if msg.get('role') == 'user'])
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
            answer, confidence_str = result.split('|', 1)
            confidence = float(confidence_str.strip())
            return answer.strip().upper() == "YES", confidence
        except (ValueError, IndexError, AttributeError) as e:
            logging.error(f"Failed to parse goal validation response: {e}")
            return False, 0.3

    async def analyze_conversation_mood(self, conversation_history: list) -> tuple[str, float]:
        """Use AI to analyze if it's a good time to ask a personal question."""
        conversation = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('text', '')}" for msg in conversation_history[-5:]])
        prompt = MOOD_ANALYSIS_PROMPT_TEMPLATE.format(conversation=conversation)

        try:
            response = self.client.responses.create(
                model="gpt-5-nano",
                input=[
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}]
                    }
                ],
                max_output_tokens=16,
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
