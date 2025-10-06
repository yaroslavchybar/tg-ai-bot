"""
Repository for all interactions with the `master_goals` and `user_goals` tables.
"""

import logging
from typing import List, Dict
from datetime import datetime

class GoalRepository:
    def __init__(self, supabase_client):
        self.client = supabase_client

    async def create_master_goal(self, day: int, order_num: int, goal_text: str) -> bool:
        """Create a master goal template"""
        try:
            data = {
                'day': day,
                'order_num': order_num,
                'goal_text': goal_text,
                'created_at': datetime.utcnow().isoformat()
            }
            self.client.table('master_goals').insert(data).execute()
            logging.info(f"Master goal created: Day {day}, Order {order_num} - {goal_text}")
            return True
        except Exception as e:
            logging.error(f"Failed to create master goal: {e}")
            return False

    async def get_master_goals_for_day(self, day: int) -> List[Dict]:
        """Get all master goals for a specific day, ordered by order_num"""
        try:
            result = self.client.table('master_goals').select('*').eq('day', day).order('order_num').execute()
            return result.data or []
        except Exception as e:
            logging.error(f"Failed to get master goals for day {day}: {e}")
            return []

    async def assign_goals_to_user(self, user_id: int, day: int) -> bool:
        """Assign all master goals for a day to a user"""
        try:
            master_goals = await self.get_master_goals_for_day(day)
            if not master_goals:
                logging.warning(f"No master goals found for day {day}")
                return False

            user_goals_data = []
            for master_goal in master_goals:
                user_goals_data.append({
                    'user_id': user_id,
                    'master_goal_id': master_goal['id'],
                    'status': 'pending',
                    'created_at': datetime.utcnow().isoformat()
                })

            if user_goals_data:
                self.client.table('user_goals').insert(user_goals_data).execute()
                logging.info(f"Assigned {len(user_goals_data)} goals for day {day} to user {user_id}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to assign goals to user {user_id}: {e}")
            return False

    async def get_pending_user_goals(self, user_id: int) -> List[Dict]:
        """Get all pending goals for a user"""
        try:
            result = self.client.table('user_goals').select('*, master_goals(*)').eq('user_id', user_id).eq('status', 'pending').order('order_num', foreign_table='master_goals').execute()
            return result.data or []
        except Exception as e:
            logging.error(f"Failed to get pending goals for user {user_id}: {e}")
            return []

    async def complete_user_goal(self, user_goal_id: int) -> bool:
        """Mark a user goal as completed"""
        try:
            data = {
                'status': 'done',
                'completed_at': datetime.utcnow().isoformat()
            }
            result = self.client.table('user_goals').update(data).eq('id', user_goal_id).execute()
            if result.data:
                logging.info(f"Completed user goal {user_goal_id}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to complete user goal {user_goal_id}: {e}")
            return False

    async def skip_user_goal(self, user_goal_id: int) -> bool:
        """Mark a user goal as skipped"""
        try:
            data = {
                'status': 'skipped',
                'completed_at': datetime.utcnow().isoformat()
            }
            result = self.client.table('user_goals').update(data).eq('id', user_goal_id).execute()
            if result.data:
                logging.info(f"Skipped user goal {user_goal_id}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to skip user goal {user_goal_id}: {e}")
            return False

    async def get_completed_goals_count(self, user_id: int, day: int) -> int:
        """Get count of completed goals for a user for a specific day."""
        try:
            # PostgREST does not support count on joined tables directly,
            # so we fetch the IDs of completed goals for the specific day and count them.
            result = self.client.table('user_goals').select('id, master_goals!inner(day)').eq('user_id', user_id).eq('status', 'done').eq('master_goals.day', day).execute()
            return len(result.data)
        except Exception as e:
            logging.error(f"Failed to get completed goals count for user {user_id} for day {day}: {e}")
            return 0

    async def initialize_user_goals(self, user_id: int, user_repo) -> bool:
        """Initialize goals for the user's current day stage"""
        try:
            await user_repo.save_user(user_id)
            current_day = await user_repo.get_user_day_stage(user_id)
            existing_goals_for_day = await self.get_user_goals_for_day(user_id, current_day)

            if existing_goals_for_day:
                return True

            success = await self.assign_goals_to_user(user_id, current_day)
            if success:
                logging.info(f"Initialized day {current_day} goals for user {user_id}")
            return success
        except Exception as e:
            logging.error(f"Failed to initialize goals for user {user_id}: {e}")
            return False

    async def ensure_user_has_current_day_goals(self, user_id: int, user_repo) -> bool:
        """Ensure user has goals for their current day stage"""
        try:
            current_day = await user_repo.get_user_day_stage(user_id)
            pending_goals = await self.get_pending_user_goals(user_id)
            if not pending_goals:
                success = await self.assign_goals_to_user(user_id, current_day)
                if success:
                    logging.info(f"Assigned day {current_day} goals to user {user_id} (no pending goals found)")
                return success
            return True
        except Exception as e:
            logging.error(f"Failed to ensure user has current day goals for user {user_id}: {e}")
            return False

    async def get_user_goals_for_day(self, user_id: int, day: int) -> List[Dict]:
        """Get all user goals for a specific day."""
        try:
            result = self.client.table('user_goals').select('*, master_goals!inner(*)').eq('user_id', user_id).eq('master_goals.day', day).execute()
            return result.data or []
        except Exception as e:
            logging.error(f"Failed to get user goals for day {day} for user {user_id}: {e}")
            return []

    async def are_all_goals_completed_for_day(self, user_id: int, day: int) -> bool:
        """Check if all goals for a given day are completed for a user."""
        user_goals_for_day = await self.get_user_goals_for_day(user_id, day)
        if not user_goals_for_day:
            return False
        return all(goal['status'] == 'done' for goal in user_goals_for_day)