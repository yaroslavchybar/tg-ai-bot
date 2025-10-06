"""
Repository for all interactions with the `messages` table in Supabase.
"""

import logging
from typing import List, Dict
from datetime import datetime

class MessageRepository:
    def __init__(self, supabase_client, ai_service):
        self.client = supabase_client
        self.ai_service = ai_service # For embeddings

    async def save_message(self, user_id: int, content: str, is_user: bool) -> bool:
        """Save a message to short-term memory (conversation flow)."""
        try:
            embedding = await self.ai_service.generate_embedding(content)
            data = {
                'user_id': user_id,
                'role': 'user' if is_user else 'bot',
                'text': content,
                'embedding': embedding,
                'created_at': datetime.utcnow().isoformat()
            }
            self.client.table('messages').insert(data).execute()
            logging.info(f"Message saved for user {user_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to save message: {e}")
            return False

    async def get_recent_messages(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent messages for short-term memory context."""
        try:
            result = self.client.table('messages') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            messages = result.data or []
            messages.reverse() # Return in chronological order
            return messages
        except Exception as e:
            logging.error(f"Failed to get recent messages: {e}")
            return []

    async def get_message_count_for_summary(self, user_id: int) -> int:
        """Get the actual number of messages in the database for this user."""
        try:
            result = self.client.table('messages').select('id', count='exact').eq('user_id', user_id).execute()
            return result.count
        except Exception as e:
            logging.error(f"Failed to get message count for user {user_id}: {e}")
            return 0

    async def delete_messages_batch(self, user_id: int, messages_to_delete: List[Dict]) -> bool:
        """Delete a batch of messages by their IDs."""
        if not messages_to_delete:
            return False
        try:
            message_ids = [msg.get('id') for msg in messages_to_delete if msg.get('id')]
            if not message_ids:
                return False
            
            self.client.table('messages').delete().in_('id', message_ids).execute()
            logging.info(f"Deleted {len(message_ids)} old messages for user {user_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to delete message batch for user {user_id}: {e}")
            return False

    async def get_all_messages(self, user_id: int) -> List[Dict]:
        """Get all messages for a user."""
        try:
            result = self.client.table('messages') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=False) \
                .execute()
            return result.data or []
        except Exception as e:
            logging.error(f"Failed to get all messages: {e}")
            return []

    async def get_messages_for_summary_batch(self, user_id: int, limit: int) -> List[Dict]:
        """Get the oldest messages for batch processing, up to a given limit."""
        try:
            # Fetch the oldest messages (ascending order)
            result = self.client.table('messages') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=False) \
                .limit(limit) \
                .execute()
            return result.data or []
        except Exception as e:
            logging.error(f"Failed to get messages for summary batch for user {user_id}: {e}")
            return []