"""
Service for generating chat responses from the AI.
Separated from the main AI service for better organization.
"""

import logging
from openai import OpenAI
from config import OPENAI_API_KEY

class ResponseService:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in config")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        logging.info("Response Service initialized successfully")

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
