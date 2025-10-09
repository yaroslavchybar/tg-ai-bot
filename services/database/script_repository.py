"""
Repository for all interactions with the `scripts` table.
"""

import logging
from typing import List, Dict, Optional

class ScriptRepository:
    def __init__(self, supabase_client):
        self.client = supabase_client

    async def create_script(self, day: int, stage: str, script_text: str) -> bool:
        """Create a new script for a specific day and stage"""
        try:
            data = {
                'day': day,
                'stage': stage,
                'script_text': script_text
            }
            self.client.table('scripts').insert(data).execute()
            logging.info(f"Script created: Day {day}, Stage {stage}")
            return True
        except Exception as e:
            logging.error(f"Failed to create script: {e}")
            return False

    async def get_script(self, day: int, stage: str) -> Optional[str]:
        """Get script text for a specific day and stage"""
        try:
            result = self.client.table('scripts').select('script_text').eq('day', day).eq('stage', stage).execute()
            if result.data:
                return result.data[0]['script_text']
            return None
        except Exception as e:
            logging.error(f"Failed to get script for day {day}, stage {stage}: {e}")
            return None

    async def get_scripts_for_day(self, day: int) -> Dict[str, str]:
        """Get all scripts for a specific day (morning, evening, none)"""
        try:
            result = self.client.table('scripts').select('stage, script_text').eq('day', day).execute()
            scripts = {}
            for script in result.data:
                scripts[script['stage']] = script['script_text']
            return scripts
        except Exception as e:
            logging.error(f"Failed to get scripts for day {day}: {e}")
            return {}

    async def update_script(self, day: int, stage: str, script_text: str) -> bool:
        """Update script for a specific day and stage"""
        try:
            data = {'script_text': script_text}
            result = self.client.table('scripts').update(data).eq('day', day).eq('stage', stage).execute()
            if result.data:
                logging.info(f"Script updated: Day {day}, Stage {stage}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to update script: {e}")
            return False

    async def delete_script(self, day: int, stage: str) -> bool:
        """Delete script for a specific day and stage"""
        try:
            result = self.client.table('scripts').delete().eq('day', day).eq('stage', stage).execute()
            if result.data:
                logging.info(f"Script deleted: Day {day}, Stage {stage}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to delete script: {e}")
            return False

    async def get_available_days(self) -> List[int]:
        """Get all days that have scripts"""
        try:
            result = self.client.table('scripts').select('day').execute()
            days = list(set([script['day'] for script in result.data]))
            days.sort()
            return days
        except Exception as e:
            logging.error(f"Failed to get available days: {e}")
            return []

    async def get_available_stages_for_day(self, day: int) -> List[str]:
        """Get all stages available for a specific day"""
        try:
            result = self.client.table('scripts').select('stage').eq('day', day).execute()
            stages = list(set([script['stage'] for script in result.data]))
            return stages
        except Exception as e:
            logging.error(f"Failed to get available stages for day {day}: {e}")
            return []
