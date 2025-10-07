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

    async def delete_all_facts(self):
        """Deletes all facts from the persona table."""
        try:
            # Supabase requires a filter for delete, so we delete all rows.
            # A bit of a hack, but it works. We are deleting all rows where the created_at is not null.
            # This should be all rows.
            self.client.table('persona').delete().neq('created_at', '1970-01-01T00:00:00').execute()
            logging.info("All persona facts deleted.")
        except Exception as e:
            logging.error(f"Failed to delete persona facts: {e}")

    async def insert_fact(self, text: str, embedding: List[float]):
        """Inserts a new fact into the persona table."""
        try:
            self.client.table('persona').insert({
                'text': text,
                'embedding': embedding
            }).execute()
            logging.info(f"Inserted new fact: {text}")
        except Exception as e:
            logging.error(f"Failed to insert persona fact: {e}")
