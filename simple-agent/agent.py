"""A small conversational agent: persistent memory, SQLite conversations,
markdown skills, DeepSeek as the LLM backend, and dynamic tool/skill loading.

Loosely modeled on the Hermes Agent architecture, scaled down to one class:
    - Memory     -> memory.json     (durable key/value facts, in the system prompt)
    - Skills     -> skills/*.md     (description + procedure; full body is loaded
                                      on demand via the `load_skill` tool)
    - Sessions   -> conversations.db (SQLite, full message history per session_id)
    - LLM        -> DeepSeek's OpenAI-compatible Chat Completions API

Tool/skill discovery (kept OUT of the system prompt to save tokens):
    - `search_tools(query)`  -> finds matching tools; matches become callable
                                 on the model's next turn (added to the active
                                 tool list).
    - `search_skills(query)` -> finds matching skills (name + description).
    - `load_skill(name)`     -> returns a skill's full instructions on demand.

These three "discovery" tools are always available; everything else (get_time,
calculator, remember, recall, ...) is hidden until search_tools surfaces it.

DeepSeek setup:
    export DEEPSEEK_API_KEY="sk-..."
    # optional overrides:
    export DEEPSEEK_BASE_URL="https://api.deepseek.com"
    export DEEPSEEK_MODEL="deepseek-chat"

Without an API key the agent runs in a simple offline mode (keyword matching
against memory and skills, no tool calling) so the rest of the class can be
exercised without network access.
"""

from __future__ import annotations

import ast
import json
import operator
import os
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
HISTORY_LIMIT = 20  # most recent messages sent to the LLM as context
MAX_TOOL_ITERATIONS = 6  # safety cap on tool-call round trips per turn

# ----------------------------------------------------------------------
# Tool definitions
#
# DISCOVERY_TOOL_DEFS are always visible to the model. TOOL_DEFS are
# "hidden" tools that only become callable once search_tools surfaces them.
# ----------------------------------------------------------------------
DISCOVERY_TOOL_DEFS = {
    "search_tools": {
        "description": "Search available tools by keyword. Matching tools become "
                        "callable on your next turn.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Keyword(s) describing what you need to do"}},
            "required": ["query"],
        },
    },
    "search_skills": {
        "description": "Search available skills by keyword. Returns matching skill names and short descriptions.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Keyword(s) describing the task"}},
            "required": ["query"],
        },
    },
    "load_skill": {
        "description": "Load the full instructions for a skill by name (use after search_skills).",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Skill name as returned by search_skills"}},
            "required": ["name"],
        },
    },
}

TOOL_DEFS = {
    "get_time": {
        "description": "Get the current date and time.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "calculator": {
        "description": "Evaluate a basic arithmetic expression (+, -, *, /, **, parentheses).",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "e.g. '(3 + 4) * 2'"}},
            "required": ["expression"],
        },
    },
    "remember": {
        "description": "Save a durable fact to persistent memory as a key/value pair.",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}, "value": {"type": "string"}},
            "required": ["key", "value"],
        },
    },
    "recall": {
        "description": "Look up a previously remembered fact by key.",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
}

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"unsupported expression: {ast.dump(node)}")


