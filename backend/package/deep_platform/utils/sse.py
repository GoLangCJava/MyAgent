import json

def format_sse(data: dict, event: str | None = None, id: str | None = None) -> str:
    lines=[]
    if id: lines.append(f"id: {id}")
    if event: lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    return "\n".join(lines)+"\n\n"

def format_heartbeat() -> str:
    return ": heartbeat\n\n"
