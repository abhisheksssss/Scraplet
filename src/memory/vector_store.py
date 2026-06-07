import os
import requests
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from typing import List

from ..config import workspace_root

class JinaEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str = None):
        # Fallback to the specific key provided by the user if none in environment
        self.api_key = api_key or os.getenv("JINA_API_KEY", "jina_8773cae1b02f418bbbf0c3a463d2995bhArTdsjwEovxdgnDqP91NFCIDPk6")
        if not self.api_key:
            raise ValueError("JINA_API_KEY is not set.")
        self.api_url = "https://api.jina.ai/v1/embeddings"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def name(self) -> str:
        return "jina-embeddings-v5-text-small"

    def __call__(self, input: Documents) -> Embeddings:
        # ChromaDB may pass empty lists
        if not input:
            return []
            
        data = {
            "model": "jina-embeddings-v5-text-small",
            "task": "retrieval.query",
            "normalized": True,
            "input": input
        }
        response = requests.post(self.api_url, headers=self.headers, json=data)
        response.raise_for_status()
        result = response.json()
        return [item["embedding"] for item in result["data"]]


class VectorStore:
    def __init__(self):
        self.db_path = workspace_root() / ".scraplet" / "chroma"
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.embedding_fn = JinaEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name="scraplet_memories",
            embedding_function=self.embedding_fn
        )

    def add_memories(self, texts: List[str], metadatas: List[dict], ids: List[str]) -> None:
        if not texts:
            return
        self.collection.upsert(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query_text: str, n_results: int = 5) -> dict:
        count = self.collection.count()
        if count == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
            
        n_results = min(n_results, count)
        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
