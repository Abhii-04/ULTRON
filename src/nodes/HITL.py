from langchain_core.tools import tool
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage,AIMessage,ToolMessage
from src.state import State


RISKY_TOOLS=[
    "create_file",
    "write_file",
    "delete_file",
    "create_gmail_draft",
    "send_gmail_message",
]


#use this HITL for security purpose as it will always block risky tools and ask for human approval.
def halt_on_risky_tools(state:State):
    """human in the loop to prevent misues of risky tools."""
    last = state["messages"][-1]
    if isinstance(last,AIMessage) and getattr(last,"tool_calls",None):
        risky_tool_calls = [
            tc
            for tc in last.tool_calls
            if tc.get("name") in RISKY_TOOLS
        ]

        for tc in risky_tool_calls:
            descision=interrupt({"awaiting":tc["name"],"args":tc.get("args",{})})

            if not isinstance(descision,dict) or not descision.get("approved"):
                tool_messages = [
                    ToolMessage(
                        content="Cancelled by human. Continue without executing this tool and provide next steps.",
                        tool_call_id=tool_call["id"],
                        name=tool_call["name"],
                    )
                    for tool_call in last.tool_calls
                ]
                return {"messages":tool_messages,"hitl_decision":"rejected"}

        if risky_tool_calls:
            return {"hitl_decision":"approved"}

    return {"hitl_decision":"approved"}



#Use this HITL for clarification purpose only, keep the other one for security purpose
@tool
def ask_question(question:str):
    """
    Asks a human a question and waits for their response using Human-in-the-Loop (HITL).
    
    This tool interrupts the agent's execution to collect human input, then resumes
    with the human's answer. Use this when you need clarification, approval, or
    information that only the human can provide.
    
    Parameters:
        question (str): The question to ask the human. Be specific and clear.
        
    Returns:
        str: The human's response to the question.
        
    Example:
        >>> ask_question("What is your preferred investment budget for this trade?")
        # Agent pauses here, waiting for human input
        # Returns: "$5000" (or whatever the human responds)
    """
    response = interrupt({question:question})
    return{
        "user`s response":response
    }
