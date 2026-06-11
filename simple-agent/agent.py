"""A small conversational agent: persistent memory, SQLite conversations,
markdown skills, and DeepSeek as the LLM backend.

Loosely modeled on the Hermes Agent architecture, scaled down to one class:
    - Memory     -> memory.json   (durable key/value facts, in the system prompt)
    - Skills     -> skills/*.md   (description + procedure, summarized in the
                                    system prompt; full body injected when relevant)
    - Sessions   -> conversations.db (SQLite, full message history per session_id)
    - LLM        -> DeepSeek's OpenAI-compatible Chat Completions API

DeepSeek setup:
    export DEEPSEEK_API_KEY="sk-..."
    # optional overrides:
    export DEEPSEEK_BASE_URL="https://api.deepseek.com"
    export DEEPSEEK_MODEL="deepseek-chat"

Without an API key the agent still runs in a simple offline mode (keyword
matching against memory and skills) so the rest of the class can be exercised
without network access.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
HISTORY_LIMIT = 20  # most recent messages sent to the LLM as context


class Agent:
    """A conversational agent with memory, SQLite-backed sessions, skills, and DeepSeek as the LLM."""

    def __init__(
        self,
        name: str,
        home: str | Path = "./agent_home",
        skills_dir: Optional[str | Path] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.name = name
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)

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
    # Skills — markdown files with a `description:` front-matter field
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
            if line and not line.startswith(("#", "-", "-")):
                return line
        return ""

    def list_skills(self) -> list[str]:
        return sorted(self.skills)

    def use_skill(self, name: str) -> Optional[str]:
        skill = self.skills.get(name)
        return skill["body"] if skill else None

    def _match_skill(self, message: str) -> Optional[str]:
        lowered = message.lower()
        for name in self.skills:
            if name.lower() in lowered or name.replace("_", " ").lower() in lowered:
                return name
        return None

    # ------------------------------------------------------------------
    # System prompt — persona + memory facts + skill summaries
    # ------------------------------------------------------------------
    def _build_system_prompt(self) -> str:
        parts = [f"You are {self.name}, a helpful conversational assistant."]

        if self.memory:
            facts = "\n".join(f"- {key}: {value}" for key, value in self.memory.items())
            parts.append(f"Known facts (persistent memory):\n{facts}")

        if self.skills:
            listing = "\n".join(f"- {name}: {meta['description']}" for name, meta in self.skills.items())
            parts.append(
                "Available skills (their full instructions are provided when relevant):\n" + listing
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

    def _call_llm(self, messages: list[dict]) -> str:
        client = self._llm_client()
        response = client.chat.completions.create(model=self.model, messages=messages)
        return response.choices[0].message.content

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
        messages = [{"role": "system", "content": self._build_system_prompt()}]

        matched_skill = self._match_skill(message)
        if matched_skill:
            messages.append({
                "role": "system",
                "content": f"The user's message matches the '{matched_skill}' skill. "
                           f"Follow these instructions:\n\n{self.skills[matched_skill]['body']}",
            })

        messages.extend(
            {"role": entry["role"], "content": entry["content"]}
            for entry in self.get_history(session_id, limit=HISTORY_LIMIT)
        )

        try:
            return self._call_llm(messages)
        except Exception as exc:
            return f"[DeepSeek call failed: {exc}]"

    def _respond_offline(self, message: str) -> str:
        """Keyword-based fallback used when no DEEPSEEK_API_KEY is configured."""
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
            "(set DEEPSEEK_API_KEY for full conversational replies)."
        )

    def close(self) -> None:
        self.db.close()


def main() -> None:
    agent = Agent("Hermes-lite", home="./agent_home")
    session_id = "cli"

    mode = "DeepSeek" if agent.api_key else "offline (no DEEPSEEK_API_KEY set)"
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
