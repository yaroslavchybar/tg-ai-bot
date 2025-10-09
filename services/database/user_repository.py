"""
Repository for all interactions with the `users` table in Supabase.
"""

import logging
from typing import Dict
from datetime import datetime, timedelta

class UserRepository:
    def __init__(self, supabase_client):
        self.client = supabase_client

    async def save_user(self, user_id: int, username: str = None) -> bool:
        """Save or update user information."""
        try:
            existing_result = self.client.table('users').select('username').eq('user_id', user_id).execute()
            existing_user = existing_result.data[0] if existing_result.data else None

            data = {'user_id': user_id}
            if username is not None:
                data['username'] = username
            elif existing_user:
                data['username'] = existing_user.get('username')

            data['first_seen'] = datetime.utcnow().isoformat()
            self.client.table('users').upsert(data, on_conflict='user_id').execute()
            logging.info(f"User saved/updated: {user_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to save user: {e}")
            return False

    async def get_user_day_stage(self, user_id: int) -> int:
        """Get user's current day stage."""
        try:
            result = self.client.table('users').select('day_stage').eq('user_id', user_id).execute()
            return result.data[0]['day_stage'] if result.data else 1
        except Exception as e:
            logging.error(f"Failed to get user day stage: {e}")
            return 1

    async def update_user_last_interaction(self, user_id: int) -> bool:
        """Update user's last interaction timestamp."""
        try:
            data = {'last_interaction': datetime.utcnow().isoformat()}
            self.client.table('users').update(data).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            logging.error(f"Failed to update last interaction: {e}")
            return False

    async def increment_conversation_counters(self, user_id: int) -> None:
        """Increment conversation counters for user messages."""
        try:
            result = self.client.table('users').select('messages_since_last_goal').eq('user_id', user_id).execute()
            current_count = result.data[0]['messages_since_last_goal'] if result.data else 0
            self.client.table('users').update({'messages_since_last_goal': current_count + 1}).eq('user_id', user_id).execute()
            logging.debug(f"Incremented conversation counters for user {user_id}")
        except Exception as e:
            logging.error(f"Failed to increment conversation counters for user {user_id}: {e}")

    async def reset_goal_counters(self, user_id: int) -> None:
        """Reset goal-related counters when a goal is asked or on exit."""
        try:
            self.client.table('users').update({
                'messages_since_last_goal': 0,
                'consecutive_skips': 0,
                'last_goal_asked_at': datetime.utcnow().isoformat()
            }).eq('user_id', user_id).execute()
            logging.info(f"Reset goal counters for user {user_id}")
        except Exception as e:
            logging.error(f"Failed to reset goal counters for user {user_id}: {e}")

    async def reset_messages_since_last_goal_only(self, user_id: int) -> None:
        """Reset only messages_since_last_goal counter."""
        try:
            self.client.table('users').update({'messages_since_last_goal': 0}).eq('user_id', user_id).execute()
            logging.debug(f"Reset messages_since_last_goal for user {user_id}")
        except Exception as e:
            logging.error(f"Failed to reset messages_since_last_goal for user {user_id}: {e}")

    async def increment_skip_counter(self, user_id: int) -> None:
        """Increment consecutive skips counter."""
        try:
            result = self.client.table('users').select('consecutive_skips').eq('user_id', user_id).execute()
            current_skips = result.data[0]['consecutive_skips'] if result.data else 0
            self.client.table('users').update({
                'consecutive_skips': current_skips + 1,
                'messages_since_last_goal': 0
            }).eq('user_id', user_id).execute()
            logging.debug(f"Incremented skip counter for user {user_id}")
        except Exception as e:
            logging.error(f"Failed to increment skip counter for user {user_id}: {e}")

    async def get_conversation_state(self, user_id: int) -> Dict:
        """Get current conversation state for a user."""
        try:
            result = self.client.table('users').select(
                'messages_since_last_goal', 'consecutive_skips', 'last_goal_asked_at', 'message_count', 'stage'
            ).eq('user_id', user_id).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logging.error(f"Failed to get conversation state for user {user_id}: {e}")
            return {}

    async def get_message_count(self, user_id: int) -> int:
        """Get current message count for user."""
        try:
            result = self.client.table('users').select('message_count').eq('user_id', user_id).execute()
            return result.data[0]['message_count'] if result.data else 0
        except Exception as e:
            logging.error(f"Failed to get message count for user {user_id}: {e}")
            return 0

    async def update_message_count(self, user_id: int, count: int) -> None:
        """Update message count for user."""
        try:
            self.client.table('users').update({'message_count': count}).eq('user_id', user_id).execute()
        except Exception as e:
            logging.error(f"Failed to update message count for user {user_id}: {e}")

    async def advance_user_day_stage(self, user_id: int) -> bool:
        """Advance user to next day stage."""
        try:
            current_day = await self.get_user_day_stage(user_id)
            new_day = current_day + 1
            data = {'day_stage': new_day}
            result = self.client.table('users').update(data).eq('user_id', user_id).execute()
            if result.data:
                logging.info(f"Advanced user {user_id} to day stage {new_day}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to advance user {user_id} to next day: {e}")
            return False

    async def get_user_stage(self, user_id: int) -> str:
        """Get user's current stage (morning/evening/none)."""
        try:
            result = self.client.table('users').select('stage').eq('user_id', user_id).execute()
            return result.data[0]['stage'] if result.data else 'none'
        except Exception as e:
            logging.error(f"Failed to get user stage: {e}")
            return 'none'

    async def set_user_stage(self, user_id: int, stage: str) -> bool:
        """Set user's stage (morning/evening/none)."""
        try:
            if stage not in ['morning', 'evening', 'none']:
                logging.error(f"Invalid stage value: {stage}")
                return False

            data = {'stage': stage}
            result = self.client.table('users').update(data).eq('user_id', user_id).execute()
            if result.data:
                logging.info(f"Set user {user_id} stage to {stage}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to set user stage: {e}")
            return False

    async def set_user_stage_morning(self, user_id: int) -> bool:
        """Set user's stage to morning."""
        return await self.set_user_stage(user_id, 'morning')

    async def set_user_stage_evening(self, user_id: int) -> bool:
        """Set user's stage to evening."""
        return await self.set_user_stage(user_id, 'evening')

    async def reset_user_stage(self, user_id: int) -> bool:
        """Reset user's stage to none."""
        return await self.set_user_stage(user_id, 'none')

    async def get_active_users(self) -> list:
        """Get all users who have interacted in the last 24 hours."""
        try:
            yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
            result = self.client.table('users').select('user_id').gte('last_interaction', yesterday).execute()
            return result.data or []
        except Exception as e:
            logging.error(f"Failed to get active users: {e}")
            return []
