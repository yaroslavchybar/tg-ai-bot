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

    async def execute_fact_actions(self, user_id: int, actions: list):
        """
        Executes a list of fact actions (ADD, UPDATE, DELETE) from the AI.
        """
        if not actions:
            return

        for action in actions:
            action_type = action.get("action")
            fact_type = action.get("fact_type")
            
            try:
                if action_type == "ADD":
                    value = action.get("value")
                    if not value:
                        continue

                    # Handle indexed fact types
                    if fact_type in ["interest", "hobbies"]:
                        next_index = await self._get_next_indexed_fact_index(user_id, fact_type)
                        fact_type = f"{fact_type}_{next_index}"
                    
                    embedding = await self.ai_service.generate_embedding(f"{fact_type}: {value}")
                    self.client.table('facts').insert({
                        'user_id': user_id,
                        'fact_type': fact_type,
                        'value': value,
                        'embedding': embedding
                    }).execute()
                    logging.info(f"AI Action: ADDED fact '{fact_type}' for user {user_id}")

                elif action_type == "UPDATE":
                    new_value = action.get("new_value")
                    if not new_value or not fact_type:
                        continue
                    
                    embedding = await self.ai_service.generate_embedding(f"{fact_type}: {new_value}")
                    self.client.table('facts').update({
                        'value': new_value,
                        'embedding': embedding
                    }).eq('user_id', user_id).eq('fact_type', fact_type).execute()
                    logging.info(f"AI Action: UPDATED fact '{fact_type}' for user {user_id}")

                elif action_type == "DELETE":
                    if not fact_type:
                        continue
                    
                    self.client.table('facts').delete().eq('user_id', user_id).eq('fact_type', fact_type).execute()
                    logging.info(f"AI Action: DELETED fact '{fact_type}' for user {user_id}")

            except Exception as e:
                logging.error(f"Failed to execute action {action} for user {user_id}: {e}")

    async def _get_next_indexed_fact_index(self, user_id: int, fact_base_type: str) -> int:
        """
        Calculates the next available index for a new indexed fact (e.g., interest, hobbies).
        """
        try:
            result = self.client.table('facts').select('fact_type').eq('user_id', user_id).like('fact_type', f'{fact_base_type}_%').execute()
            if not result.data:
                return 0
            
            max_index = -1
            for fact in result.data:
                try:
                    index = int(fact['fact_type'].split('_')[-1])
                    if index > max_index:
                        max_index = index
                except (ValueError, IndexError):
                    continue
            return max_index + 1
        except Exception as e:
            logging.error(f"Failed to get next index for {fact_base_type} for user {user_id}: {e}")
            return 0 # Fallback to 0

    async def clear_user_facts(self, user_id: int) -> bool:
        """Clear all facts for a user."""
        try:
            self.client.table('user_facts').delete().eq('user_id', user_id).execute()
            logging.info(f"Cleared all facts for user {user_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to clear user facts: {e}")
            return False
