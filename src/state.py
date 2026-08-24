from langgraph.graph.message import add_messages
from typing import Annotated, Any, TypedDict


class State(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    next: str
    user_id: str
    feedback_on_work: str
    internet_skill: str
    linkedin_skill: str
