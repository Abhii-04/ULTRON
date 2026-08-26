import os
from tavily import TavilyClient
from typing import Literal
from langchain_core.tools import tool
from dotenv import load_dotenv
from typing import Dict,Any,List


load_dotenv(override=True)

FORBIDDEN_KEYWORDS = {
    # Access restrictions
    "access denied",
    "forbidden",
    "page not found",
    "404 not found",
    "sign in to continue",
    "login required",
    "enable javascript",
    "verify you are human",
    "captcha",

    # Cookie and privacy noise
    "accept all cookies",
    "cookie policy",
    "privacy preferences",
    "manage cookies",

    # Promotional and spam content
    "sponsored content",
    "limited time offer",
    "buy now",
    "subscribe now",
    "affiliate link",
    "promoted content",

    # Scraping/error responses
    "request blocked",
    "rate limit exceeded",
    "too many requests",
    "temporarily unavailable",
    "service unavailable",
}


@tool
def web_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news"] = "general",
) -> Dict[str, List[Dict[str, str]]]:
    """Search the web for current or external information."""

    max_results = max(1, min(max_results, 10))

    tavily = TavilyClient(os.environ["TAVILY_API_KEY"])

    response = tavily.search(
        query=query,
        max_results=max_results,
        topic=topic,
        include_raw_content=False,
    )

    results = []

    for page in response.get("results", []):
        content = page.get("content", "")

        if any(
            keyword.lower() in content.lower()
            for keyword in FORBIDDEN_KEYWORDS
        ):
            continue

        results.append({
            "title": page.get("title", ""),
            "url": page.get("url", ""),
            "content": content[:400],
        })

    return {"results": results}