"""
Skills Registry — LangChain Chat Agent
========================================
Interactive CLI agent backed by all tools registered in the Skills Registry.

Usage:
    python langchain_integration.py [options]

Options:
    --registry URL      Registry REST base URL (default: http://localhost:8000)
    --skills NAME ...   Only load tools from these skill names
    --meta              Also include registry meta-tools (list_skills, search_skills …)
    --verbose           Show tool calls and results as they happen

LLM provider (auto-detected):
    OLLAMA_HOST set  →  ChatOllama (OLLAMA_MODEL, default llama3.2)
    OLLAMA_HOST unset →  ChatAnthropic (ANTHROPIC_API_KEY required)

Install:
    pip install langchain langchain-anthropic langchain-ollama langgraph requests
"""

import json
import os
import sys
import textwrap
import warnings
import argparse
import requests as _requests
from typing import Any

warnings.filterwarnings("ignore", category=DeprecationWarning)

# populated from --registry arg (or default)
REGISTRY_REST = "http://localhost:8000"
REGISTRY_MCP  = "http://localhost:8001/mcp"


# ─────────────────────────────────────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────────────────────────────────────

def get_model():
    """Return ChatOllama when OLLAMA_HOST is set, otherwise ChatAnthropic."""
    ollama_host = os.getenv("OLLAMA_HOST", "").strip().rstrip("/")
    if ollama_host:
        from langchain_ollama import ChatOllama
        model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
        return ChatOllama(
            model=model_name,
            base_url=ollama_host,
            temperature=0,
            think=False,
            num_predict=4096,
        ), f"ollama/{model_name}"
    else:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-opus-4-8", temperature=0), "anthropic/claude-opus-4-8"


# ─────────────────────────────────────────────────────────────────────────────
# Tool builders
# ─────────────────────────────────────────────────────────────────────────────

def _execute_skill_tool(skill_id: str, tool_name: str, **kwargs) -> str:
    r = _requests.post(
        f"{REGISTRY_REST}/skills/{skill_id}/tools/{tool_name}/execute",
        json={"params": kwargs},
        timeout=30,
    )
    if not r.ok:
        return f"Error {r.status_code}: {r.text}"
    return str(r.json().get("result", r.json()))


def build_langchain_tools(skill_names: list[str] | None = None):
    """Fetch active skills from the registry and return LangChain StructuredTool objects."""
    from langchain_core.tools import StructuredTool
    from pydantic import create_model, Field

    try:
        skills = _requests.get(f"{REGISTRY_REST}/skills", timeout=5).json()
    except Exception as e:
        print(f"[error] Cannot reach registry at {REGISTRY_REST}: {e}")
        return []

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
            if not tool_name or not (tool_def.get("code") or "").strip():
                continue

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

            def make_fn(sid, tname):
                def fn(**kwargs) -> str:
                    return _execute_skill_tool(sid, tname, **kwargs)
                fn.__name__ = tname
                return fn

            lc_tools.append(StructuredTool(
                name=tool_name,
                description=f"[{skill['name']}] {tool_def.get('description', '')}",
                func=make_fn(skill["id"], tool_name),
                args_schema=ArgsSchema,
            ))

    return lc_tools


def build_registry_meta_tools():
    """Registry discovery tools: list_skills, search_skills, get_skill, list_categories."""
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
# Chat agent
# ─────────────────────────────────────────────────────────────────────────────

def _wrap(text: str, width: int = 88, indent: str = "") -> str:
    return textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)


_META_TOOL_NAMES = {"list_skills", "search_skills", "get_skill", "list_categories"}


def run_chat(tools: list, model, model_label: str, verbose: bool = False):
    from langgraph.prebuilt import create_react_agent
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

    agent = create_react_agent(model, tools)
    history: list = []

    meta   = [t for t in tools if t.name in _META_TOOL_NAMES]
    skill  = [t for t in tools if t.name not in _META_TOOL_NAMES]

    print()
    print("─" * 60)
    print("  Skills Registry Chat Agent")
    print(f"  Model  : {model_label}")
    if meta:
        print(f"  Skills : {', '.join(t.name for t in meta)}")
    if skill:
        print(f"  Tools  : {', '.join(t.name for t in skill)}")
    print("─" * 60)
    print("  Type your message and press Enter.")
    print("  Commands: /tools  /clear  /quit")
    print("─" * 60)
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue

        # Built-in commands
        if user_input.lower() in ("/quit", "/exit", "/bye", "quit", "exit"):
            print("Bye!")
            break
        if user_input.lower() == "/clear":
            history.clear()
            print("[history cleared]\n")
            continue
        if user_input.lower() == "/tools":
            if meta:
                print("\nRegistry (skill discovery):")
                for t in meta:
                    print(f"  • {t.name}: {t.description[:80]}")
            if skill:
                print("\nSkill tools (callable):")
                for t in skill:
                    print(f"  • {t.name}: {t.description[:80]}")
            print()
            continue

        history.append(HumanMessage(content=user_input))

        print("\nAgent: ", end="", flush=True)
        try:
            for chunk in agent.stream({"messages": history}):
                # Each chunk is a dict keyed by node name
                for node, state in chunk.items():
                    messages = state.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            if msg.tool_calls and verbose:
                                for tc in msg.tool_calls:
                                    args_str = json.dumps(tc["args"], ensure_ascii=False)
                                    print(f"\n  🔧 {tc['name']}({args_str})", flush=True)
                            elif msg.content:
                                # Final answer — print it
                                answer = msg.content if isinstance(msg.content, str) else str(msg.content)
                                print(answer, flush=True)
                                history.append(msg)

                        elif isinstance(msg, ToolMessage) and verbose:
                            result_preview = str(msg.content)[:120].replace("\n", " ")
                            print(f"  ✓ {result_preview}", flush=True)

        except Exception as e:
            print(f"[error] {e}", flush=True)

        print()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Skills Registry interactive chat agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              python langchain_integration.py
              python langchain_integration.py --verbose
              python langchain_integration.py --skills "Unit Converter" "Weather Forecast"
              python langchain_integration.py --no-meta
              OLLAMA_HOST=http://localhost:11434 python langchain_integration.py
        """),
    )
    parser.add_argument("--registry", default="http://localhost:8000",
                        help="Registry REST base URL (default: http://localhost:8000)")
    parser.add_argument("--skills", nargs="*", metavar="NAME",
                        help="Only load tools from these skill names (default: all)")
    parser.add_argument("--no-meta", action="store_true",
                        help="Exclude registry discovery tools (list_skills, search_skills, …)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show tool calls and results in real time")
    args = parser.parse_args()

    # Apply registry URL
    REGISTRY_REST = args.registry.rstrip("/")

    # Check LLM provider
    ollama_host = os.getenv("OLLAMA_HOST", "").strip()
    if not ollama_host and not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: set OLLAMA_HOST (Ollama) or ANTHROPIC_API_KEY (Anthropic) first.")
        sys.exit(1)

    # Always include registry meta-tools so the agent knows what skills exist
    # and can search/discover capabilities dynamically.
    # Use --no-meta to skip them (e.g. when skill tools already cover everything).
    skill_tools = build_langchain_tools(args.skills)
    meta_tools  = [] if args.no_meta else build_registry_meta_tools()
    tools = meta_tools + skill_tools

    if not tools:
        print("No tools loaded. Add some skills via the dashboard first.")
        sys.exit(1)

    model, model_label = get_model()
    run_chat(tools, model, model_label, verbose=args.verbose)
