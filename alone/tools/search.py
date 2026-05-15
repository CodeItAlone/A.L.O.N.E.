import yaml
from ddgs import DDGS
from langchain_ollama import ChatOllama
from langchain.tools import tool

def _get_llm():
    config_path = "config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return ChatOllama(model=config["model"], base_url=config["model_url"])

@tool
def search_web(query: str) -> str:
    """Searches the web using DuckDuckGo and returns a summary of the top 5 results."""
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
        return response.content
    except Exception as e:
        return f"Search failed: {e}"
