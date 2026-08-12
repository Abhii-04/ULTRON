import os
from dotenv import load_dotenv
from typing import Any, Dict, List

#Langgraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

#Langchain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

#Subgraph Imports
from src.subgraphs.internet_agent import InternetAgent
from src.subgraphs.assistent import Assistent

from src.state import State

load_dotenv(override=True)

llm=ChatOpenAI(
api_key = os.getenv('DEEPSEEK_API_KEY'),
model = 'deepseek-v4-flash',
base_url = "https://api.deepseek.com",
)

class Agent:
    def __init__(self):
        self.internet_graph=None
        self.browser_graph=None
        self.graph=None
        self.agent_id = None
        self.memory = None

    async def setup(self):
        internet = InternetAgent()
        internet.setup()
        await internet.build_graph()
        self.internet_graph = internet.graph

        assistent = Assistent()
        assistent.setup()
        await assistent.build_graph()
        self.browser_graph = assistent.graph

        self.memory = InMemorySaver()
        await self.build_graph()

    def orchestrator(self, state: State) -> Dict[str, Any]:
        system_message = SystemMessage(
            content="""
            You are the routing controller for a two-agent assistant system.

            Read the user's latest request and choose the agent that should handle it.

            Tool-call formatting rule:
            Never write DSML, XML, JSON, or any other tool-call markup in your text.
            Your response must be exactly one route word.

            Priority rule:
            If the request mentions or requires the internet, web, online sources, URLs,
            search, lookup, browsing, current information, recent information, latest
            information, external information, source-backed research, or facts that may
            have changed, route to internet.

            Route to internet when the task needs:
            - Any task over the internet, web, online services, websites, URLs, or search engines
            - Current, recent, or external information
            - Web search or source-backed research
            - News, prices, schedules, product availability, laws, docs, or facts that may have changed
            - Comparing options using online sources
            - Looking up documentation, APIs, errors, package behavior, or examples from online sources

            Route to assistant when the task needs:
            - General reasoning
            - Writing, editing, planning, summarizing, brainstorming, or explaining
            - Help based only on the conversation context
            - Any task that does not require internet, web, online, current, recent, external, or source-backed information

            When unsure whether internet is needed, choose internet.

            Return ONLY one word:
            internet
            assistant
            """
        )

        messages = [system_message] + state["messages"]
        response = llm.invoke(messages)

        route = response.content.strip().lower()

        if route not in ("internet", "assistant"):
            route = "assistant"

        return {
            "next": route,
        }

    def orchestrator_router(self, state: State):
        route = state.get("next")

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
                "tool call, so no tool was executed. If this was a Gmail retry, "
                "first enable the Gmail API for the Google Cloud project used by "
                "credentials.json, then run the request again."
            )

        return content

    async def build_graph(self):
        if self.internet_graph is None:
            raise RuntimeError(
                "Internet graph has not been initialized. "
                "Call setup() before build_graph()."
            )
        if self.browser_graph is None:
            raise RuntimeError(
                "Browser graph has not been initialized. "
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
            "assistant",
            self.browser_graph
        )

        graph_builder.add_edge(
            START,
            "orchestrator"
        )

        graph_builder.add_conditional_edges(
            "orchestrator",
            self.orchestrator_router,
            {
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
            "assistant",
            END
        )

        self.graph = graph_builder.compile(
            checkpointer=self.memory
        )

    async def run_superstep(self, message,history):
        config = {"configurable":{"thread_id": self.agent_id}}

        state = {
            "messages":[HumanMessage(content=message)],
        }

        result = await self.graph.ainvoke(
            state,
            config=config
        )

        final_message = result["messages"][-1]
        final_message.content = self.sanitize_final_content(final_message.content)

        print(final_message.content)
        return result
