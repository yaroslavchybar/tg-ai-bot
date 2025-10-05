# Telegram Bot AI (Chloe/Lisa)

A sophisticated, AI-powered Telegram bot built with Python. It uses Telethon for Telegram integration, OpenAI for intelligent responses, and Supabase for a complex, multi-layer memory system.

## Features

- 🤖 **Conversational AI**: Engages users with a consistent persona named "Lisa" using OpenAI's GPT models.
- 🧠 **Advanced Memory System**: Features a 7-layer memory architecture for storing short-term, long-term, and semantic information about users and conversations.
- 📈 **Goal-Oriented Dialogue**: Follows a 7-day relationship progression plan, intelligently deciding when to ask questions to build rapport.
- ⚙️ **Automated Maintenance**: Includes a scheduler for automated tasks like generating daily conversation summaries and cleaning up old data.
- VECTOR-SEARCH **Semantic Search**: Utilizes vector embeddings to find relevant memories and facts, leading to highly context-aware responses.

## Architecture

The bot is designed with a clean, service-oriented architecture that separates concerns into three main layers: **Logic**, **Services**, and **Database Repositories**.

- **Logic Layer (`logic/`)**: Contains the core business logic. It orchestrates calls to various services to manage the conversation flow and generate responses.
- **Services Layer (`services/`)**: Provides specialized, independent services for AI interaction (OpenAI) and scheduled maintenance tasks.
- **Database Layer (`services/database/`)**: Contains repository classes, where each class is responsible for all database interactions for a single table (e.g., `UserRepository`, `MessageRepository`).

This separation of concerns makes the codebase modular, easier to maintain, and highly testable.

## Project Structure

```
tgbotai/
├── bot.py
├── config.py
├── constants.py
├── main.py
├── requirements.txt
├── scheduler.py
│
├── logic/
│   ├── conversation_manager.py
│   └── prompt_builder.py
│
└── services/
    ├── ai_service.py
    ├── maintenance_service.py
    └── database/
        ├── user_repository.py
        ├── message_repository.py
        └── ... (repositories for each table)
```

- `main.py`: The main entry point that initializes and starts the bot and scheduler.
- `bot.py`: Initializes all services and repositories, and handles incoming Telegram events.
- `config.py`: Manages configuration and environment variables.
- `constants.py`: Stores global constants like master goals and regex patterns.
- `scheduler.py`: Configures and runs scheduled maintenance tasks.
- `logic/conversation_manager.py`: The central orchestrator that manages conversation flow.
- `logic/prompt_builder.py`: Centralized module for building all AI prompt templates.
- `services/ai_service.py`: The single point of contact for all OpenAI API calls.
- `services/maintenance_service.py`: Encapsulates logic for scheduled tasks.
- `services/database/`: Contains all database repository classes, each mapped to a table.

## Setup

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Environment Variables:**
    Create a `.env` file and populate it with your API keys for Telegram, OpenAI, and Supabase.
3.  **Database Schema:**
    Run the necessary SQL scripts in your Supabase project to set up the tables.
4.  **Start the bot:**
    ```bash
    python main.py
    ```

## The Memory System: A Deep Dive

This implementation features a sophisticated **7-table enhanced memory system** that creates genuinely intelligent conversations with relationship progression, personality consistency, and semantic memory search.

### Memory Architecture Overview

- **Layer 1: Short-Term Memory (Recent Conversations)**: Maintains immediate conversation context using the last few messages.
- **Layer 2: Long-Term Memory (User Profile & Facts)**: Stores structured facts about the user (name, age, interests) to personalize responses.
- **Layer 3: Semantic Memory (Vector Search)**: Uses vector embeddings on messages and facts to find relevant past information based on meaning, not just keywords.
- **Layer 4: Personality System (Lisa's Character)**: Ensures a consistent AI personality by storing and retrieving Lisa's traits and background.
- **Layer 5: Mid-Term Memory (Rolling Summaries)**: Automatically summarizes conversations every 20 messages to capture key details efficiently.
- **Layer 6: Long-Term Memory (Daily Consolidation)**: Creates consolidated daily recaps from the rolling summaries for long-term tracking.
- **Layer 7: Relationship Progression (Day-Based Goals)**: Guides the conversation towards relationship-building objectives defined in a 7-day funnel.

### Enhanced Database Schema

The system uses 7 specialized tables for comprehensive memory management:

- **`users`**: Manages user data, including their current `day_stage` in the relationship funnel.
- **`messages`**: Stores all conversation history with vector embeddings for semantic search.
- **`facts`**: Contains structured, extractable information about the user.
- **`persona`**: Holds the personality traits and background for the bot persona.
- **`summaries`**: Stores rolling and daily consolidated summaries of conversations.
- **`goals`**: Defines the objectives for each day of the relationship progression.

(For detailed `CREATE TABLE` statements, please refer to the project's `.sql` schema files).

### Key Technical Features

- **AI-Powered Fact Extraction**: Uses an AI model to analyze user messages and automatically extract personal information into a structured format.
- **Vector Embeddings & Semantic Search**: Leverages OpenAI's `text-embedding-ada-002` model to create 1536-dimension embeddings for all messages, facts, and summaries, enabling powerful semantic search.
- **Automated Maintenance**: An `APScheduler` job runs daily to automatically generate rolling summaries, consolidate them into daily recaps, and clean up old data, ensuring the system is self-managing.

## Documentation Reference

- [Telethon Documentation](https://docs.telethon.dev/en/stable/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Supabase Documentation](https://supabase.com/docs)