class Agent:
    """A conversational agent with memory, SQLite-backed sessions, dynamically-loaded tools/skills, and DeepSeek as the LLM."""

    def __init__(
        self,
        name: str,
        home: str | Path = "./agent_home",
        skills_dir: Optional[str | Path] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        verbose: bool = True,
    ):
        self.name = name
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

        # ---- Memory ----
        self.memory_path = self.home / "memory.json"
        self.memory: dict[str, str] = self._load_memory()

        # ---- Skills (bundled alongside this file by default) ----
        self.skills_dir = Path(skills_dir) if skills_dir else Path(__file__).parent / "skills"
        self.skills: dict[str, dict[str, str]] = self._load_skills()

        # ---- Conversations ----
        self.db = sqlite3.connect(self.home / "conversations.db", check_same_thread=False)
        self._init_db()

        # ---- LLM (DeepSeek, OpenAI-compatible) ----
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = base_url or os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
        self.model = model or os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL)
        self._client = None  # lazily created — see _llm_client()

        # ---- Tool registry ----
        self.tools: dict[str, dict] = self._build_tool_registry()

    # ------------------------------------------------------------------
    # Memory — durable key/value facts persisted to memory.json
    # ------------------------------------------------------------------
    def _load_memory(self) -> dict[str, str]:
        if self.memory_path.exists():
            return json.loads(self.memory_path.read_text())
        return {}

    def _save_memory(self) -> None:
        self.memory_path.write_text(json.dumps(self.memory, indent=2))

    def remember(self, key: str, value: str) -> None:
        self.memory[key] = value
        self._save_memory()

    def recall(self, key: str) -> Optional[str]:
        return self.memory.get(key)

    def forget(self, key: str) -> None:
        if self.memory.pop(key, None) is not None:
            self._save_memory()

    # ------------------------------------------------------------------
    # Conversations — every message logged to SQLite, grouped by session
    # ------------------------------------------------------------------
    def _init_db(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id, id)"
        )
        self.db.commit()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        self.db.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, time.time()),
        )
        self.db.commit()

    def get_history(self, session_id: str, limit: Optional[int] = None) -> list[dict]:
        query = "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id"
        rows = self.db.execute(query, (session_id,)).fetchall()
        history = [{"role": role, "content": content, "created_at": ts} for role, content, ts in rows]
        return history[-limit:] if limit else history

    # ------------------------------------------------------------------
    # Skills — markdown files with a `description:` front-matter field.
    # Only name + description are ever shown to the model; the full body
    # is fetched on demand via the `load_skill` tool.
    # ------------------------------------------------------------------
    def _load_skills(self) -> dict[str, dict[str, str]]:
        skills = {}
        for path in sorted(self.skills_dir.glob("*.md")):
            text = path.read_text()
            skills[path.stem] = {"description": self._extract_description(text), "body": text}
        return skills

    @staticmethod
    def _extract_description(text: str) -> str:
        match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
        return ""

    def list_skills(self) -> list[str]:
        return sorted(self.skills)

    def use_skill(self, name: str) -> Optional[str]:
        skill = self.skills.get(name)
        return skill["body"] if skill else None

    def _match_skill(self, message: str) -> Optional[str]:
        """Best-effort name match used only by the offline fallback."""
        lowered = message.lower()
        for name in self.skills:
            if name.lower() in lowered or name.replace("_", " ").lower() in lowered:
                return name
        return None

    # ------------------------------------------------------------------
    # Tool registry — schemas + handlers. search_tools/search_skills/
    # load_skill are always active; everything else starts hidden.
    # ------------------------------------------------------------------
    def _build_tool_registry(self) -> dict[str, dict]:
        handlers = {
            "search_tools": self._tool_search_tools,
            "search_skills": self._tool_search_skills,
            "load_skill": self._tool_load_skill,
            "get_time": self._tool_get_time,
            "calculator": self._tool_calculator,
            "remember": self._tool_remember,
            "recall": self._tool_recall,
        }
        registry = {}
        for tool_name, spec in {**DISCOVERY_TOOL_DEFS, **TOOL_DEFS}.items():
            registry[tool_name] = {
                "schema": {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": spec["description"],
                        "parameters": spec["parameters"],
                    },
                },
                "handler": handlers[tool_name],
            }
        return registry

    @property
    def discovery_tools(self) -> list[str]:
        return list(DISCOVERY_TOOL_DEFS)

    def _tool_search_tools(self, query: str = "") -> str:
        query_lower = query.lower()
        matches = [
            self.tools[name]["schema"]["function"]
            for name, spec in TOOL_DEFS.items()
            if not query_lower or query_lower in f"{name} {spec['description']}".lower()
        ]
        return json.dumps({"matches": matches})

    def _tool_search_skills(self, query: str = "") -> str:
        query_lower = query.lower()
        matches = [
            {"name": name, "description": meta["description"]}
            for name, meta in self.skills.items()
            if not query_lower or query_lower in f"{name} {meta['description']}".lower()
        ]
        return json.dumps({"matches": matches})

    def _tool_load_skill(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            return json.dumps({"error": f"no skill named '{name}'", "available": self.list_skills()})
        return json.dumps({"name": name, "instructions": skill["body"]})

    def _tool_get_time(self) -> str:
        return json.dumps({"now": datetime.now().isoformat()})

    def _tool_calculator(self, expression: str) -> str:
        try:
            result = _safe_eval(ast.parse(expression, mode="eval").body)
            return json.dumps({"expression": expression, "result": result})
        except Exception as exc:
            return json.dumps({"expression": expression, "error": str(exc)})

    def _tool_remember(self, key: str, value: str) -> str:
        self.remember(key, value)
        return json.dumps({"saved": {key: value}})

    def _tool_recall(self, key: str) -> str:
        value = self.recall(key)
        if value is None:
            return json.dumps({"error": f"no memory for '{key}'"})
        return json.dumps({key: value})

    # ------------------------------------------------------------------
    # System prompt — persona + memory facts + discovery guidance.
    # Tool schemas and skill listings are deliberately NOT dumped here.
    # ------------------------------------------------------------------
    def _build_system_prompt(self) -> str:
        parts = [f"You are {self.name}, a helpful conversational assistant."]

        if self.memory:
            facts = "\n".join(f"- {key}: {value}" for key, value in self.memory.items())
            parts.append(f"Known facts (persistent memory):\n{facts}")

        parts.append(
            "Most of your tools and skills are NOT listed here, to keep this prompt short.\n"
            "- Call `search_tools(query)` to find tools for the current task — matches "
            "become callable on your next turn.\n"
            "- Call `search_skills(query)` to find relevant skills, then `load_skill(name)` "
            "to fetch its full instructions before following it."
        )
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # LLM — DeepSeek via the OpenAI-compatible Chat Completions API
    # ------------------------------------------------------------------
    def _llm_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def _call_llm(self, messages: list[dict], tools: Optional[list[dict]] = None):
        client = self._llm_client()
        kwargs = {"model": self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message

    # ------------------------------------------------------------------
    # Conversation turn
    # ------------------------------------------------------------------
    def respond(self, session_id: str, message: str) -> str:
        """Log the user's message, get a reply (DeepSeek if configured, offline otherwise), log and return it."""
        self.add_message(session_id, "user", message)

        if self.api_key:
            reply = self._respond_with_llm(session_id, message)
        else:
            reply = self._respond_offline(message)

        self.add_message(session_id, "assistant", reply)
        return reply

    def _respond_with_llm(self, session_id: str, message: str) -> str:
        messages: list[dict] = [{"role": "system", "content": self._build_system_prompt()}]
        messages.extend(
            {"role": entry["role"], "content": entry["content"]}
            for entry in self.get_history(session_id, limit=HISTORY_LIMIT)
        )

        # Only the discovery tools start active — search_tools dynamically
        # extends this list as the model surfaces tools it wants to use.
        active_tools = self.discovery_tools

        for _ in range(MAX_TOOL_ITERATIONS):
            schemas = [self.tools[name]["schema"] for name in active_tools]
            try:
                msg = self._call_llm(messages, tools=schemas)
            except Exception as exc:
                return f"[DeepSeek call failed: {exc}]"

            if not msg.tool_calls:
                return msg.content or ""

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.function.name, "arguments": call.function.arguments},
                    }
                    for call in msg.tool_calls
                ],
            })

            for call in msg.tool_calls:
                tool_name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                if self.verbose:
                    arg_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
                    print(f"  [tool] {tool_name}({arg_str})")

                if tool_name not in self.tools:
                    result = json.dumps({"error": f"unknown tool '{tool_name}'"})
                else:
                    result = self.tools[tool_name]["handler"](**args)
                    if tool_name == "search_tools":
                        for found in json.loads(result).get("matches", []):
                            if found["name"] not in active_tools:
                                active_tools.append(found["name"])

                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        return "[stopped: reached max tool-call iterations]"

    def _respond_offline(self, message: str) -> str:
        """Keyword-based fallback used when no DEEPSEEK_API_KEY is configured (no tool calling)."""
        lowered = message.lower()
        notes = [
            f"(recalling {key}: {value})"
            for key, value in self.memory.items()
            if key.lower().replace("_", " ") in lowered
        ]

        matched_skill = self._match_skill(message)
        if matched_skill:
            notes.append(f"[skill: {matched_skill}]\n{self.skills[matched_skill]['body'].strip()}")

        if notes:
            return "\n".join(notes)
        return (
            f"{self.name}: I heard \"{message}\" but have no matching memory or skill "
            "(set DEEPSEEK_API_KEY for full conversational replies with tool calling)."
        )

    def close(self) -> None:
        self.db.close()


def main() -> None:
    agent = Agent("Hermes-lite", home="./agent_home")
    session_id = "cli"

    mode = "DeepSeek (tool calling enabled)" if agent.api_key else "offline (no DEEPSEEK_API_KEY set)"
    print(f"{agent.name} ready [{mode}]. Skills: {', '.join(agent.list_skills()) or 'none'}.")
    print("Type 'exit' to quit.\n")

    try:
        while True:
            try:
                user_input = input("you> ").strip()
            except EOFError:
                break
            if user_input.lower() in {"exit", "quit"}:
                break
            if not user_input:
                continue
            print(f"{agent.name}> {agent.respond(session_id, user_input)}\n")
    finally:
        agent.close()


if __name__ == "__main__":
    main()
