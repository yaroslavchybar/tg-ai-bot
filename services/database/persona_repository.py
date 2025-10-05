"""
Repository for all interactions with the `persona` table in Supabase.
"""

import logging
from typing import List

class PersonaRepository:
    def __init__(self, supabase_client):
        self.client = supabase_client

    async def get_persona_facts(self) -> List[str]:
        """Get Lisa's persona facts."""
        try:
            result = self.client.table('persona').select('text').execute()
            return [fact['text'] for fact in result.data] if result.data else []
        except Exception as e:
            logging.error(f"Failed to get persona facts: {e}")
            return []
