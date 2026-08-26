from textwrap import dedent
from typing import Annotated
from langchain_core.tools import tool, BaseTool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.prebuilt import InjectedState
from langgraph_supervisor.handoff import METADATA_KEY_HANDOFF_DESTINATION

def _normalize_agent_name(agent_name:str)->str:
    """convert an agent name to a valid tool name format"""
    return agent_name.replace(" ","_".lower())


#Custom handoff tool that lets the orchestrator transfer a task to another agent while providing exact instructions
def create_task_instructions_handoff_tool(*,agent_name:str,name:str|None=None,description:str|None=None)->BaseTool:
    """create a tool that transfers control to another agent with specific task instructions."""
    if name is None:
        name=f"transfer_to_{_normalize_agent_name(agent_name)}"
    if description is None:
        description = f"Ask agent '{agent_name}' for help"
    
    @tool(name,description=description)
    def handoff_to_agent(
        task_instructions:Annotated[str,dedent("""
        specify EXACTLY what this agent should do,what data they should retrieve, and what output you expect back.
        Include any specific parameters or constraints that will help the agent complete the task succesfully. 
        """)],
        state:Annotated[dict,InjectedState],
        tool_call_id:Annotated[str,InjectedToolCallId]
        ):
        tool_message = ToolMessage(
            content =dedent(f"""
            Succesfully transfered to {agent_name}.
            [INSTRUCTIONS TO FOLLOW]: {task_instructions} 
            """),
            name=name,
            tool_call_id= tool_call_id,
            response_metadata = {METADATA_KEY_HANDOFF_DESTINATION:agent_name},
        )

        messages = state["messages"] 
        return Command(
            goto=agent_name,
            graph=Command.PARENT,
            update={
                "messages":messages+[tool_message],
                "task_instructions":task_instructions,
            },
        )
    handoff_to_agent.metadata={METADATA_KEY_HANDOFF_DESTINATION:agent_name}
    return handoff_to_agent
    

    #pass it as a tool to orchestrator or any planner agent 
    