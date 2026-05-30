import yaml
import os

from duckduckgo_search import DDGS  # type: ignore
from langchain_ollama import ChatOllama  # type: ignore
from langchain.tools import tool  # type: ignore

def _get_llm():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config.yaml")
    if not os.path.exists(config_path):
        if os.path.exists("config.yaml"):
            config_path = "config.yaml"
        elif os.path.exists("../config.yaml"):
            config_path = "../config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return ChatOllama(model=config["model"], base_url=config["model_url"], keep_alive="5m")

@tool
def search_web(query: str) -> str:
    """Searches the web using DuckDuckGo and returns a summary. Trigger this tool for questions about current events, real-time or post-2023 information, news, up-to-date facts, or facts you do not know."""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append(f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}\n")
        
        context = "\n".join(results)
        
        # Summarize using LLM
        llm = _get_llm()
        prompt = (
            f"Based on the following search results for '{query}', "
            "provide a concise and helpful summary. Address the user as 'Sir'.\n\n"
            f"{context}"
        )
        response = llm.invoke(prompt)
        summary = response.content
        
        # Save search query and summary to persistent memory
        try:
            from core import memory
            memory.add_memory(
                role="system",
                content=f"Searched the web for '{query}' and found: {summary}",
                metadata={"type": "web_search", "query": query}
            )
        except Exception as me:
            print(f"[Memory Warning] Failed to log search to database: {me}")
            
        return summary
    except Exception as e:
        return f"Search failed: {e}"
