from typing import Callable
from langchain_core.tools import BaseTool, tool
from langgraph.graph.state import RunnableConfig
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


###universal tool wrapper to use HITL cause mcp tools  cant be controlled with the curent settings
def add_approval(main_tool:Callable|BaseTool)->BaseTool:
    """wrap a tool to support human in the loop review"""
    if not isinstance(main_tool,BaseTool):
        main_tool = tool(main_tool)
    
    @tool(
        main_tool.name,
        description = main_tool.description,
        args_schema= main_tool.args_schema
    )
    def call_main_tool_with_hitl(config:RunnableConfig, **tool_input):
        descision =interrupt({
            "awaiting": main_tool.name,
            "args":tool_input,
        })

        #tool approved
        if isinstance(descision,dict) and descision.get("approved"):
            return main_tool.invoke(tool_input,config)

        #tool rejected
        return "cancelled by human.continue without executing that tool and provide next steps"
    return call_main_tool_with_hitl


def add_approval_to_risky_tools(tools: list[BaseTool],) -> list[BaseTool]:
    """Wrap only risky tools."""

    return [
        add_approval(current_tool)
        if current_tool.name in RISKY_TOOLS
        else current_tool
        for current_tool in tools
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
