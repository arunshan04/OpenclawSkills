"""
Skills Registry — LangChain Integration
========================================
Two approaches:

  Approach A: MCP adapter (uses the MCP protocol directly on port 8001)
              All registered tools appear automatically — no hardcoding.

  Approach B: REST API (dynamic tool generation from /skills endpoint)
              Reads skill definitions and builds LangChain tools on the fly.
              Works even without the MCP client library.

LLM provider (auto-detected at runtime):
  - Set OLLAMA_HOST to use a local/remote Ollama server (e.g. ngrok URL)
  - Set OLLAMA_MODEL to choose the model (default: llama3.2)
  - Falls back to Anthropic claude-opus-4-8 when OLLAMA_HOST is not set

Install:
    pip install langchain langchain-anthropic langchain-ollama langgraph
    pip install langchain-mcp-adapters          # only needed for Approach A
"""

import asyncio
import json
import os
import warnings
import requests as _requests
from typing import Any

warnings.filterwarnings("ignore", category=DeprecationWarning)  # suppress langgraph v1 migration warnings


REGISTRY_REST  = "http://localhost:8000"
REGISTRY_MCP   = "http://localhost:8001/mcp"


# ─────────────────────────────────────────────────────────────────────────────
# Model selection helper
# ─────────────────────────────────────────────────────────────────────────────

def get_model():
    """
    Return a LangChain chat model.
    Uses Ollama when OLLAMA_HOST is set, otherwise Anthropic.
    """
    ollama_host = os.getenv("OLLAMA_HOST", "").strip().rstrip("/")
    if ollama_host:
        from langchain_ollama import ChatOllama
        model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
        print(f"[model] Using Ollama  host={ollama_host}  model={model_name}")
        return ChatOllama(
            model=model_name,
            base_url=ollama_host,
            temperature=0,
            think=False,       # disable qwen3 chain-of-thought
            num_predict=4096,
        )
    else:
        from langchain_anthropic import ChatAnthropic
        print("[model] Using Anthropic claude-opus-4-8")
        return ChatAnthropic(model="claude-opus-4-8", temperature=0)


# ─────────────────────────────────────────────────────────────────────────────
# Approach A — MCP Adapter (auto-discovers all registered tools)
# ─────────────────────────────────────────────────────────────────────────────

async def run_agent_via_mcp(user_message: str):
    """Connect via the MCP protocol — every tool in the registry is available."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langgraph.prebuilt import create_react_agent

    async with MultiServerMCPClient({
        "skills_registry": {
            "url": REGISTRY_MCP,
            "transport": "streamable_http",
        }
    }) as client:
        tools = client.get_tools()
        print(f"[MCP] Loaded {len(tools)} tools: {[t.name for t in tools]}")

        model = get_model()
        agent = create_react_agent(model, tools)
        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": user_message}]
        })
        return result["messages"][-1].content


# ─────────────────────────────────────────────────────────────────────────────
# Approach B — REST API (no MCP library needed)
# ─────────────────────────────────────────────────────────────────────────────

def _execute_skill_tool(skill_id: str, tool_name: str, **kwargs) -> str:
    """Call the registry's tool execution endpoint."""
    r = _requests.post(
        f"{REGISTRY_REST}/skills/{skill_id}/tools/{tool_name}/execute",
        json={"params": kwargs},
        timeout=30,
    )
    if not r.ok:
        return f"Error {r.status_code}: {r.text}"
    return str(r.json().get("result", r.json()))


def build_langchain_tools(skill_names: list[str] | None = None):
    """
    Fetch skills from the registry and return a list of LangChain StructuredTool objects.

    Args:
        skill_names: Optional filter — only include these skill names.
                     Pass None to include all active skills.
    """
    from langchain_core.tools import StructuredTool
    from pydantic import create_model, Field

    skills = _requests.get(f"{REGISTRY_REST}/skills").json()
    lc_tools = []

    for skill in skills:
        if skill.get("status") != "active":
            continue
        if skill_names and skill["name"] not in skill_names:
            continue

        tools = skill.get("tools", [])
        if isinstance(tools, str):
            tools = json.loads(tools)

        for tool_def in tools:
            tool_name = tool_def.get("name", "")
            code       = tool_def.get("code", "")
            if not tool_name or not code:
                continue   # skip tools without an implementation

            # Build a Pydantic model from the tool's input_schema
            schema     = tool_def.get("input_schema") or {}
            properties = schema.get("properties", {})
            required   = set(schema.get("required", []))

            fields: dict[str, Any] = {}
            for param, info in properties.items():
                py_type = {"string": str, "integer": int, "number": float,
                           "boolean": bool}.get(info.get("type", "string"), str)
                default = ... if param in required else None
                fields[param] = (py_type, Field(default, description=info.get("description", "")))

            ArgsSchema = create_model(f"{tool_name}_schema", **fields) if fields else None

            _skill_id   = skill["id"]
            _tool_name  = tool_name

            def make_fn(sid, tname):
                def fn(**kwargs) -> str:
                    return _execute_skill_tool(sid, tname, **kwargs)
                fn.__name__ = tname
                return fn

            lc_tool = StructuredTool(
                name=tool_name,
                description=f"[{skill['name']}] {tool_def.get('description', '')}",
                func=make_fn(_skill_id, _tool_name),
                args_schema=ArgsSchema,
            )
            lc_tools.append(lc_tool)

    print(f"[REST] Built {len(lc_tools)} LangChain tools from registry")
    return lc_tools


