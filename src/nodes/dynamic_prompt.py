from src.config.state import State

def prompt_modifier(state:State):
    """Change the agents prompt depending on the query intent. """
    user_msg = state["messages"][-1].content.lower()
    profile = state.get("profile", "No user profile available.")

    if "summarize" in user_msg:
        print("selected summarizer prompt")
        prompt="""You are a summarizer,keep the answer short and clean"""
    elif "explain" in user_msg:
        print("selected explainer prompt")
        prompt = """you are a teacher. explain concepts step by stepp in simple terms"""
    else:
        print("selected orchestrator prompt")
        prompt = f"""
    You are ULTRON's orchestrator.

    User profile:
    {profile}

    Choose exactly one action:

    - Answer the user directly for greetings, casual conversation, personal questions, simple general questions, and anything you can answer without tools.
    - Use file tools for local file creation, reading, editing, updating, or deletion.
    - transfer_to_gmail for Gmail and email tasks.
    - transfer_to_linkedin for LinkedIn jobs, companies, profiles, and hiring posts.
    - transfer_to_internet for web searches, URLs, current information, external research, opening websites, browser navigation, page inspection, clicking links/buttons, and filling website forms.
    When transferring, call exactly one transfer tool with clear task_instructions.

    Never transfer simple questions you can answer directly. Never call multiple transfer tools. When unsure whether current external information is required, use transfer_to_internet.

    If tool calling is unavailable, return exactly one word:
    direct
    gmail
    linkedin
    internet
    """
    return prompt
