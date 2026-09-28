import json
import re
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup


def web_search(query: str, max_results: int = 4) -> str:
    """
    Searches the live web and returns top results with titles, links, and snippets.
    Equipped with an internal 5s timeout and automatic fallback.
    """
    # 1. Primary Engine: DuckDuckGo Search package with a strict 5s ceiling
    try:
        from duckduckgo_search import DDGS
        with DDGS(timeout=5) as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))

        if raw_results:
            formatted = [f"Web Search Results for '{query}':"]
            for idx, r in enumerate(raw_results, 1):
                title = r.get("title", "Untitled")
                href = r.get("href", "")
                snippet = r.get("body", "")
                formatted.append(f"{idx}. {title}\n   URL: {href}\n   Snippet: {snippet}")
            return "\n\n".join(formatted)
    except Exception as e:
        print(f"[SEARCH NOTICE] Primary search endpoint notice: {e}")

    # 2. Resilient Zero-Dependency Fallback: DuckDuckGo Instant Answer API
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        topics = []
        if data.get("AbstractText"):
            topics.append(f"1. {data.get('Heading', 'Summary')}\n   Snippet: {data.get('AbstractText')}\n   URL: {data.get('AbstractURL', '')}")

        for r in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(r, dict) and r.get("Text"):
                topics.append(f"- {r.get('Text')}\n  URL: {r.get('FirstURL', '')}")

        if topics:
            return f"Web Search Results for '{query}':\n\n" + "\n\n".join(topics)
    except Exception:
        pass

    return f"Unable to fetch real-time web results for '{query}'. Please synthesize an accurate summary using your internal knowledge base."


def read_web_page(url: str, max_chars: int = 2000) -> str:
    """Visits a webpage URL and extracts clean readable text, stripping ads and HTML."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode("utf-8", errors="ignore")

        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
            element.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars] if text else "Webpage contained no readable text."
    except Exception as e:
        return f"Failed to extract webpage content: {e}"