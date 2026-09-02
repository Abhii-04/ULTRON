from langchain_core.messages import HumanMessage
from src.config.state import State
from typing import Any,List
from src.config.memory import memory


DIRECT_CHAT_HISTORY_LIMIT = 6
MEMORY_TOP_K = 3
MAX_MEMORY_ITEM_CHARS = 180

FILE_ACTION_WORDS = {"read","write","create","delete","edit","update","save",}
FILE_TARGET_WORDS = { "file","folder","directory","path",".txt",".md",".py",".json",}
SERVICE_INTENT_WORDS = { "gmail","email","inbox","draft", "linkedin","job","profile","web","internet","search","latest","current",
"recent","url","http","https","browser","open","website", "webpage", "site","navigate","click","inspect","solari",
"qa","test","tester","repo","github","frontend","backend",}

CASUAL_CHAT_WORDS = { "hi","hello", "hey","thanks","thank you", "ok", "okay", "cool","great"}



def _message_text(message:Any)->str:
    content = getattr(message,"content","")
    return content if isinstance(content,str) else str(content)

def _latest_human_text(messages:List[Any])->str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return _message_text(message)
    return _message_text(messages[-1] if messages else " ")


def _looks_like_tool_request(text:str)->bool:
    lowered = text.lower()
    has_file_action = any(word in lowered for word in FILE_ACTION_WORDS)
    has_file_target = any(word in lowered for word in FILE_TARGET_WORDS)
    return (has_file_action and has_file_target) or any(word in lowered for word in SERVICE_INTENT_WORDS)

def _looks_casual(text:str)->bool:
    lowered = text.strip().lower()
    return len(lowered.split()) <= 5 and any(word ==lowered or word in lowered for word in CASUAL_CHAT_WORDS)

def recent_chat_messages(messages:List[Any])->list[Any]:
    return messages[-DIRECT_CHAT_HISTORY_LIMIT:]

def _format_memory_context(memory_list:List[dict[str,Any]])->str:
    memory_lines = []
    for item in memory_list:
        memory_text = item.get("memory")
        if not memory_text:
            continue
        memory_lines.append(f"-{str(memory_text)[:MAX_MEMORY_ITEM_CHARS]}")
    return "\n".join(memory_lines)

def _load_memory_context(user_text: str, user_id: str) -> str:
    try:
        memories = memory.search(user_text, filters={"user_id": user_id}, top_k=MEMORY_TOP_K)
        return _format_memory_context(memories.get("results", []))
    except Exception as e:
        print(f"Error retrieving memory: {type(e).__name__}:{e}")
        return ""


def _save_memory(user_text: str, assistant_text: str, user_id: str) -> None:
    if _looks_casual(user_text):
        return

    try:
        interaction = [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ]
        result = memory.add(interaction, user_id=user_id)
        print(f"memory saved:{len(result.get('results', []))} memories added")
    except Exception as e:
        print(f"Error saving memory: {type(e).__name__}:{e}")


def handle_file_tool_error(error: Exception) -> str:
    """Return file tool failures to the model instead of crashing the graph."""
    return f"File tool call failed: {type(error).__name__}: {error}"
