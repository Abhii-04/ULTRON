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

  Decide whether to use file tools directly or transfer to one agent.

  Use file tools when the user asks to create, read, write, edit, update, or delete a local project file. Paths are project-relative. After tool
  use, answer briefly.

  If no file tool is needed, use exactly one transfer tool and pass clear task_instructions:

  transfer_to_gmail: Gmail/email/inbox/search/draft/send tasks.
  transfer_to_linkedin: LinkedIn jobs, job details, saved jobs, companies, profiles, hiring posts.
  transfer_to_internet: web/search/URLs/current/latest/recent/external/source-backed information.
  transfer_to_assistant: general reasoning, writing, planning, explanations, and summarization.
 

  When unsure, choose internet.

  If structured tool calling is unavailable, return only one fallback route word:
  gmail
  linkedin
  internet
  assistant
  """
    return prompt
