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


def create_web_tools(tracker: ActionTracker) -> list[StructuredTool]:
    def fetch_url(url: str) -> str:
        try:
            response = httpx.get(url, follow_redirects=True, timeout=20)
            output = f"HTTP {response.status_code}\n\n{_clip(response.text, 16000)}"
        except Exception as e:
            output = f"ERROR: {e}"
        
        tracker.log(
            action_type="code_analysis",
            path=f"fetch:{url}",
            details={"after": output, "toolName": "fetch_url"},
            status="executed",
        )
        return output

    def browser_fetch_url(url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
            from bs4 import BeautifulSoup
        except ImportError:
            return "ERROR: Install playwright and beautifulsoup4"
            
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Wait 2 seconds for client-side JavaScript frameworks to render
                page.wait_for_timeout(2000)
                
                html = page.content()
                browser.close()
                
            soup = BeautifulSoup(html, "html.parser")
            for script in soup(["script", "style", "noscript", "svg", "img", "nav", "footer"]):
                script.extract()
            
            text = soup.get_text(separator="\n")
            lines = (line.strip() for line in text.splitlines())
            output = "\n".join(chunk for chunk in lines if chunk)
            output = _clip(output, 20000)
            
        except Exception as e:
            output = f"ERROR: Playwright failed to fetch URL: {e}"

        tracker.log(
            action_type="code_analysis",
            path=f"browser_fetch:{url}",
            details={"after": output, "toolName": "browser_fetch_url"},
            status="executed",
        )
        return output

    def web_search(query: str, limit: int = 5) -> str:
        try:
            from ddgs import DDGS
        except ImportError:
            return "ERROR: Install ddgs"
            
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=limit))
                
            if not results:
                output = "(no results found)"
            else:
                lines = []
                for index, item in enumerate(results, start=1):
                    title = item.get("title") or "(untitled)"
                    url = item.get("href") or ""
                    snippet = item.get("body") or ""
                    lines.append(f"{index}. {title}\n   URL: {url}\n   {snippet}")
                output = "\n\n".join(lines)
        except Exception as e:
            output = f"ERROR: Search failed: {e}"

        tracker.log(
            action_type="code_analysis",
            path=f"web_search:{query}",
            details={"after": output, "toolName": "web_search"},
            status="executed",
        )
        return _clip(output)

    return [
        StructuredTool.from_function(
            fetch_url,
            name="fetch_url",
            description="HTTP GET a URL and return raw response body. Extremely fast but fails on JS-rendered sites.",
            args_schema=FetchUrlArgs,
        ),
        StructuredTool.from_function(
            browser_fetch_url,
            name="browser_fetch_url",
            description="Open a headless Chromium browser, load a URL, wait for JS to render, and return the stripped text content. Slower but works perfectly on dynamic sites.",
            args_schema=FetchUrlArgs,
        ),
        StructuredTool.from_function(
            web_search,
            name="web_search",
            description="Search the internet completely free using DuckDuckGo.",
            args_schema=WebSearchArgs,
        ),
    ]
