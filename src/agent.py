import os
from dotenv import load_dotenv
from typing import Any, Dict, List

#Langgraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

#Langchain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

#Subgraph Imports
from src.subgraphs.internet_agent import InternetAgent
from src.subgraphs.assistant import Assistant
from src.subgraphs.gmail_agent import Gmail_agent
from src.subgraphs.linkedin_agent import LinkedinAgent

from src.state import State

load_dotenv(override=True)

llm=ChatOpenAI(
api_key = os.getenv('DEEPSEEK_API_KEY'),
model = 'deepseek-v4-flash',
base_url = "https://api.deepseek.com",
)


def _latest_human_text(messages: List[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage) and isinstance(message.content, str):
            return message.content
    return ""


def _deterministic_route_from_text(text: str) -> str | None:
    latest_text = text.lower()

    if any(word in latest_text for word in ("gmail", "email", "mail", "inbox")):
        return "gmail"

    if "linkedin" in latest_text and any(
        phrase in latest_text
        for phrase in (
            "job",
            "saved job",
            "company",
            "profile",
            "hiring post",
            "search post",
        )
    ):
        return "linkedin"

    return None

class Agent:
    def __init__(self):
        self.internet_graph=None
        self.assistant_graph=None
        self.gmail_graph=None
        self.linkedin_graph=None
        self.graph=None
        self.agent_id = None
        self.checkpointer = None
        self.store = None
        self.internet_agent = None
        self.assistant_agent = None
        self.gmail_agent = None
        self.linkedin_agent = None

    async def setup(self):
        internet = InternetAgent()
        internet.setup()
        await internet.build_graph()
        self.internet_graph = internet.graph
        self.internet_agent = internet

        gmail = Gmail_agent()
        await gmail.build_graph()
        self.gmail_graph = gmail.graph
        self.gmail_agent = gmail

        linkedin = LinkedinAgent()
        await linkedin.build_graph()
        self.linkedin_graph = linkedin.graph
        self.linkedin_agent = linkedin

        assistant = Assistant()
        assistant.setup()
        await assistant.build_graph()
        self.assistant_graph = assistant.graph
        self.assistant_agent = assistant

        self.checkpointer = InMemorySaver()
        self.store = InMemoryStore()
        await self.build_graph()

    def get_user_profile(self, store: BaseStore, user_id: str) -> Dict[str, Any]:
        memory = store.get(("user", user_id), "profile")
        return memory.value if memory else {}

    def update_user_profile(
        self,
        user_id: str,
        profile: Dict[str, Any],
    ) -> None:
        if self.store is None:
            raise RuntimeError("Memory store has not been initialized. Call setup() first.")

        self.store.put(("user", user_id), "profile", profile)

    def orchestrator(self, state: State, store: BaseStore) -> Dict[str, Any]:
        user_id = state.get("user_id", "default")
        profile = self.get_user_profile(store, user_id)
        deterministic_route = _deterministic_route_from_text(
            _latest_human_text(state["messages"])
        )

        if deterministic_route is not None:
            return {
                "next": deterministic_route,
            }

        system_message = SystemMessage(
            content=f"""
            You are the routing controller for a four-workflow assistant system.

            Stored user profile for routing context:
            {profile}

            Read the user's latest request and choose the agent that should handle it.

            Tool-call formatting rule:
            Do not describe tool calls or tool syntax in your text.
            Your response must be exactly one route word.

            Priority rule:
            If the request is about Gmail, email, inbox messages, email drafts,
            reading email, searching email, or sending email, route to gmail.

            If the request is about LinkedIn job search, job details, saved jobs,
            company research, company profiles, or hiring-post searches, route to linkedin.

            If the request mentions or requires the internet, web, online sources, URLs,
            websites, search, lookup, browsing, current
            information, recent information, latest information, external information,
            connected online accounts, MCP-backed services,
            source-backed research, or facts that may have changed, route to internet.

            Route to gmail when the task needs:
            - Gmail search, Gmail reading, Gmail thread lookup, Gmail drafts, or Gmail sending
            - Email inbox actions
            - Email account actions
            - Finding, summarizing, drafting, replying to, or sending email

            Route to internet when the task needs:
            - Any task over the internet, web, online services, websites, URLs, or search engines
            - Current, recent, or external information
            - Web search or source-backed research
            - News, prices, schedules, product availability, laws, docs, or facts that may have changed
            - Comparing options using online sources
            - Looking up documentation, APIs, errors, package behavior, or examples from online sources

            Route to linkedin when the task needs:
            - LinkedIn job search, job details, saved jobs, company research, company profiles, or hiring-post searches
            - MCP-backed LinkedIn job tools

            Route to assistant when the task needs:
            - General reasoning
            - Writing, editing, planning, summarizing, brainstorming, or explaining
            - Help based only on the conversation context
            - Any task that does not require internet, web, online, current, recent,
            external, source-backed information, LinkedIn, Gmail, email,
            or connected account tools

            When unsure whether internet is needed, choose internet.

            Return ONLY one word:
            gmail
            linkedin
            internet
            assistant
            """
        )

        messages = [system_message] + state["messages"]
        response = llm.invoke(messages)

        route = response.content.strip().lower()

        if route not in ("gmail", "linkedin", "internet", "assistant"):
            route = "assistant"

        return {
            "next": route,
        }

    def orchestrator_router(self, state: State):
        route = state.get("next")

        if route == "gmail":
            return "gmail"

        if route == "linkedin":
            return "linkedin"

        if route == "internet":
            return "internet"

        if route == "assistant":
            return "assistant"

        return END

    def format_conversation(self,messages:List[Any])->str:
        conversation = "Conversation history: \n\n"

        for message in messages:
            if isinstance(message,HumanMessage):
                conversation += f"User: {message.content}\n"
            elif isinstance(message,AIMessage):
                text  = message.content or "[Tools use]"
                conversation += f"Assistant: {text}\n"

        return conversation

    def sanitize_final_content(self, content: Any) -> Any:
        if isinstance(content, str) and "DSML" in content and "tool_calls" in content:
            return (
                "The model produced raw tool-call markup instead of a structured "
                "tool call, so no tool was executed. Re-run the request; if it "
                "keeps happening, the model/provider is not returning tool calls "
                "through the expected structured interface."
            )

        return content

    async def build_graph(self):
        if self.internet_graph is None:
            raise RuntimeError(
                "Internet graph has not been initialized. "
                "Call setup() before build_graph()."
            )
        if self.assistant_graph is None:
            raise RuntimeError(
                "Assistant graph has not been initialized. "
                "Call setup() before build_graph()."
            )
        if self.gmail_graph is None:
            raise RuntimeError(
                "Gmail graph has not been initialized. "
                "Call setup() before build_graph()."
            )
        if self.linkedin_graph is None:
            raise RuntimeError(
                "LinkedIn graph has not been initialized. "
                "Call setup() before build_graph()."
            )

        graph_builder = StateGraph(State)

        graph_builder.add_node(
            "orchestrator",
            self.orchestrator
        )

        graph_builder.add_node(
            "internet",
            self.internet_graph
        )

        graph_builder.add_node(
            "gmail",
            self.gmail_graph
        )

        graph_builder.add_node(
            "linkedin",
            self.linkedin_graph
        )

        graph_builder.add_node(
            "assistant",
            self.assistant_graph
        )

        graph_builder.add_edge(
            START,
            "orchestrator"
        )

        graph_builder.add_conditional_edges(
            "orchestrator",
            self.orchestrator_router,
            {
                "gmail": "gmail",
                "linkedin": "linkedin",
                "internet": "internet",
                "assistant": "assistant",
                END: END,
            },
        )

        graph_builder.add_edge(
            "internet",
            END
        )

        graph_builder.add_edge(
            "gmail",
            END
        )

        graph_builder.add_edge(
            "linkedin",
            END
        )

        graph_builder.add_edge(
            "assistant",
            END
        )

        self.graph = graph_builder.compile(
            checkpointer=self.checkpointer,
            store=self.store,
        )

    async def close(self):
        if self.internet_agent is not None:
            await self.internet_agent.close()
        if self.linkedin_agent is not None:
            await self.linkedin_agent.close()

    async def run_superstep(self, message, history, user_id: str = "default"):
        config = {"configurable":{"thread_id": self.agent_id}}

        state = {
            "messages":[HumanMessage(content=message)],
            "user_id": user_id,
        }

        result = await self.graph.ainvoke(
            state,
            config=config
        )

        final_message = result["messages"][-1]
        final_message.content = self.sanitize_final_content(final_message.content)

        print(final_message.content)
        return result
