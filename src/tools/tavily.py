from dotenv import load_dotenv
import os
from tavily import TavilyClient
from typing import Literal


load_dotenv(override=True)

def Internet_search(query:str,max_results:int=5,topic:Literal["general","news"]="general",included_raw_content:bool=False):
    """Search the web for current or external information."""
    api_key = os.getenv('TAVILY_API_KEY')
    if not api_key:
        raise RuntimeError("api key not found")
    tavily = TavilyClient(api_key)
    print("ran tavily tool")
    response= tavily.search(
        query = query,
        max_results = max_results,
        topic = topic,
        included_raw_content=included_raw_content,
        )
    results=[]
    for result in response["results"]:
        results.append({
            "title":result["title"],
            "content":result["content"][:400]
        })
    return results
