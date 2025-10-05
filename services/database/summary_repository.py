"""
Repository for all interactions with the `summaries` table in Supabase.
"""

import logging
from typing import List, Dict
from datetime import datetime
import numpy as np

class SummaryRepository:
    def __init__(self, supabase_client, ai_service):
        self.client = supabase_client
        self.ai_service = ai_service # For embeddings

    async def save_summary(self, user_id: int, summary_text: str, is_daily_recap: bool = False) -> bool:
        """Save a summary to the database."""
        try:
            text_to_embed = f"[DAILY RECAP] {summary_text}" if is_daily_recap else summary_text
            embedding = await self.ai_service.generate_embedding(text_to_embed)
            
            data = {
                'user_id': user_id,
                'summary_text': text_to_embed,
                'embedding': embedding,
                'created_at': datetime.utcnow().isoformat()
            }
            self.client.table('summaries').insert(data).execute()
            logging.info(f"Summary saved for user {user_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to save summary for user {user_id}: {e}")
            return False

    async def get_relevant_summaries(self, user_id: int, current_message: str, limit: int = 3) -> List[Dict]:
        """Get top relevant summaries using semantic search."""
        try:
            current_embedding = await self.ai_service.generate_embedding(current_message)
            if not current_embedding:
                return []

            result = self.client.table('summaries') \
                .select('id, summary_text, embedding, created_at') \
                .eq('user_id', user_id) \
                .not_.is_('embedding', None) \
                .order('created_at', desc=True) \
                .limit(10) \
                .execute() # Limit to last 10 for performance

            summaries = result.data or []
            if not summaries:
                return []

            for summary in summaries:
                summary['similarity'] = self._cosine_similarity(current_embedding, summary.get('embedding', []))

            summaries.sort(key=lambda x: x['similarity'], reverse=True)
            return summaries[:limit]
        except Exception as e:
            logging.error(f"Failed to get relevant summaries for user {user_id}: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0

    async def get_daily_summaries_for_recap(self, user_id: int) -> List[Dict]:
        """Get all summaries from today (excluding daily recaps)."""
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            result = self.client.table('summaries') \
                .select('*') \
                .eq('user_id', user_id) \
                .gte('created_at', today_start) \
                .not_.like('summary_text', '[DAILY RECAP]%') \
                .execute()
            return result.data or []
        except Exception as e:
            logging.error(f"Failed to get summaries for daily recap for user {user_id}: {e}")
            return []

    async def delete_summaries_batch(self, user_id: int, summaries_to_delete: List[Dict]) -> bool:
        """Delete a batch of summaries by their IDs."""
        if not summaries_to_delete:
            return False
        try:
            summary_ids = [summary.get('id') for summary in summaries_to_delete if summary.get('id')]
            if not summary_ids:
                return False
            self.client.table('summaries').delete().in_('id', summary_ids).execute()
            logging.info(f"Deleted {len(summary_ids)} individual summaries for user {user_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to delete summaries batch for user {user_id}: {e}")
            return False
