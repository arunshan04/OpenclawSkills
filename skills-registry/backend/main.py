import json
import uuid
import asyncio
import time
import functools
from datetime import datetime
from contextlib import asynccontextmanager
from typing import List, Optional, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from fastmcp.tools import Tool as MCPTool
from pydantic import BaseModel

from models import SkillCreate, SkillUpdate, LLMResearchRequest, LLMResearchResponse
from database import init_db, get_db, row_to_dict
from llm_service import research_skill
from executor import execute_tool, load_tool_fn
from logger import setup_logging, get_log_buffer, log

setup_logging()
_log = log("registry")


# ── MCP Server ────────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="Skills Registry",
    instructions=(
        "This MCP server provides access to the Skills Registry. "
        "Skills registered here with implemented tools are directly callable. "
        "Use list_skills to discover available capabilities."
    ),
)

_registered_tool_names: set[str] = set()


def _wrap_with_logging(fn, tool_name: str):
    """Wrap a tool function so every MCP call is logged with params, result, and timing."""
    @functools.wraps(fn)
    def logged(**kwargs):
        param_summary = {k: (str(v)[:80] if isinstance(v, str) else v) for k, v in kwargs.items()}
        _log.info("TOOL_CALL  tool=%s  params=%s", tool_name, param_summary)
        t0 = time.monotonic()
        try:
            result = fn(**kwargs)
            ms = round((time.monotonic() - t0) * 1000)
            preview = str(result)[:120].replace("\n", "↵")
            _log.info("TOOL_OK  tool=%s  ms=%d  result=%r", tool_name, ms, preview)
            return result
        except Exception as exc:
            ms = round((time.monotonic() - t0) * 1000)
            _log.error("TOOL_ERROR  tool=%s  ms=%d  error=%s", tool_name, ms, exc)
            raise
    return logged


def register_skill_tools(tools: list[dict], skill_name: str, override: bool = False):
    """Dynamically register tool implementations with FastMCP."""
    for tool_def in tools:
        tool_name = tool_def.get("name", "").strip()
        has_impl = any([
            tool_def.get("code", "").strip(),
            tool_def.get("source_file", "").strip(),
            tool_def.get("source_url", "").strip(),
        ])
        if not tool_name or not has_impl:
            continue
        if tool_name in _registered_tool_names and not override:
            continue

        fn = load_tool_fn(tool_def, tool_name)
        if fn is None:
            _log.warning("MCP_SKIP  tool=%s  skill=%s  reason=load_error", tool_name, skill_name)
            continue

        try:
            logged_fn = _wrap_with_logging(fn, tool_name)
            mcp_tool = MCPTool.from_function(logged_fn, name=tool_name, description=tool_def.get("description", ""))
            mcp.add_tool(mcp_tool)
            _registered_tool_names.add(tool_name)
            source = tool_def.get("source_file") or tool_def.get("source_url") or "inline"
            _log.info("MCP_REGISTER  tool=%s  skill=%s  source=%s  override=%s",
                      tool_name, skill_name, source, override)
        except Exception as e:
            _log.error("MCP_REGISTER_FAIL  tool=%s  skill=%s  error=%s", tool_name, skill_name, e)


def load_all_dynamic_tools():
    """At startup, load and register all tools that have implementations."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT name, tools FROM skills WHERE status='active'"
        ).fetchall()
    before = len(_registered_tool_names)
    for row in rows:
        tools = json.loads(row["tools"]) if isinstance(row["tools"], str) else row["tools"] or []
        register_skill_tools(tools, row["name"])
    added = len(_registered_tool_names) - before
    _log.info("STARTUP  skills_scanned=%d  tools_registered=%d", len(rows), added)


# ── Built-in registry MCP tools ───────────────────────────────────────────────
@mcp.tool()
def list_skills(
    category: Optional[str] = None,
    status: Optional[str] = "active",
    limit: int = 50,
) -> List[dict]:
    """List all skills in the registry, optionally filtered by category or status."""
    _log.info("TOOL_CALL  tool=list_skills  params={category=%s, status=%s, limit=%d}", category, status, limit)
    t0 = time.monotonic()
    with get_db() as conn:
        query = "SELECT * FROM skills WHERE 1=1"
        params: list = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY name LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        result = [row_to_dict(r) for r in rows]
    _log.info("TOOL_OK  tool=list_skills  ms=%d  result=%d skills", round((time.monotonic()-t0)*1000), len(result))
    return result


@mcp.tool()
def get_skill(skill_id: str) -> dict:
    """Get detailed information about a specific skill by its ID."""
    _log.info("TOOL_CALL  tool=get_skill  params={skill_id=%s}", skill_id)
    t0 = time.monotonic()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
        if not row:
            _log.warning("TOOL_OK  tool=get_skill  ms=%d  result=not_found", round((time.monotonic()-t0)*1000))
            return {"error": f"Skill '{skill_id}' not found"}
        result = row_to_dict(row)
    _log.info("TOOL_OK  tool=get_skill  ms=%d  result=%s", round((time.monotonic()-t0)*1000), result.get("name"))
    return result


@mcp.tool()
def search_skills(query: str) -> List[dict]:
    """Search skills by name, description, or tags."""
    _log.info("TOOL_CALL  tool=search_skills  params={query=%r}", query)
    t0 = time.monotonic()
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM skills WHERE
               name LIKE ? OR description LIKE ? OR tags LIKE ? OR category LIKE ?
               ORDER BY name LIMIT 20""",
            tuple(f"%{query}%" for _ in range(4))
        ).fetchall()
        result = [row_to_dict(r) for r in rows]
    _log.info("TOOL_OK  tool=search_skills  ms=%d  result=%d matches", round((time.monotonic()-t0)*1000), len(result))
    return result


