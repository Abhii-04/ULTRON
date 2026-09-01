from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from src.config.state import State

def print_messages(state:State,messages,truncate_length=200):
    """
    Print messages with trunctatino for long tool message content """
    for message in messages:
        if isinstance(message,ToolMessage):
            print(f"=================================[1m Tool Message [0m=================================")
            print(f"name:{message.name}")

            content = message.content
            if len(content)>truncate_length:
                print(f"{content[:truncate_length]}...\n[content truncated - {len(content)} chars total]")
            else:
                print(content)
        else:
            message.preety_print()