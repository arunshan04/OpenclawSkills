"""
A standalone A2A chat client for talking to an agent registered on the
LiteLLM proxy.

It speaks the A2A JSON-RPC `message/send` protocol against
    {PROXY}/a2a/{agent_id_or_name}
keeping a single contextId across turns so the proxy logs them as one
conversation.

Usage:
    # interactive
    python agent_chat_client.py

    # scripted (one message per CLI arg)
    python agent_chat_client.py "hi" "what is 2+2?" "summarize the A2A protocol"

Env:
    PROXY      default http://localhost:4000
    PROXY_KEY  default sk-1234          (LiteLLM virtual/master key)
    AGENT      default deepseek-helper  (agent_id OR agent_name)
"""
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

import httpx

PROXY = os.environ.get("PROXY", "http://localhost:4000")
PROXY_KEY = os.environ.get("PROXY_KEY", "sk-1234")
AGENT = os.environ.get("AGENT", "deepseek-helper")


class AgentChatClient:
    """Minimal A2A client that keeps conversation context across turns."""

    def __init__(self, proxy: str, api_key: str, agent: str) -> None:
        self.endpoint = f"{proxy.rstrip('/')}/a2a/{agent}"
        self.api_key = api_key
        self.agent = agent
        # one contextId for the whole session -> grouped in the proxy logs
        self.context_id = str(uuid.uuid4())
        self._client = httpx.Client(timeout=90.0)

    def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }
        resp = self._client.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def send(self, text: str) -> str:
        """Send one user turn, return the agent's text reply."""
        params = {
            "message": {
                "kind": "message",
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
                "contextId": self.context_id,
            }
        }
        data = self._rpc("message/send", params)
        if "error" in data:
            return f"[error] {data['error']}"
        return self._extract_text(data.get("result", {}))

    @staticmethod
    def _extract_text(result: Dict[str, Any]) -> str:
        parts = result.get("parts", []) or []
        out: List[str] = []
        for p in parts:
            if isinstance(p, dict) and p.get("text"):
                out.append(str(p["text"]))
        return " ".join(out).strip() or "(no text in response)"

    def close(self) -> None:
        self._client.close()


def _banner(client: AgentChatClient) -> None:
    print("=" * 64)
    print(f" A2A Chat  →  agent '{client.agent}'  via  {PROXY}")
    print(f" context_id: {client.context_id}")
    print("=" * 64)


def run_scripted(client: AgentChatClient, messages: List[str]) -> None:
    for i, msg in enumerate(messages, 1):
        print(f"\n[you  #{i}] {msg}")
        reply = client.send(msg)
        print(f"[agent #{i}] {reply}")


def run_interactive(client: AgentChatClient) -> None:
    print(" Type your message and press Enter. 'exit' or Ctrl-D to quit.\n")
    while True:
        try:
            msg = input("you   > ").strip()
        except EOFError:
            break
        if msg.lower() in {"exit", "quit"}:
            break
        if not msg:
            continue
        print(f"agent > {client.send(msg)}")


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    client = AgentChatClient(PROXY, PROXY_KEY, AGENT)
    _banner(client)
    try:
        if argv:
            run_scripted(client, argv)
        else:
            run_interactive(client)
    finally:
        client.close()
    print("\n[done]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
