from src.state import State

def dynamic_agent_selection(state:State):
    """Select an agent based on task given by user. """
    last_msg = state["messages"][-1].content.lower()

    if any(word in last_msg for word in ["linkedin"]):
        return "Linkedin"
    elif any(word in last_msg for word in ["web search","internet search","search","latest","current"]):
        return "internet"
    else:
        return "orchestrator"