def run_agent_via_rest(user_message: str, skill_names: list[str] | None = None):
    """Build tools from the registry REST API and run a LangChain agent."""
    from langgraph.prebuilt import create_react_agent

    tools = build_langchain_tools(skill_names)
    model = get_model()
    agent = create_react_agent(model, tools)
    result = agent.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })
    return result["messages"][-1].content


# ─────────────────────────────────────────────────────────────────────────────
# Approach B+ — Registry as a Tool Itself (meta-tool pattern)
# ─────────────────────────────────────────────────────────────────────────────

def build_registry_meta_tools():
    """
    Returns LangChain tools for the 4 built-in registry endpoints
    (list_skills, get_skill, search_skills, list_categories).
    The agent can use these to discover what's available.
    """
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel

    class SearchInput(BaseModel):
        query: str

    class GetInput(BaseModel):
        skill_id: str

    def list_skills_fn(category: str = "", status: str = "active") -> str:
        params = {"status": status}
        if category:
            params["category"] = category
        r = _requests.get(f"{REGISTRY_REST}/skills", params=params)
        skills = r.json()
        return "\n".join(f"- {s['name']} ({s['category']}): {s['description'][:80]}" for s in skills)

    def search_skills_fn(query: str) -> str:
        r = _requests.get(f"{REGISTRY_REST}/skills", params={"search": query})
        skills = r.json()
        if not skills:
            return f"No skills found matching '{query}'"
        return "\n".join(f"- {s['name']} (id={s['id']}): {s['description'][:80]}" for s in skills)

    def get_skill_fn(skill_id: str) -> str:
        r = _requests.get(f"{REGISTRY_REST}/skills/{skill_id}")
        if not r.ok:
            return f"Skill '{skill_id}' not found"
        s = r.json()
        tool_names = [t["name"] for t in s.get("tools", []) if isinstance(t, dict)]
        return f"{s['name']}: {s['description']}\nTools: {tool_names}\nCategory: {s['category']}"

    def list_categories_fn() -> str:
        r = _requests.get(f"{REGISTRY_REST}/skills/categories")
        cats = r.json()
        return ", ".join(f"{c['category']} ({c['count']})" for c in cats)

    return [
        StructuredTool.from_function(list_skills_fn,    name="list_skills",     description="List all available skills in the registry, optionally filter by category"),
        StructuredTool.from_function(search_skills_fn,  name="search_skills",   description="Search skills by name, description or tags", args_schema=SearchInput),
        StructuredTool.from_function(get_skill_fn,      name="get_skill",       description="Get details about a specific skill by ID", args_schema=GetInput),
        StructuredTool.from_function(list_categories_fn,name="list_categories", description="List all skill categories in the registry"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Example usage
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ollama_host = os.getenv("OLLAMA_HOST", "")
    if not ollama_host and not os.getenv("ANTHROPIC_API_KEY"):
        print("Set OLLAMA_HOST (for Ollama) or ANTHROPIC_API_KEY (for Anthropic) first")
        exit(1)

    print("=" * 60)
    print("Test 1: list_skills meta-tool — what's in the registry?")
    print("=" * 60)
    meta_tools = build_registry_meta_tools()
    model = get_model()
    from langgraph.prebuilt import create_react_agent  # noqa: PLC0415
    agent = create_react_agent(model, meta_tools)
    result = agent.invoke({"messages": [{"role": "user", "content":
        "List all skills in the registry and summarise what each one does in one line."}]})
    print("Answer:", result["messages"][-1].content)

    print("\n" + "=" * 60)
    print("Test 2: Unit conversion via REST skill tool")
    print("=" * 60)
    answer = run_agent_via_rest(
        "Convert 100 km to miles using the unit converter skill",
        skill_names=["Unit Converter"],
    )
    print("Answer:", answer)

    print("\n" + "=" * 60)
    print("Test 3: Weather via REST skill tool")
    print("=" * 60)
    answer = run_agent_via_rest(
        "What is the current weather in London?",
        skill_names=["Weather Forecast"],
    )
    print("Answer:", answer)
