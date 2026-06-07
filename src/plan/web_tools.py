from __future__ import annotations

import os
from typing import Any

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..agent.tracker import ActionTracker


def _clip(text: str, limit: int = 8000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


class FetchUrlArgs(BaseModel):
    url: str = Field(..., description="URL to fetch.")


class WebSearchArgs(BaseModel):
    query: str = Field(..., description="Search query.")
    limit: int = Field(5, ge=1, le=10, description="Maximum result count.")


def _firecrawl_app() -> Any:
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise RuntimeError("Set FIRECRAWL_API_KEY to use web_search or web_crawl.")
    try:
        from firecrawl import FirecrawlApp
    except ImportError as exc:
        raise RuntimeError("Install firecrawl-py to use Firecrawl tools.") from exc
    return FirecrawlApp(api_key=api_key)


def create_web_tools(tracker: ActionTracker) -> list[StructuredTool]:
    def fetch_url(url: str) -> str:
        response = httpx.get(url, follow_redirects=True, timeout=20)
        output = f"HTTP {response.status_code}\n\n{_clip(response.text, 16000)}"
        tracker.log(
            action_type="code_analysis",
            path=f"fetch:{url}",
            details={"after": output, "toolName": "fetch_url"},
            status="executed",
        )
        return output

    def web_search(query: str, limit: int = 5) -> str:
        app = _firecrawl_app()
        result = app.search(query, limit=limit)
        items = result.get("data") or result.get("web") or []
        lines: list[str] = []
        for index, item in enumerate(items[:limit], start=1):
            title = item.get("title") or "(untitled)"
            url = item.get("url") or ""
            snippet = item.get("description") or item.get("snippet") or ""
            lines.append(f"{index}. {title}\n   {url}\n   {snippet}")
        output = "\n\n".join(lines) or "(no result)"
        tracker.log(
            action_type="code_analysis",
            path=f"web_search:{query}",
            details={"after": output, "toolName": "web_search"},
            status="executed",
        )
        return _clip(output)

    def web_crawl(url: str) -> str:
        app = _firecrawl_app()
        result = app.scrape_url(url, params={"formats": ["markdown"]})
        markdown = result.get("markdown") or result.get("data", {}).get("markdown") or ""
        output = markdown or "(empty)"
        tracker.log(
            action_type="code_analysis",
            path=f"web_crawl:{url}",
            details={"after": _clip(output), "toolName": "web_crawl"},
            status="executed",
        )
        return _clip(output)

    return [
        StructuredTool.from_function(
            fetch_url,
            name="fetch_url",
            description="HTTP GET a URL and return response body.",
            args_schema=FetchUrlArgs,
        ),
        StructuredTool.from_function(
            web_search,
            name="web_search",
            description="Search the web using Firecrawl.",
            args_schema=WebSearchArgs,
        ),
        StructuredTool.from_function(
            web_crawl,
            name="web_crawl",
            description="Scrape a URL into Markdown using Firecrawl.",
            args_schema=FetchUrlArgs,
        ),
    ]
