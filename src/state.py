from tkinter import ANCHOR
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field ,ConfigDict
from typing import Literal,Annotated,Any,Optional, Dict, TypedDict,List


class State(TypedDict, total=False):
    messages:Annotated[List[str],add_messages]
    next:str
    path:Annotated[str,"path to the file to be created."]
    file_name:Annotated[str,"name of the file to be created"]
    filepath: Annotated[str, "the path to the file to be modified"]
    current_file_content: Annotated[Optional[str], "the content of the file currently being edited or created"]