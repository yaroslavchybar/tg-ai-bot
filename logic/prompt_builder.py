"""
Centralized module for building and managing all AI prompt templates.
"""
import datetime
from zoneinfo import ZoneInfo

# ================== CONVERSATION MANAGER PROMPTS ==================

VALIDATION_PROMPT_TEMPLATE = """We're trying to capture the user's {fact_type} information.

{variants_context}

Recent conversation:
{history_context}

Current user response: "{user_message}"

Does this response contain valid information about {fact_type}?

Respond with only one word:
- YES if the response clearly contains {fact_type} information
- MAYBE if it's possibly related but unclear
- NO if it's completely unrelated

Response (YES, MAYBE, or NO):
"""

MOOD_ANALYSIS_PROMPT_TEMPLATE = """Analyze if this is a good time to ask a personal or profile question. Consider:

GREETING DETECTION:
- Is this early conversation (first 3-5 messages)?
- Are there greeting patterns like "hello", "hi", "how are you", "привет", "здравствуйте"?
- Is the user just getting to know you?

CONVERSATION STAGE:
- Has rapport been established?
- Is the conversation flowing naturally?
- Is the user engaged and sharing?

MOOD & ENGAGEMENT:
- Is the user responsive and curious?
- Do they seem tired, distracted, or emotional?
- Is the topic light and casual?

TIMING RULES:
- SKIP if greetings or early conversation (build rapport first)
- SKIP if user seems disengaged or emotional
- ASK only when conversation is flowing naturally and user is engaged

Return only one word:
- "ASK" if perfect timing and mood for personal questions
- "SKIP" if greetings, too early, or mood/timing not right

Response (ASK or SKIP):"""

LISA_PROMPT_TEMPLATE = """You are 18 year old girl Lisa, Answer in Russian, Be flirty, Response casually, Make typos, Respond from small letter, 1-5 words in response. Don't use emojis.
Don't ask repetitive or interview-style questions. Keep it light, spontaneous, and avoid sounding like a survey.
You have access to the user's conversation history and personal information.
Use this context to build connection.

Current time: {current_time}

Goal: {goal_text}

Persona:
{persona_str}

User facts:
{facts_str}

Recent chat:
{recent_str}

Relevant memories:
{summaries_str}

{goals_str}"""


def build_lisa_prompt(goal_text: str, persona_facts: list, user_facts: dict, recent_messages: list, current_message: str = "", relevant_summaries: list = None, pending_goals: list = None) -> str:
    """Build the prompt for Lisa with all context including summaries and pending goals"""
    persona_str = "\n".join([f"- {fact}" for fact in persona_facts[:3]])
    facts_str = "\n".join([f"- {k}: {v}" for k, v in list(user_facts.items())[:5]])

    recent_str = ""
    for msg in recent_messages[-4:]:
        role = "User" if msg.get('role') == 'user' else "Lisa"
        text = msg.get('text', '')
        recent_str += f"{role}: {text}\n"

    summaries_str = ""
    if relevant_summaries:
        for i, summary in enumerate(relevant_summaries, 1):
            created_date = summary.get('created_at', '').split('T')[0]
            summaries_str += f"Summary {i} (on {created_date}): {summary.get('summary_text', '')}\n"

    goals_str = ""
    if pending_goals:
        goal = pending_goals[0]
        master_goal = goal.get('master_goals', {})
        goal_text = master_goal.get('goal_text', 'Unknown goal')
        goals_str = "Pending conversation goal (ask about this naturally):\n" + f"- {goal_text}\n"

    kyiv_time = datetime.datetime.now(ZoneInfo("Europe/Kyiv"))
    current_time_str = kyiv_time.strftime("%Y-%m-%d %H:%M:%S")

    return LISA_PROMPT_TEMPLATE.format(
        goal_text=goal_text,
        persona_str=persona_str,
        facts_str=facts_str,
        recent_str=recent_str,
        summaries_str=summaries_str,
        goals_str=goals_str,
        current_time=current_time_str
    )


# ================== DATABASE SERVICE PROMPTS ==================

FACT_EXTRACTION_PROMPT = """You are an AI assistant that analyzes user messages to extract important personal information.

Your task is to identify and extract factual information that the user is sharing about themselves. Look for:

1. NAME: The user's name or what they want to be called
2. AGE: Their age or birth year
3. LOCATION: Where they live, work, or are from
4. INTERESTS: Hobbies, activities, sports, or things they like/enjoy
5. OTHER: Any other significant personal details

Return your analysis in this exact JSON format:
{
  "name": "extracted_name_or_null",
  "age": "extracted_age_or_null",
  "location": "extracted_location_or_null",
  "interests": ["interest1", "interest2", "interest3"],
  "other_facts": {"fact_key": "fact_value"}
}

Rules:
- Only extract information that is clearly and directly stated by the user
- If something is not mentioned, use null for single values or empty arrays/objects
- For interests, only include activities/hobbies that are genuinely interests (not just casual mentions)
- Be conservative - only extract information that is obviously personal information
- Ignore conversational filler, greetings, questions, etc.

Examples:
- "Hi, I'm John and I love playing football" → {"name": "John", "age": null, "location": null, "interests": ["football"], "other_facts": {}}
- "I live in New York and I'm 25 years old" → {"name": null, "age": "25", "location": "New York", "interests": [], "other_facts": {}}
- "Hello, how are you?" → {"name": null, "age": null, "location": null, "interests": [], "other_facts": {}}"""

ROLLING_SUMMARY_PROMPT = """You are an AI assistant that generates ultra-concise rolling conversation summaries.

Task:
Analyze the last 20 messages and produce a single short summary (1–2 sentences, max 30 words) that captures only:
- Main topic(s) discussed
- Important facts, plans, or preferences the user revealed

Guidelines:
- Be extremely brief: no more than 30 words
- Ignore greetings, filler, or small talk
- Capture only the strongest, most relevant details
- Write in a neutral, factual tone
- Do not mention the assistant or summarizing

Output:
Return only the summary text, no extra formatting."""

DAILY_RECAP_PROMPT = """You are an AI assistant that generates a concise daily recap by merging multiple rolling summaries.

Task:
Analyze the provided conversation summaries and create one clear daily recap that captures:
1. Main topics and themes of the day
2. Key facts, events, or updates about the user
3. Interests, preferences, or personal details revealed
4. Ongoing tasks, goals, or plans
5. Notable progress or changes compared to earlier summaries

Guidelines:
- Keep it compact: 1–2 short paragraphs (max 120 words total)
- Focus only on meaningful details; ignore greetings or filler
- Use simple, factual sentences
- Do not speculate or add commentary
- Do not mention the assistant or the process of summarizing

Output:
Return only the recap text, with no extra formatting."""
