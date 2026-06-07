import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List

import json
from langchain_core.messages import HumanMessage, AIMessage

from ..llm import get_model
from ..config import workspace_root
from .vector_store import VectorStore
from .types import MemoryType

class ExtractedMemory(BaseModel):
    memory: str = Field(description="The memory text to retain")
    type: MemoryType = Field(description="The category of the memory")

class MemoryExtraction(BaseModel):
    memories: List[ExtractedMemory]

class MemoryManager:
    def __init__(self):
        self.vector_store = VectorStore()
        self.history_file = workspace_root() / ".scraplet" / "short_term_history.json"

    def get_short_term_history(self, limit: int = 10) -> list:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            
            messages = []
            # Keep only the last `limit` pairs (so limit*2 messages)
            for msg in history[-limit*2:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            return messages
        except Exception as e:
            print(f"Failed to load short-term history: {e}")
            return []

    def add_short_term_history(self, user_content: str, ai_content: str):
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass
        
        history.append({"role": "user", "content": user_content})
        history.append({"role": "assistant", "content": ai_content})
        
        # Keep last 20 interactions (40 messages) to prevent huge files
        history = history[-40:]
        
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Failed to save short-term history: {e}")

    def extract_and_store(self, goal: str, result_text: str):
        llm = get_model(temperature=0)
        
        system_prompt = (
            "You are a memory extraction agent. Your job is to extract long-term useful facts, preferences, "
            "and project details from the conversation. Only extract information that would be useful for "
            "future interactions. Do not extract transient thoughts or temporary code changes.\n\n"
            "Categories:\n"
            "- fact: General immutable facts.\n"
            "- preference: User preferences (e.g. languages, tools).\n"
            "- project: Context about the current or past projects.\n"
            "- conversation: High level summaries of what was discussed.\n"
            "- task: High level tasks the user requested.\n"
        )
        
        user_prompt = f"Conversation:\nUser: {goal}\nAssistant: {result_text}\n\nExtract memories."
        
        structured_llm = llm.with_structured_output(MemoryExtraction)
        
        try:
            extraction = structured_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            if not extraction.memories:
                return
                
            texts = []
            metadatas = []
            ids = []
            
            timestamp = datetime.now().isoformat()
            
            for mem in extraction.memories:
                texts.append(mem.memory)
                metadatas.append({
                    "type": mem.type.value,
                    "timestamp": timestamp
                })
                ids.append(f"mem_{uuid.uuid4().hex}")
                
            self.vector_store.add_memories(texts, metadatas, ids)
            
        except Exception as e:
            print(f"Memory extraction failed: {e}")

    def retrieve_relevant_context(self, query: str) -> str:
        results = self.vector_store.query(query, n_results=5)
        
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        if not documents:
            return ""
            
        formatted_memories = []
        for doc, meta in zip(documents, metadatas):
            mem_type = meta.get("type", "unknown").upper()
            formatted_memories.append(f"{mem_type}: {doc}")
            
        context = "Relevant Memories:\n" + "\n".join(formatted_memories)
        return context
