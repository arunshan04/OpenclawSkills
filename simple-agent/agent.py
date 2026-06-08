"""A minimal agent: persistent memory, SQLite-backed conversations, and file-based skills.

Loosely modeled on the Hermes Agent architecture (memory store + SessionDB +
skills directory), scaled down to one class for learning/demo purposes.

Layout under `home`:
    memory.json       - durable key/value facts the agent remembers across sessions
    conversations.db  - SQLite log of every message, grouped by session_id
    skills/*.md       - markdown snippets the agent can pull in by name
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional


class Agent:
    """An agent that remembers facts, logs conversations to SQLite, and uses skills from disk."""

    def __init__(self, name: str, home: str | Path = "./agent_home"):
        self.name = name
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)

        self.memory_path = self.home / "memory.json"
        self.memory: dict[str, str] = self._load_memory()

        self.skills_dir = self.home / "skills"
        self.skills_dir.mkdir(exist_ok=True)
        self.skills: dict[str, str] = self._load_skills()

        self.db = sqlite3.connect(self.home / "conversations.db", check_same_thread=False)
        self._init_db()

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

    def get_history(self, session_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        return [{"role": role, "content": content, "created_at": ts} for role, content, ts in rows]

    # ------------------------------------------------------------------
    # Skills — markdown snippets loaded from skills/*.md, matched by name
    # ------------------------------------------------------------------
    def _load_skills(self) -> dict[str, str]:
        return {path.stem: path.read_text() for path in sorted(self.skills_dir.glob("*.md"))}

    def list_skills(self) -> list[str]:
        return sorted(self.skills)

    def use_skill(self, name: str) -> Optional[str]:
        return self.skills.get(name)

    # ------------------------------------------------------------------
    # Conversation turn — ties memory, skills, and the conversation log together
    # ------------------------------------------------------------------
    def respond(self, session_id: str, message: str) -> str:
        """Log the user's message, draft a reply from memory + matching skills, log and return it."""
        self.add_message(session_id, "user", message)

        lowered = message.lower()
        notes = [
            f"(recalling {key}: {value})"
            for key, value in self.memory.items()
            if key.lower().replace("_", " ") in lowered
        ]
        notes += [f"[skill: {name}]\n{body.strip()}" for name, body in self.skills.items() if name.lower() in lowered]

        reply = "\n".join(notes) if notes else f"{self.name}: I heard \"{message}\" but have no matching memory or skill."
        self.add_message(session_id, "assistant", reply)
        return reply

    def close(self) -> None:
        self.db.close()


if __name__ == "__main__":
    agent = Agent("Demo", home="./agent_home")

    (agent.skills_dir / "greeting.md").write_text("# Greeting Skill\nSay hello warmly and ask how you can help.")
    agent.skills = agent._load_skills()

    agent.remember("favorite_color", "teal")

    print(agent.respond("session-1", "What's my favorite color?"))
    print(agent.respond("session-1", "Can you use the greeting skill?"))
    print("History:", agent.get_history("session-1"))

    agent.close()
