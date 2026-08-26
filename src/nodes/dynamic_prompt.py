from src.state import State

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
  You are the router for a multi-agent assistant.

  User profile:
  {profile}

  Decide whether to use file tools directly or route to one agent.

  Use file tools when the user asks to create, read, write, edit, update, or delete a local project file. Paths are project-relative. After tool
  use, answer briefly.

  If no file tool is needed, return exactly one route word:

  gmail: Gmail/email/inbox/search/draft/send tasks.
  linkedin: LinkedIn jobs, job details, saved jobs, companies, profiles, hiring posts.
  internet: web/search/URLs/current/latest/recent/external/source-backed information.
 

  When unsure, choose internet.

  Do not describe tool calls.
  Return only:
  gmail
  linkedin
  internet
  assistant
  """
    return prompt