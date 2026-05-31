from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ToolDef(BaseModel):
    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    code: Optional[str] = None
    source_file: Optional[str] = None   # path to a .py file on disk
    source_url: Optional[str] = None    # HTTP endpoint to delegate execution to


class PromptDef(BaseModel):
    name: str
    description: str
    template: Optional[str] = None


class ResourceDef(BaseModel):
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


class SkillCreate(BaseModel):
    name: str
    description: str
    category: str = "General"
    icon: str = "🔧"
    icon_bg_color: str = "#6366f1"
    tags: List[str] = []
    version: str = "1.0.0"
    author: str = "Unknown"
    status: str = "active"
    tools: List[ToolDef] = []
    prompts: List[PromptDef] = []
    resources: List[ResourceDef] = []
    mcp_config: Dict[str, Any] = {}
    source: str = "manual"
    metadata: Dict[str, Any] = {}


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    icon_bg_color: Optional[str] = None
    tags: Optional[List[str]] = None
    version: Optional[str] = None
    author: Optional[str] = None
    status: Optional[str] = None
    tools: Optional[List[ToolDef]] = None
    prompts: Optional[List[PromptDef]] = None
    resources: Optional[List[ResourceDef]] = None
    mcp_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMResearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    existing_skills: Optional[List[str]] = []


class LLMResearchResponse(BaseModel):
    name: str
    description: str
    category: str
    icon: str
    icon_bg_color: str
    tags: List[str]
    tools: List[ToolDef]
    prompts: List[PromptDef]
    resources: List[ResourceDef]
    mcp_config: Dict[str, Any]
    rationale: str
    metadata: Dict[str, Any] = {}
