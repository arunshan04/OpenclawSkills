# LiteLLM + A2A Agent + MCP Tools — local runbook

A reproducible stack: LiteLLM proxy/dashboard, a DeepSeek-backed A2A agent,
an MCP tools server, and a standalone chat client — all wired together and
runnable on `localhost`.

```
agent_chat_client.py ──▶ LiteLLM proxy (:4000, /a2a/<agent>) ──▶ deepseek_a2a_agent.py (:9100)
                                                                        │
                                                                        ├─▶ DeepSeek API (via proxy /v1/chat/completions)
                                                                        └─▶ MCP gateway (/mcp-rest/tools/*) ──▶ mcp_tools_server.py (:9200)
```

## 0. Prerequisites (once)

```bash
# Postgres (LiteLLM's UI/DB needs it)
sudo service postgresql start
sudo -u postgres psql -c "CREATE ROLE litellm LOGIN PASSWORD 'litellm';"
sudo -u postgres psql -c "CREATE DATABASE litellm OWNER litellm;"

# Python env
python -m venv .venv && source .venv/bin/activate
pip install 'litellm[proxy]' a2a-sdk==0.3.24 fastapi uvicorn httpx 'mcp[cli]'

export DATABASE_URL="postgresql://litellm:litellm@localhost:5432/litellm"
export DEEPSEEK_API_KEY="<your-own-deepseek-key>"   # generate a fresh one
```

`litellm_config.yaml` references the DeepSeek key only via `os.environ/DEEPSEEK_API_KEY`
— never hardcode it.

## 1. Start the MCP tools server (port 9200)

```bash
python mcp_tools_server.py
```
Exposes 5 demo tools (`add`, `multiply`, `word_count`, `current_time`, `weather`)
over streamable-HTTP at `http://localhost:9200/mcp`.

## 2. Start the LiteLLM proxy + dashboard (port 4000)

```bash
litellm --config litellm_config.yaml --port 4000
```
Dashboard: `http://localhost:4000/ui` — log in with **username `admin`**,
**password = your `master_key`** (`sk-1234` in the sample config; change it for real use).

## 3. Register the MCP server with the proxy

Via UI: *MCP Servers → + Add New MCP Server* → name `demo_tools`, transport `HTTP`,
URL `http://localhost:9200/mcp`, auth `none`.

Or via API:
```bash
curl -s -X POST http://localhost:4000/v1/mcp/server \
  -H "Authorization: Bearer sk-1234" -H "Content-Type: application/json" \
  -d '{"server_name":"demo_tools","alias":"demo_tools","url":"http://localhost:9200/mcp","transport":"http","auth_type":"none"}'
```
Copy the returned `server_id` for step 5.

## 4. Start the A2A agent (port 9100)

```bash
export PROXY_BASE=http://localhost:4000
export PROXY_KEY=sk-1234
export MCP_SERVER_ID="<server_id from step 3>"
uvicorn deepseek_a2a_agent:app --host 0.0.0.0 --port 9100
```
Serves its agent card at `http://localhost:9100/.well-known/agent-card.json`
and handles A2A JSON-RPC `message/send` at `/`.

## 5. Register the agent with the proxy

Via UI: *Agents → Add Agent* → URL `http://localhost:9100/`.

Or via API (note: `agent_name` must be unique):
```bash
curl -s -X POST http://localhost:4000/v1/agents \
  -H "Authorization: Bearer sk-1234" -H "Content-Type: application/json" \
  -d '{"agent_id":"deepseek-helper","agent_name":"deepseek-helper","agent_card_params":{"url":"http://localhost:9100/"}}'
```
Copy the returned `agent_id` (a UUID) for step 6.

## 6. Chat with the agent

```bash
export PROXY=http://localhost:4000
export PROXY_KEY=sk-1234
export AGENT="<agent_id from step 5>"          # or the agent_name, if unique

# scripted
python agent_chat_client.py "hi" "what is 23*7? use your multiply tool" "weather in Paris?"

# interactive
python agent_chat_client.py
```

The client keeps one `contextId` for the whole session so the proxy groups the
turns together in *Logs*.

## Notes

- **MCP traffic doesn't appear in the dashboard's Logs/spend-log screen** — only
  `acompletion` (LLM) and `asend_message` (agent) call types get persisted to
  `LiteLLM_SpendLogs` in this LiteLLM build; `call_mcp_tool` rows are never written.
  To verify MCP tool invocation, check the **MCP server's own access log**
  (`ListToolsRequest` / `CallToolRequest` entries) and the **proxy's access log**
  (`GET /mcp-rest/tools/list`, `POST /mcp-rest/tools/call`) — both line up 1:1
  with each chat turn that needed a tool.
- If you see `"Tool names must be unique"` errors from DeepSeek, you likely have
  a duplicate MCP server registration — `GET /v1/mcp/server` and delete the stale one.
- `server_name` for MCP servers cannot contain `-` (use `_`).
