from langgraph.graph.message import add_messages
from typing import Annotated, Any, TypedDict


class State(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    next: str
    user_id: str
    feedback_on_work: str
    internet_skill: str
    linkedin_skill: str
    hitl_decision: str
    task_instructions: str
    mem0_user_id: str
    context_trim_call_count: int
