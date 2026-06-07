from enum import Enum
from typing import Any, Dict, TypedDict

class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    PROJECT = "project"
    CONVERSATION = "conversation"
    TASK = "task"

class MemoryDocument(TypedDict):
    text: str
    type: MemoryType
    timestamp: str
    metadata: Dict[str, Any]