@mcp.tool()
def list_categories() -> List[str]:
    """List all unique skill categories in the registry."""
    _log.info("TOOL_CALL  tool=list_categories")
    t0 = time.monotonic()
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM skills ORDER BY category").fetchall()
        result = [r[0] for r in rows]
    _log.info("TOOL_OK  tool=list_categories  ms=%d  result=%s", round((time.monotonic()-t0)*1000), result)
    return result


# ── FastAPI App ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    _log.info("SERVER_START  rest=0.0.0.0:8000  mcp=0.0.0.0:8001")
    init_db()
    load_all_dynamic_tools()
    task = asyncio.create_task(
        mcp.run_http_async(host="0.0.0.0", port=8001, json_response=True, stateless_http=True)
    )
    yield
    _log.info("SERVER_STOP")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Skills Registry API",
    description="REST API + MCP server with embedded tool execution",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Tool execution ────────────────────────────────────────────────────────────
class ExecuteRequest(BaseModel):
    params: dict[str, Any] = {}


@app.post("/skills/{skill_id}/tools/{tool_name}/execute")
def api_execute_tool(skill_id: str, tool_name: str, req: ExecuteRequest):
    """Execute a tool's embedded Python code with provided parameters."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Skill not found")

    skill = row_to_dict(row)
    tools = skill.get("tools", [])
    tool_def = next((t for t in tools if t.get("name") == tool_name), None)

    if not tool_def:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found in skill")

    code = (tool_def.get("code") or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Tool has no implementation. Add Python code first.")

    try:
        result = execute_tool(code, tool_name, req.params)
        return {"ok": True, "result": result, "tool": tool_name}
    except TimeoutError as e:
        _log.error("TOOL_TIMEOUT  skill=%s  tool=%s", skill_id, tool_name)
        raise HTTPException(status_code=408, detail=str(e))
    except (ValueError, RuntimeError) as e:
        _log.error("TOOL_EXEC_FAIL  skill=%s  tool=%s  error=%s", skill_id, tool_name, str(e)[:200])
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/tools/reload")
def api_reload_tools():
    """Re-scan the DB and register any newly added tool implementations with FastMCP."""
    before = len(_registered_tool_names)
    load_all_dynamic_tools()
    after = len(_registered_tool_names)
    return {"registered_tools": after, "newly_added": after - before}


class ExternalToolRequest(BaseModel):
    name: str
    description: str
    input_schema: Optional[dict] = None
    # Provide ONE of these:
    code: Optional[str] = None          # inline Python
    source_file: Optional[str] = None   # /path/to/file.py  (function name must match 'name')
    source_url: Optional[str] = None    # https://my-api.com/tool  (POST, receives params as JSON)
    override: bool = False              # replace if already registered


@app.post("/tools/register")
def api_register_external_tool(req: ExternalToolRequest):
    """
    Register an external tool with MCP directly — no skill record needed.
    Use this to wire up functions from files, HTTP endpoints, or inline code
    without going through the UI.
    """
    if not any([req.code, req.source_file, req.source_url]):
        raise HTTPException(status_code=400, detail="Provide code, source_file, or source_url")

    if req.name in _registered_tool_names and not req.override:
        raise HTTPException(
            status_code=409,
            detail=f"Tool '{req.name}' already registered. Set override=true to replace it."
        )

    tool_def = req.model_dump()
    fn = load_tool_fn(tool_def, req.name)
    if fn is None:
        raise HTTPException(status_code=422, detail=f"Failed to load function '{req.name}'. Check your code/file.")

    logged_fn = _wrap_with_logging(fn, req.name)
    mcp_tool = MCPTool.from_function(logged_fn, name=req.name, description=req.description)
    mcp.add_tool(mcp_tool)
    _registered_tool_names.add(req.name)

    source = req.source_file or req.source_url or "inline"
    _log.info("MCP_REGISTER  tool=%s  skill=external  source=%s  override=%s", req.name, source, req.override)
    return {"ok": True, "tool": req.name, "source": source, "registered_tools": sorted(_registered_tool_names)}


# ── REST Endpoints ────────────────────────────────────────────────────────────
@app.get("/skills", response_model=List[dict])
def api_list_skills(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    with get_db() as conn:
        base = "SELECT * FROM skills WHERE 1=1"
        params: list = []
        if category:
            base += " AND category = ?"
            params.append(category)
        if status:
            base += " AND status = ?"
            params.append(status)
        if search:
            base += " AND (name LIKE ? OR description LIKE ? OR tags LIKE ?)"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        base += " ORDER BY name"
        rows = conn.execute(base, params).fetchall()
        return [row_to_dict(r) for r in rows]


@app.get("/skills/categories")
def api_list_categories():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) as count FROM skills GROUP BY category ORDER BY category"
        ).fetchall()
        return [{"category": r[0], "count": r[1]} for r in rows]


@app.get("/skills/stats")
def api_stats():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM skills WHERE status='active'").fetchone()[0]
        categories = conn.execute("SELECT COUNT(DISTINCT category) FROM skills").fetchone()[0]
        llm_gen = conn.execute("SELECT COUNT(*) FROM skills WHERE source='llm_generated'").fetchone()[0]
        with_code = conn.execute(
            "SELECT COUNT(*) FROM skills WHERE tools LIKE '%\"code\"%'"
        ).fetchone()[0]
        return {
            "total": total,
            "active": active,
            "categories": categories,
            "llm_generated": llm_gen,
            "with_implementations": with_code,
        }


@app.get("/skills/{skill_id}")
def api_get_skill(skill_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Skill not found")
        return row_to_dict(row)


@app.post("/skills", status_code=201)
def api_create_skill(skill: SkillCreate):
    skill_id = f"skill-{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM skills WHERE name = ?", (skill.name,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Skill '{skill.name}' already exists")
        tools_data = [t.model_dump() for t in skill.tools]
        conn.execute("""
            INSERT INTO skills
            (id, name, description, category, icon, icon_bg_color, tags, version, author, status,
             tools, prompts, resources, mcp_config, source, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            skill_id, skill.name, skill.description, skill.category,
            skill.icon, skill.icon_bg_color,
            json.dumps(skill.tags), skill.version, skill.author, skill.status,
            json.dumps(tools_data),
            json.dumps([p.model_dump() for p in skill.prompts]),
            json.dumps([r.model_dump() for r in skill.resources]),
            json.dumps(skill.mcp_config), skill.source, json.dumps(skill.metadata),
            now, now
        ))
    register_skill_tools(tools_data, skill.name)
    _log.info("SKILL_CREATE  id=%s  name=%s  category=%s  tools=%d  source=%s",
              skill_id, skill.name, skill.category, len(tools_data), skill.source)
    return api_get_skill(skill_id)


