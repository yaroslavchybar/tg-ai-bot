"""
Repository for all interactions with the `facts` table in Supabase.
"""

import logging
from typing import Dict, List
from datetime import datetime

class FactRepository:
    def __init__(self, supabase_client, ai_service):
        self.client = supabase_client
        self.ai_service = ai_service # For embeddings

    async def get_user_facts_dict(self, user_id: int) -> Dict[str, str]:
        """Get user facts as a dictionary."""
        try:
            result = self.client.table('facts').select('fact_type, value').eq('user_id', user_id).execute()
            return {fact['fact_type']: fact['value'] for fact in result.data} if result.data else {}
        except Exception as e:
            logging.error(f"Failed to get user facts: {e}")
            return {}

    async def save_facts(self, user_id: int, facts_data: dict):
        """Saves multiple extracted facts to the database."""
        if not facts_data:
            return

        facts_to_save = []
        # Get existing interests to handle indexing
        existing_facts = await self.get_user_facts_dict(user_id)
        interest_indices = [int(k.split('_')[1]) for k in existing_facts if k.startswith('interest_')]
        next_interest_index = max(interest_indices) + 1 if interest_indices else 0

        # Process single value facts
        for fact_type in ['name', 'age', 'location']:
            if facts_data.get(fact_type):
                facts_to_save.append({'fact_type': fact_type, 'value': facts_data[fact_type]})

        # Process interests
        for interest in facts_data.get('interests', []):
            facts_to_save.append({'fact_type': f'interest_{next_interest_index}', 'value': interest})
            next_interest_index += 1

        # Process other facts
        for key, value in facts_data.get('other_facts', {}).items():
            facts_to_save.append({'fact_type': key, 'value': value})

        # Batch save all facts
        for fact in facts_to_save:
            embedding = await self.ai_service.generate_embedding(f"{fact['fact_type']}: {fact['value']}")
            data = {
                'user_id': user_id,
                'fact_type': fact['fact_type'],
                'value': fact['value'],
                'asked': False,
                'answered': True,
                'embedding': embedding
            }
            try:
                self.client.table('facts').upsert(data, on_conflict='user_id,fact_type').execute()
                logging.info(f"Saved fact for user {user_id}: {fact['fact_type']}")
            except Exception as e:
                logging.error(f"Failed to save fact {fact['fact_type']} for user {user_id}: {e}")

    async def clear_user_facts(self, user_id: int) -> bool:
        """Clear all facts for a user."""
        try:
            self.client.table('user_facts').delete().eq('user_id', user_id).execute()
            logging.info(f"Cleared all facts for user {user_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to clear user facts: {e}")
            return False
