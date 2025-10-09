"""
Main Telegram event handler.
Initializes all services and repositories and handles incoming messages.
"""

import logging
import asyncio
from telethon import events
from supabase import create_client, Client

from config import telegram_client, SUPABASE_URL, SUPABASE_KEY
from logic.conversation_manager import ConversationManager
from services.ai_service import AIService
from services.response_service import ResponseService
from services.database.user_repository import UserRepository
from services.database.message_repository import MessageRepository
from services.database.fact_repository import FactRepository
from services.database.goal_repository import GoalRepository
from services.database.persona_repository import PersonaRepository
from services.database.summary_repository import SummaryRepository
from services.database.script_repository import ScriptRepository

# --- INITIALIZE SERVICES ---

# Initialize Supabase client
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize services and repositories
ai_service = AIService()
response_service = ResponseService()
user_repo = UserRepository(supabase_client)
message_repo = MessageRepository(supabase_client, ai_service)
fact_repo = FactRepository(supabase_client, ai_service)
goal_repo = GoalRepository(supabase_client)
persona_repo = PersonaRepository(supabase_client)
summary_repo = SummaryRepository(supabase_client, ai_service)
script_repo = ScriptRepository(supabase_client)

# Initialize the main conversation manager
conversation_manager = ConversationManager(
    ai_service=ai_service,
    response_service=response_service,
    user_repo=user_repo,
    message_repo=message_repo,
    fact_repo=fact_repo,
    goal_repo=goal_repo,
    persona_repo=persona_repo,
    summary_repo=summary_repo,
    script_repo=script_repo
)

logging.info("Bot components initialized successfully.")

# --- TELEGRAM EVENT HANDLER ---

@telegram_client.on(events.NewMessage(incoming=True))
async def handle_message(event):
    """Message handler that sends user message to the ConversationManager."""
    if not event.is_private:
        return

    sender = await event.get_sender()
    if sender.bot:
        return

    user_id = sender.id
    message_text = event.message.text

    # Get AI response
    ai_response = await conversation_manager.get_response(message_text, user_id)

    # If no response (script completed), don't send anything
    if ai_response is None:
        logging.info(f"Processed message from {user_id}: '{message_text[:50]}...' -> No response (script completed)")
        return

    logging.info(f"Processed message from {user_id}: '{message_text[:50]}...' -> AI response generated")

    # Handle both single messages and split messages (when "$" symbol is used)
    if isinstance(ai_response, list):
        for i, part in enumerate(ai_response):
            await telegram_client.send_message(user_id, part)
            if i < len(ai_response) - 1:  # Don't delay after last message
                await asyncio.sleep(1.5)  # Natural pause between messages
    else:
        await telegram_client.send_message(user_id, ai_response)