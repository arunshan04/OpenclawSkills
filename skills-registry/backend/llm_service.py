import os
import json
import httpx
from models import LLMResearchResponse, ToolDef, PromptDef, ResourceDef

ICON_SUGGESTIONS = {
    "Research": "🔍", "Development": "💻", "Analytics": "📊", "Security": "🛡️",
    "Creative": "🎨", "Productivity": "📝", "Communication": "💬", "AI/ML": "🤖",
    "Data": "🗄️", "Cloud": "☁️", "Automation": "⚡", "General": "🔧",
    "Finance": "💰", "Education": "📚", "Healthcare": "🏥", "DevOps": "🚀"
}

COLOR_SUGGESTIONS = {
    "Research": "#3b82f6", "Development": "#10b981", "Analytics": "#f59e0b",
    "Security": "#ef4444", "Creative": "#ec4899", "Productivity": "#8b5cf6",
    "Communication": "#06b6d4", "AI/ML": "#6366f1", "Data": "#f97316",
    "Cloud": "#0ea5e9", "Automation": "#84cc16", "General": "#6b7280",
    "Finance": "#22c55e", "Education": "#a855f7", "Healthcare": "#14b8a6",
    "DevOps": "#f43f5e"
}

SYSTEM_PROMPT = """You are a Skills Registry architect. When given a skill requirement, you generate a comprehensive skill definition for an MCP (Model Context Protocol) registry.

A skill defines capabilities that an AI agent can use. Each skill has:
- Tools (functions the AI can call)
- Prompts (reusable prompt templates)
- Resources (data/files the AI can access)
- MCP configuration (how to connect to the MCP server)

Always return valid JSON matching the exact schema provided."""

USER_PROMPT_TEMPLATE = """Research and design a skill for the following requirement:

REQUIREMENT: {query}

{category_hint}

Existing skills in registry (avoid duplication):
{existing_list}

Return a JSON object with this EXACT structure:
{{
  "name": "Short descriptive name (2-4 words)",
  "description": "Detailed description (2-3 sentences) of what this skill does and its key benefits",
  "category": "One of: Research, Development, Analytics, Security, Creative, Productivity, Communication, AI/ML, Data, Cloud, Automation, DevOps, Finance, Education, Healthcare, General",
  "icon": "Single emoji that best represents this skill",
  "icon_bg_color": "Hex color code matching the category theme",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "tools": [
    {{
      "name": "tool_function_name",
      "description": "What this tool does",
      "input_schema": {{
        "type": "object",
        "properties": {{
          "param_name": {{"type": "string", "description": "Parameter description"}}
        }},
        "required": ["param_name"]
      }},
      "code": "def tool_function_name(param_name: str) -> str:\\n    # Implementation using only these available modules:\\n    # requests, json, re, math, datetime, uuid, os, pathlib, subprocess, shutil\\n    # No import statements needed — modules are pre-loaded\\n    result = f\\"Result for {{param_name}}\\"\\n    return result"
    }}
  ],
  "prompts": [
    {{
      "name": "prompt_name",
      "description": "What this prompt template is for",
      "template": "The actual prompt template with {{variables}}"
    }}
  ],
  "resources": [],
  "mcp_config": {{
    "transport": "stdio",
    "command": "python",
    "args": ["-m", "skill_module_name"]
  }},
  "rationale": "Brief explanation of design decisions and why this skill configuration makes sense",
  "metadata": {{
    "complexity": "low|medium|high",
    "use_cases": ["use case 1", "use case 2"]
  }}
}}

IMPORTANT for tools:
- Write REAL working Python code for each tool's "code" field
- The function name MUST exactly match the tool "name" field
- Do NOT use import statements — these modules are pre-loaded: requests, json, re, math, datetime, uuid, os, pathlib, subprocess, shutil
- Use requests for HTTP calls, pathlib for file ops, subprocess for shell commands
- Return a string result always
- Keep each function focused and complete (not pseudocode)

Generate 2-4 meaningful tools with real implementations and 0-2 prompts."""


