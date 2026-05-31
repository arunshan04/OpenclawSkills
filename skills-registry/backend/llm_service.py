import os
import json
import anthropic
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


def research_skill(query: str, category: str = None, existing_skills: list = None) -> LLMResearchResponse:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    existing_list = "\n".join(f"- {s}" for s in (existing_skills or []))
    category_hint = f"Preferred category: {category}" if category else ""

    system_prompt = """You are a Skills Registry architect. When given a skill requirement, you generate a comprehensive skill definition for an MCP (Model Context Protocol) registry.

A skill defines capabilities that an AI agent can use. Each skill has:
- Tools (functions the AI can call)
- Prompts (reusable prompt templates)
- Resources (data/files the AI can access)
- MCP configuration (how to connect to the MCP server)

Always return valid JSON matching the exact schema provided."""

    user_prompt = f"""Research and design a skill for the following requirement:

REQUIREMENT: {query}

{category_hint}

Existing skills in registry (avoid duplication):
{existing_list if existing_list else "None"}

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
      }}
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

Generate 2-4 meaningful tools and 0-2 prompts. Make tool schemas realistic and useful."""

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    response_text = message.content[0].text.strip()

    # Extract JSON from response
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    data = json.loads(response_text)

    # Ensure icon and color are sensible
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
