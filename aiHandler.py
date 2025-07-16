import re
from typing import Optional, Tuple
import os
from dotenv import load_dotenv
from groq import Groq
from prompt import system_prompt
import google.generativeai as genai

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

async def get_ai_response(text: str) -> str:
    try:
        # Remove any extra parameters that might be causing issues
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1024,  # Changed from max_completion_tokens
            top_p=1,
            stream=False,
            stop=None,
        )
        response = completion.choices[0].message.content
        return response

    except Exception as groq_error:
        print(f"Groq API failed: {groq_error}")
        print("Trying Gemini as fallback...")
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            full_prompt = f"{system_prompt}\n\nUser: {text}"
            gemini_response = gemini_model.generate_content(full_prompt)
            return gemini_response.text
        except Exception as gemini_error:
            print(f"Gemini API also failed: {gemini_error}")
            return None


async def parse_ai_response(response: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    patterns = {
        "action": re.compile(r"Action:\s*(.+)", re.IGNORECASE),
        "task": re.compile(r"Task:\s*(.+)", re.IGNORECASE),
        "duedate": re.compile(r"Due date:\s*(.+)", re.IGNORECASE),
        "time": re.compile(r"Time:\s*(.+)", re.IGNORECASE),
        "note": re.compile(r"Note:\s*(.+)", re.IGNORECASE),
    }

    def extract_field(field: str) -> Optional[str]:
        match = patterns[field].search(response)
        if match:
            val = match.group(1).strip()
            if val.lower() == "null":
                return None
            return val
        return None

    action = extract_field("action")
    task = extract_field("task")
    duedate = extract_field("duedate")
    duetime = extract_field("time")
    note = extract_field("note")

    # If required, add validation: return None tuple if action is missing
    if not action:
        return None, None, None, None, None

    return action, task, duedate, duetime, note