def _extract_json(text: str) -> dict:
    """Extract and parse the first JSON object from a response string."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    # Some models prepend prose before the JSON object
    start = text.find("{")
    if start > 0:
        text = text[start:]
    return json.loads(text)


def _call_ollama(user_prompt: str) -> str:
    """Call Ollama's native /api/chat endpoint."""
    host = os.environ["OLLAMA_HOST"].rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        "stream": False,
        "think": False,          # disable qwen3 extended thinking
        "options": {
            "temperature": 0,
            "num_predict": 4096,
        },
    }

    with httpx.Client(timeout=300) as client:
        r = client.post(f"{host}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
        msg = data["message"]
        # When think=False the answer is in content; fall back to thinking if content is empty
        return msg.get("content") or msg.get("thinking", "")


def _call_deepseek(user_prompt: str) -> str:
    """Call DeepSeek API (OpenAI-compatible)."""
    from openai import OpenAI
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4096,
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def _call_anthropic(user_prompt: str) -> str:
    """Call Anthropic Claude API."""
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text.strip()


def _pick_provider(user_prompt: str) -> str:
    """Call the first configured LLM provider: Ollama → DeepSeek → Anthropic."""
    if os.getenv("OLLAMA_HOST", "").strip():
        return _call_ollama(user_prompt)
    if os.getenv("DEEPSEEK_API_KEY", "").strip():
        return _call_deepseek(user_prompt)
    return _call_anthropic(user_prompt)


def research_skill(query: str, category: str = None, existing_skills: list = None) -> LLMResearchResponse:
    existing_list = "\n".join(f"- {s}" for s in (existing_skills or []))
    category_hint = f"Preferred category: {category}" if category else ""

    user_prompt = USER_PROMPT_TEMPLATE.format(
        query=query,
        category_hint=category_hint,
        existing_list=existing_list if existing_list else "None",
    )

    response_text = _pick_provider(user_prompt)

    data = _extract_json(response_text)

    cat = data.get("category", "General")
    if not data.get("icon") or data["icon"] == "🔧":
        data["icon"] = ICON_SUGGESTIONS.get(cat, "🔧")
    if not data.get("icon_bg_color"):
        data["icon_bg_color"] = COLOR_SUGGESTIONS.get(cat, "#6366f1")

    return LLMResearchResponse(
        name=data["name"],
        description=data["description"],
        category=data.get("category", "General"),
        icon=data.get("icon", "🔧"),
        icon_bg_color=data.get("icon_bg_color", "#6366f1"),
        tags=data.get("tags", []),
        tools=[ToolDef(**t) for t in data.get("tools", [])],
        prompts=[PromptDef(**p) for p in data.get("prompts", [])],
        resources=[ResourceDef(**r) for r in data.get("resources", [])],
        mcp_config=data.get("mcp_config", {}),
        rationale=data.get("rationale", ""),
        metadata=data.get("metadata", {})
    )


_TOOL_SYSTEM_PROMPT = """You are an expert Python developer writing tool functions for an AI skill registry.
A tool is a single Python function that an AI agent can call. It must:
- Have a clear, snake_case function name
- Accept typed parameters
- Return a string result
- Use only pre-loaded modules: requests, json, re, math, datetime, uuid, os, pathlib, subprocess, shutil
- NOT use import statements (modules are pre-injected)
Always return valid JSON only."""

_TOOL_PROMPT = """Write a single tool function for the following requirement:

REQUIREMENT: {prompt}

Return a JSON object with this EXACT structure:
{{
  "name": "snake_case_function_name",
  "description": "One sentence describing what this tool does",
  "input_schema": {{
    "type": "object",
    "properties": {{
      "param_name": {{"type": "string", "description": "what this param is"}}
    }},
    "required": ["param_name"]
  }},
  "code": "def snake_case_function_name(param_name: str) -> str:\\n    # implementation\\n    return result"
}}

Rules for the code:
- Function name MUST match the "name" field exactly
- No import statements — modules are pre-loaded: requests, json, re, math, datetime, uuid, os, pathlib
- Always return a string
- Write real, working code (not pseudocode)"""


def research_tool(prompt: str) -> dict:
    """Generate a single ToolDef dict from a plain-English prompt."""
    user_prompt = _TOOL_PROMPT.format(prompt=prompt)

    ollama_host = os.getenv("OLLAMA_HOST", "").strip()
    if ollama_host:
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        host = ollama_host.rstrip("/")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _TOOL_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_predict": 2048},
        }
        with httpx.Client(timeout=300) as c:
            r = c.post(f"{host}/api/chat", json=payload)
            r.raise_for_status()
            msg = r.json()["message"]
            response_text = msg.get("content") or msg.get("thinking", "")
    elif os.getenv("DEEPSEEK_API_KEY", "").strip():
        from openai import OpenAI
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _TOOL_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=2048,
            temperature=0,
        )
        response_text = response.choices[0].message.content.strip()
    else:
        import anthropic as _ant
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("No LLM provider configured. Set DEEPSEEK_API_KEY, OLLAMA_HOST, or ANTHROPIC_API_KEY.")
        client = _ant.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            system=_TOOL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        response_text = message.content[0].text.strip()

    return _extract_json(response_text)
