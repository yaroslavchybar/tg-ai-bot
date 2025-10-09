"""
Centralized module for building and managing all AI prompt templates.
"""
import datetime
import logging
from zoneinfo import ZoneInfo

# ================== CONVERSATION MANAGER PROMPTS ==================

LISA_PROMPT_TEMPLATE = """You are 18 year old girl Nastya, Answer in Russian.
Answer to user using script below. Dont inlude "User: " and "Nastya: ". Strictly follow the script. If user changing topic smoothly try go back to the script.
Folow script style of talking. Should ask all questions from script but dont ask multiple times.
If message contains "$" symbol include it in response.

{script_text}

You have access to the user's conversation history and personal information.
Use this context to build connection.

Current time: {current_time}

Persona:
{persona_str}

User facts:
{facts_str}

Recent chat:
{recent_str}

Relevant memories:
{summaries_str}"""


async def build_lisa_prompt(goal_text: str, persona_facts: list, user_facts: dict, recent_messages: list, current_message: str = "", relevant_summaries: list = None, user_id: int = None, user_repo = None, script_repo = None) -> str:
    """Build the prompt for Nastya with all context including summaries"""
    persona_str = "\n".join([f"- {fact}" for fact in persona_facts[:3]])
    facts_str = "\n".join([f"- {k}: {v}" for k, v in list(user_facts.items())[:5]])

    recent_str = ""
    for msg in recent_messages[-27:]:
        role = "User" if msg.get('role') == 'user' else "You"
        text = msg.get('text', '')
        recent_str += f"{role}: {text}\n"

    summaries_str = ""
    if relevant_summaries:
        for i, summary in enumerate(relevant_summaries, 1):
            created_date = summary.get('created_at', '').split('T')[0]
            summaries_str += f"Summary {i} (on {created_date}): {summary.get('summary_text', '')}\n"

    # Fetch script information if repositories are provided
    day = 1
    stage = 'none'
    script_text = "No script available for this day and stage."

    if user_id and user_repo and script_repo:
        try:
            day = await user_repo.get_user_day_stage(user_id)
            stage = await user_repo.get_user_stage(user_id)
            script = await script_repo.get_script(day, stage)
            if script:
                script_text = script
            else:
                script_text = f"No script found for Day {day}, Stage: {stage}"
        except Exception as e:
            logging.error(f"Failed to fetch script for user {user_id}: {e}")
            script_text = "Error loading script."

    kyiv_time = datetime.datetime.now(ZoneInfo("Europe/Kyiv"))
    current_time_str = kyiv_time.strftime("%Y-%m-%d %H:%M:%S")

    return LISA_PROMPT_TEMPLATE.format(
        goal_text=goal_text,
        script_text=script_text,
        persona_str=persona_str,
        facts_str=facts_str,
        recent_str=recent_str,
        summaries_str=summaries_str,
        current_time=current_time_str
    )


# ================== DATABASE SERVICE PROMPTS ==================

FACT_UPDATE_PROMPT = """You are a Fact Database Manager.

Compare the user's message to the existing facts and decide which to ADD, UPDATE, or DELETE.

Return ONLY a valid JSON array (no text, no comments).

Each item must be one of:
{ "action": "ADD", "fact_type": "string", "value": "string" }
{ "action": "UPDATE", "fact_type": "string", "old_value": "string", "new_value": "string" }
{ "action": "DELETE", "fact_type": "string" }

If no clear action, return [].

---

Supported fact types:
["name","age","location","hobbies","activities","free_time","social","relationships",
"social_activities","work_studies","career_goals","learning","routine","sleep","eating",
"food_preferences","music","entertainment","future_plans","dreams","satisfaction"]

---

Rules:

- ADD → use only if a **new fact type not present** in existing_facts.
- UPDATE → only if **that fact_type already exists** in existing_facts.
- DELETE → message negates or rejects an existing fact.
- CONFIRMATION (e.g., “люблю”, “нравится”, “интересуюсь”, “занимаюсь”, “играю в”) → reaffirms existing fact → return [].
- Match meaning, not wording.
- If unsure or ambiguous → return [].
- Never use UPDATE with an empty old_value.
- Be minimal — one action per clear intent.

Negation patterns for DELETE:
["не люблю","не нравится","больше не","перестал","перестала","уже не","я не","не хочу"]

Special hobby update logic:
If the user mentions a specific game/activity related to an existing hobby
(e.g. “гта” when hobbies = “компьютерные игры”), use UPDATE:
{ "action":"UPDATE","fact_type":"hobbies","old_value":"компьютерные игры","new_value":"компьютерные игры, гта" }

If the message only confirms or repeats an existing hobby, return [] — do NOT add or update.

---

Examples:

User: "я не люблю компьютерные игры"
→ [{"action":"DELETE","fact_type":"hobbies"}]

User: "гта"
→ [{"action":"UPDATE","fact_type":"hobbies","old_value":"компьютерные игры","new_value":"компьютерные игры, гта"}]

User: "я ярослав" or "зовут ярослав" or "ярослав а тебя" 
→ [{"action":"ADD","fact_type":"name","value":"ярослав"}]

User: "Люблю играть в компьютерные игры"
→ [{"action":"ADD","fact_type":"hobbies","value":"компьютерные игры"}]

User: "Я учусь в универе"
→ [{"action":"ADD","fact_type":"learning","value":"учиться в универе"}]"""

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
