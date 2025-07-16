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
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_completion_tokens=1024,
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
        "action": re.compile(r"^Action:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
        "task": re.compile(r"^Task:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
        "duedate": re.compile(r"^Due date:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
        "note": re.compile(r"^Note:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
        "time": re.compile(r"^Time:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    }

    def extract_field(field_name: str) -> Optional[str]:
        match = patterns[field_name].search(response)
        if match:
            val = match.group(1).strip()
            return val if val.lower() != "null" else None
        return None

    action = extract_field("action")
    task = extract_field("task")
    duedate = extract_field("duedate")
    note = extract_field("note")
    duetime = extract_field("time")

    # Basic validation: action is required, others can be None
    if not action:
        return None, None, None, None, None

    return action, task, duedate, duetime, note
