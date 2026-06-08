"""
A minimal, spec-compliant A2A agent server.

- Serves its agent card at GET /.well-known/agent-card.json (+ /.well-known/agent.json)
- Handles A2A JSON-RPC `message/send` at POST /
- Backed by DeepSeek (deepseek-chat) via the local LiteLLM proxy, with a
  deterministic fallback so it never hard-fails.

Run:  uvicorn deepseek_a2a_agent:app --host 0.0.0.0 --port 9100
"""
import json
import os
import uuid
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

AGENT_PORT = int(os.environ.get("AGENT_PORT", "9100"))
AGENT_PUBLIC_URL = os.environ.get("AGENT_PUBLIC_URL", f"http://localhost:{AGENT_PORT}/")

# The agent reaches DeepSeek *through* the LiteLLM proxy (so the call is logged
# + cost-tracked there too). Falls back gracefully if unreachable.
PROXY_BASE = os.environ.get("PROXY_BASE", "http://localhost:4000")
PROXY_KEY = os.environ.get("PROXY_KEY", "sk-1234")
BACKING_MODEL = os.environ.get("BACKING_MODEL", "deepseek-chat")

# MCP: the agent pulls tools from LiteLLM's MCP gateway and lets DeepSeek call
# them via function-calling. Set MCP_SERVER_ID to the registered server's id.
MCP_SERVER_ID = os.environ.get("MCP_SERVER_ID", "")
MCP_TOOLS_LIST = f"{PROXY_BASE}/mcp-rest/tools/list"
MCP_TOOLS_CALL = f"{PROXY_BASE}/mcp-rest/tools/call"

SYSTEM_PROMPT = (
    "You are 'DeepSeek Helper', a concise A2A agent. You have access to MCP "
    "tools (math, text, time, weather). Use a tool when it helps answer "
    "accurately, then reply helpfully in at most 4 sentences."
)


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {PROXY_KEY}"}


def _fetch_mcp_tools() -> List[Dict[str, Any]]:
    """List MCP tools from LiteLLM and convert them to OpenAI tool schema."""
    try:
        r = httpx.get(MCP_TOOLS_LIST, headers=_auth_headers(), timeout=20.0)
        r.raise_for_status()
        payload = r.json()
        raw = payload.get("tools", payload) if isinstance(payload, dict) else payload
        tools = []
        for t in raw:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("inputSchema")
                        or {"type": "object", "properties": {}},
                    },
                }
            )
        return tools
    except Exception:
        return []


def _call_mcp_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Execute an MCP tool through the LiteLLM gateway, return text result."""
    try:
        body: Dict[str, Any] = {"name": name, "arguments": arguments}
        if MCP_SERVER_ID:
            body["server_id"] = MCP_SERVER_ID
        r = httpx.post(
            MCP_TOOLS_CALL, headers=_auth_headers(), json=body, timeout=30.0
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data.get("structuredContent"), dict):
            return json.dumps(data["structuredContent"])
        parts = data.get("content", [])
        return " ".join(
            p.get("text", "") for p in parts if isinstance(p, dict)
        ) or json.dumps(data)
    except Exception as exc:
        return f"[tool error: {exc}]"

app = FastAPI(title="DeepSeek A2A Agent")


AGENT_CARD: Dict[str, Any] = {
    "protocolVersion": "0.3.0",
    "name": "DeepSeek Helper",
    "description": (
        "A general-purpose assistant agent backed by DeepSeek. Answers questions, "
        "explains concepts, and summarizes text via the A2A protocol."
    ),
    "url": AGENT_PUBLIC_URL,
    "version": "1.0.0",
    "defaultInputModes": ["text"],
    "defaultOutputModes": ["text"],
    "capabilities": {"streaming": False},
    "skills": [
        {
            "id": "answer_question",
            "name": "Answer a question",
            "description": "Answers general-knowledge questions concisely.",
            "tags": ["qa", "general", "deepseek"],
            "examples": ["What is the capital of France?", "Explain TCP in one line"],
        },
        {
            "id": "summarize",
            "name": "Summarize text",
            "description": "Produces a short summary of the provided text.",
            "tags": ["summarize", "nlp"],
            "examples": ["Summarize: <long text>"],
        },
    ],
}


def _extract_user_text(params: Dict[str, Any]) -> str:
    """Pull the concatenated text out of an A2A message/send params object."""
    message = params.get("message", {}) or {}
    parts = message.get("parts", []) or []
    chunks: List[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        # A2A TextPart: {"kind": "text", "text": "..."}
        if part.get("kind") == "text" and part.get("text"):
            chunks.append(str(part["text"]))
        # tolerate {"type": "text", ...} or nested text
        elif part.get("text"):
            chunks.append(str(part["text"]))
    return "\n".join(chunks).strip()


def _chat_completion(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]):
    """One call to deepseek-chat (with optional tools) through the proxy."""
    body: Dict[str, Any] = {
        "model": BACKING_MODEL,
        "messages": messages,
        "max_tokens": 400,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    resp = httpx.post(
        f"{PROXY_BASE}/v1/chat/completions",
        headers=_auth_headers(),
        json=body,
        timeout=90.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]


def _ask_deepseek(user_text: str) -> str:
    """Answer the user, using MCP tools via DeepSeek function-calling.

    Runs a short tool-calling loop: ask the model, run any MCP tool calls it
    requests, feed results back, repeat until it returns a final answer.
    Falls back gracefully on any error.
    """
    try:
        tools = _fetch_mcp_tools()
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]
        for _ in range(4):  # cap tool-calling rounds
            msg = _chat_completion(messages, tools)
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return (msg.get("content") or "").strip() or "(no answer)"
            # record the assistant turn that requested the tools
            messages.append(msg)
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    args = {}
                result = _call_mcp_tool(name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id"),
                        "name": name,
                        "content": result,
                    }
                )
        # Out of rounds — ask once more without tools for a final answer.
        final = _chat_completion(messages, [])
        return (final.get("content") or "").strip() or "(no answer)"
    except Exception as exc:  # graceful, never hard-fail the A2A call
        return (
            f"[DeepSeek Helper fallback] I received: '{user_text}'. "
            f"(backend error: {exc})"
        )


def _message_result(text: str, request_id: Any, context_id: str) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "kind": "message",
            "messageId": str(uuid.uuid4()),
            "role": "agent",
            "parts": [{"kind": "text", "text": text}],
            "contextId": context_id,
        },
    }


@app.get("/.well-known/agent-card.json")
@app.get("/.well-known/agent.json")
async def agent_card() -> JSONResponse:
    return JSONResponse(content=AGENT_CARD)


@app.post("/")
@app.post("/message/send")
async def handle_rpc(request: Request) -> JSONResponse:
    body = await request.json()
    request_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {}) or {}

    if body.get("jsonrpc") != "2.0":
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id,
             "error": {"code": -32600, "message": "jsonrpc must be 2.0"}},
            status_code=400,
        )

    if method not in ("message/send", "message/stream"):
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id,
             "error": {"code": -32601, "message": f"method '{method}' not supported"}},
            status_code=400,
        )

    context_id = (params.get("message", {}) or {}).get("contextId") or str(uuid.uuid4())
    user_text = _extract_user_text(params) or "(empty message)"
    answer = _ask_deepseek(user_text)
    return JSONResponse(content=_message_result(answer, request_id, context_id))


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}