@app.put("/skills/{skill_id}")
def api_update_skill(skill_id: str, update: SkillUpdate):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Skill not found")

        current = row_to_dict(row)
        now = datetime.utcnow().isoformat()
        data = update.model_dump(exclude_none=True)

        for field in ["tags", "mcp_config", "metadata"]:
            if field in data:
                data[field] = json.dumps(data[field])

        tools_data = None
        if "tools" in data:
            tools_data = [item if isinstance(item, dict) else item.model_dump() for item in data["tools"]]
            data["tools"] = json.dumps(tools_data)
        for field in ["prompts", "resources"]:
            if field in data:
                data[field] = json.dumps([item if isinstance(item, dict) else item.model_dump() for item in data[field]])

        if not data:
            return current

        set_clause = ", ".join(f"{k} = ?" for k in data)
        values = list(data.values()) + [now, skill_id]
        conn.execute(f"UPDATE skills SET {set_clause}, updated_at = ? WHERE id = ?", values)

    if tools_data:
        register_skill_tools(tools_data, current.get("name", skill_id))
    changed = [k for k in update.model_dump(exclude_none=True).keys()]
    _log.info("SKILL_UPDATE  id=%s  name=%s  fields=%s", skill_id, current.get("name"), changed)
    return api_get_skill(skill_id)


@app.delete("/skills/{skill_id}", status_code=204)
def api_delete_skill(skill_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT id, name FROM skills WHERE id = ?", (skill_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Skill not found")
        _log.info("SKILL_DELETE  id=%s  name=%s", skill_id, row["name"])
        conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))


@app.post("/skills/research", response_model=LLMResearchResponse)
def api_research_skill(request: LLMResearchRequest):
    try:
        result = research_skill(
            query=request.query,
            category=request.category,
            existing_skills=request.existing_skills or [],
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM research failed: {str(e)}")


@app.get("/logs")
def api_logs(limit: int = Query(100, le=500), level: Optional[str] = Query(None)):
    """Return recent log entries from the in-memory buffer."""
    entries = get_log_buffer()
    if level:
        entries = [e for e in entries if e.get("level") == level.upper()]
    return {"logs": entries[-limit:], "total": len(entries)}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "registered_tools": len(_registered_tool_names),
        "tools": sorted(_registered_tool_names),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
