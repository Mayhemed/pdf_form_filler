# models.py

from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class FormField:
    """Represents a single fillable field from a PDF form."""
    name: str = ""
    type: str = "Text"
    alttext: str = ""
    flags: int = 0
    justification: str = "Left"
    state_options: List[str] = field(default_factory=list)

@dataclass
class DataSource:
    """Represents a data source for AI extraction (file, text, etc.)."""
    name: str
    source_type: str
    content: str