import json
import os
import anthropic
from dotenv import load_dotenv

# Load ANTHROPIC_API_KEY from the .env file (the Anthropic client reads it from there)
load_dotenv()

# Instructions for Claude
SYSTEM = """You help people plan their day in small, calm steps.
For the task the person gives you, choose how much energy it takes
(Light, Medium or Heavy) and write up to 4 short, concrete steps.
Each step should be under 10 words and start with a verb."""

# The exact JSON shape we want back: a load level and a list of steps
SCHEMA = {
    "type": "object",
    "properties": {
        "load": {"type": "string", "enum": ["Light", "Medium", "Heavy"]},
        "steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["load", "steps"],
    "additionalProperties": False,
}

# Backup suggestions: if a keyword appears in the task, use its load and steps
KEYWORDS = {
    "clean": ("Medium", ["Get your cleaning things", "Clean one small area", "Put things back", "Wash your hands"]),
    "laundry": ("Light", ["Gather your clothes", "Start the machine", "Set a timer", "Hang or dry the clothes"]),
    "email": ("Light", ["Open the message", "Write a short reply", "Read it once", "Send it"]),
    "reply": ("Light", ["Open the message", "Write a short reply", "Read it once", "Send it"]),
    "call": ("Medium", ["Write what you want to say", "Find a quiet spot", "Make the call", "Note what was agreed"]),
    "shop": ("Heavy", ["Check what you need", "Write a short list", "Take bags and wallet", "Go to the store"]),
    "cook": ("Medium", ["Choose a simple recipe", "Get the ingredients out", "Cook step by step", "Clean up"]),
    "meeting": ("Medium", ["Check the time and place", "Write one question to ask", "Leave or join on time"]),
}
DEFAULT = ("Medium", ["Get what you need ready", "Start with one small part", "Take a short break if needed", "Finish and tidy up"])


# Ask Claude for a load level and up to 4 steps; use the keyword backup if anything goes wrong
def suggest_task(text):
    # No key in .env: don't try to call Claude, go straight to the backup
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("No API key found, using keyword backup")
        return keyword_backup(text)
    try:
        client = anthropic.Anthropic(timeout=20.0, max_retries=1)
        response = client.beta.messages.create(
            model="claude-opus-5-5",
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # if Claude declines, the API retries on another model
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            system=SYSTEM,
            messages=[{"role": "user", "content": text}],
        )
        if response.stop_reason == "refusal":
            return keyword_backup(text)
        answer = json.loads(next((b.text for b in response.content if b.type == "text"), ""))
        return {"load": answer["load"], "steps": answer["steps"][:4], "source": "ai"}
    # Any error at all (network, bad key, odd answer, SDK problem) uses the backup instead of crashing
    except Exception as error:
        print("AI suggestion failed, using keyword backup:", error)
        return keyword_backup(text)


# Backup: look for a known keyword in the task, or use general steps
def keyword_backup(text):
    for word, (load, steps) in KEYWORDS.items():
        if word in text.lower():
            return {"load": load, "steps": steps, "source": "backup"}
    load, steps = DEFAULT
    return {"load": load, "steps": steps, "source": "backup"}
