"""
Skills Registry — LangChain Integration
========================================
Two approaches:

  Approach A: MCP adapter (uses the MCP protocol directly on port 8001)
              All registered tools appear automatically — no hardcoding.

  Approach B: REST API (dynamic tool generation from /skills endpoint)
              Reads skill definitions and builds LangChain tools on the fly.
              Works even without the MCP client library.

Install:
    pip install langchain langchain-anthropic langgraph
    pip install langchain-mcp-adapters          # only needed for Approach A
"""

import asyncio
import json
import requests as _requests
from typing import Any

REGISTRY_REST  = "http://localhost:8000"
REGISTRY_MCP   = "http://localhost:8001/mcp"


# ─────────────────────────────────────────────────────────────────────────────
# Approach A — MCP Adapter (auto-discovers all registered tools)
# ─────────────────────────────────────────────────────────────────────────────

async def run_agent_via_mcp(user_message: str):
    """Connect via the MCP protocol — every tool in the registry is available."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langgraph.prebuilt import create_react_agent
    from langchain_anthropic import ChatAnthropic

    async with MultiServerMCPClient({
        "skills_registry": {
            "url": REGISTRY_MCP,
            "transport": "streamable_http",
        }
    }) as client:
        tools = client.get_tools()
        print(f"[MCP] Loaded {len(tools)} tools: {[t.name for t in tools]}")

        model = ChatAnthropic(model="claude-opus-4-8", temperature=0)
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
    from langchain.tools import StructuredTool
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

            # Capture loop variables
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


def run_agent_via_rest(user_message: str):
    """Build tools from the registry REST API and run a LangChain agent."""
    from langgraph.prebuilt import create_react_agent
    from langchain_anthropic import ChatAnthropic

    tools = build_langchain_tools()   # pass skill_names=["Web Search"] to filter

    model = ChatAnthropic(model="claude-opus-4-8", temperature=0)
    agent = create_react_agent(model, tools)
    result = agent.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })
    return result["messages"][-1].content


# ─────────────────────────────────────────────────────────────────────────────
# Approach B+ — Registry as a Tool Itself (meta-tool pattern)
# ─────────────────────────────────────────────────────────────────────────────
# Give the agent access to the REGISTRY tools (list_skills, search_skills, etc.)
# so it can discover and reason about available capabilities dynamically.

def build_registry_meta_tools():
    """
    Returns LangChain tools for the 4 built-in registry MCP tools
    (list_skills, get_skill, search_skills, list_categories).
    The agent can use these to discover what's available.
    """
    from langchain.tools import StructuredTool
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
        tools = s.get("tools", [])
        tool_names = [t["name"] for t in tools if isinstance(t, dict)]
        return f"{s['name']}: {s['description']}\nTools: {tool_names}\nCategory: {s['category']}"

    def list_categories_fn() -> str:
        r = _requests.get(f"{REGISTRY_REST}/skills/categories")
        cats = r.json()
        return ", ".join(f"{c['category']} ({c['count']})" for c in cats)

    return [
        StructuredTool.from_function(list_skills_fn,   name="list_skills",    description="List all available skills in the registry, optionally filter by category"),
        StructuredTool.from_function(search_skills_fn,  name="search_skills",  description="Search skills by name, description or tags", args_schema=SearchInput),
        StructuredTool.from_function(get_skill_fn,      name="get_skill",      description="Get details about a specific skill by ID", args_schema=GetInput),
        StructuredTool.from_function(list_categories_fn,name="list_categories",description="List all skill categories in the registry"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Example usage
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    # Make sure ANTHROPIC_API_KEY is set
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY env var first")
        exit(1)

    print("=" * 60)
    print("Option 1: Registry tools + skill tools together (REST)")
    print("=" * 60)
    all_tools = build_registry_meta_tools() + build_langchain_tools()
    print(f"Total tools: {len(all_tools)} → {[t.name for t in all_tools]}")

    answer = run_agent_via_rest("Search the web for latest Python 3.13 features")
    print("\nAgent answer:", answer)

    print("\n" + "=" * 60)
    print("Option 2: Via MCP protocol (auto-discovers all tools)")
    print("=" * 60)
    answer = asyncio.run(run_agent_via_mcp("List all skills in the registry"))
    print("\nAgent answer:", answer)
