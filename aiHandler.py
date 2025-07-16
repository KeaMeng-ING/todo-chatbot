import re
from typing import Optional, Tuple

async def parse_ai_response(response: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    patterns = {
        "action": re.compile(r"^Action:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
        "task": re.compile(r"^Task:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
        "duedate": re.compile(r"^Due date:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
        "note": re.compile(r"^Note:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
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

    # Basic validation: action is required, others can be None
    if not action:
        return None, None, None, None

    return action, task, duedate, note
