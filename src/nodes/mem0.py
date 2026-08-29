from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from mem0 import MemoryClient
from src.state import State
import os 
from dotenv import load_dotenv


load_dotenv(override = True)
mem0=MemoryClient()

llm=ChatOpenAI(
    api_key = os.getenv("DEEPSEEK_API_KEY"),
    base_url = 'https://api.deepseek.com',
    model = 'deepseek-v4-flash',
)

def chatbot(state:State):
    messages=state["messages"]
    user_id = state["user_id"]
    try:
        #retrieve relevant memories
        memories = mem0.search(messages[-1].content,filters = {"user_id":user_id})


        #handle dict response format
        memory_list = memories['results']
        context = "relevant information from previous conversations:\n"
        for memory in memory_list:
            context += f"-{['memory']}\n"

        system_message = SystemMessage(context =f"""you are a helpful customer support assistant. Use the provieded context to personalize your responses
         and remember user preferences and past interactions {context}""")

        full_message = [system_message]+messages
        response = llm.invoke(full_message)
        try:
            interaction = [
                {
                    "role":"user",
                    "content":messages[-1].content
                },
                {
                    "role":"assistant",
                    "content": response.content
                }
            ]
            result = mem0.add(interaction,user_id=user_id)
            print(f"memory saved:{len(result.get('results',[]))} memories added")

        except Exception as e:
            print(f"Error saving memory:{e}")

        return {"messages":[response]}

    except Exception as e:
        print(f"Error in chatbot: {e}")

        #fallback response without memory context
        response = llm.invoke(messages)
        return{"messages":[response]}
    
