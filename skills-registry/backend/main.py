import json
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from models import SkillCreate, SkillUpdate, LLMResearchRequest, LLMResearchResponse
from database import init_db, get_db, row_to_dict
from llm_service import research_skill


# ── MCP Server ────────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="Skills Registry",
    instructions=(
        "This MCP server provides access to the Skills Registry, "
        "a catalog of AI agent capabilities. Use it to discover, search, "
        "and manage skills that agents can leverage."
    ),
)


@mcp.tool()
def list_skills(
    category: Optional[str] = None,
    status: Optional[str] = "active",
    limit: int = 50,
) -> List[dict]:
    """List all skills in the registry, optionally filtered by category or status."""
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
        return [row_to_dict(r) for r in rows]


@mcp.tool()
def get_skill(skill_id: str) -> dict:
    """Get detailed information about a specific skill by its ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
        if not row:
            return {"error": f"Skill '{skill_id}' not found"}
        return row_to_dict(row)


@mcp.tool()
def search_skills(query: str) -> List[dict]:
    """Search skills by name, description, or tags."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM skills WHERE
               name LIKE ? OR description LIKE ? OR tags LIKE ? OR category LIKE ?
               ORDER BY name LIMIT 20""",
            tuple(f"%{query}%" for _ in range(4))
        ).fetchall()
        return [row_to_dict(r) for r in rows]


@mcp.tool()
def list_categories() -> List[str]:
    """List all unique skill categories in the registry."""
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM skills ORDER BY category").fetchall()
        return [r[0] for r in rows]


@mcp.tool()
def get_skill_tools(skill_id: str) -> List[dict]:
    """Get the list of tools provided by a specific skill."""
    with get_db() as conn:
        row = conn.execute("SELECT tools FROM skills WHERE id = ?", (skill_id,)).fetchone()
        if not row:
            return []
        return json.loads(row[0]) if isinstance(row[0], str) else row[0]


# ── FastAPI App ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Skills Registry API",
    description="REST API and MCP server for managing AI agent skills",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP server under /mcp
app.mount("/mcp", mcp.http_app())


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
        return {
            "total": total,
            "active": active,
            "categories": categories,
            "llm_generated": llm_gen,
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
        # Check name uniqueness
        existing = conn.execute("SELECT id FROM skills WHERE name = ?", (skill.name,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Skill '{skill.name}' already exists")
        conn.execute("""
            INSERT INTO skills
            (id, name, description, category, icon, icon_bg_color, tags, version, author, status,
             tools, prompts, resources, mcp_config, source, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            skill_id, skill.name, skill.description, skill.category,
            skill.icon, skill.icon_bg_color,
            json.dumps(skill.tags), skill.version, skill.author, skill.status,
            json.dumps([t.model_dump() for t in skill.tools]),
            json.dumps([p.model_dump() for p in skill.prompts]),
            json.dumps([r.model_dump() for r in skill.resources]),
            json.dumps(skill.mcp_config),
            skill.source,
            json.dumps(skill.metadata),
            now, now
        ))
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

        # Serialize list/dict fields
        for field in ["tags", "mcp_config", "metadata"]:
            if field in data:
                data[field] = json.dumps(data[field])
        for field in ["tools", "prompts", "resources"]:
            if field in data:
                data[field] = json.dumps([item.model_dump() for item in data[field]])

        if not data:
            return current

        set_clause = ", ".join(f"{k} = ?" for k in data)
        values = list(data.values()) + [now, skill_id]
        conn.execute(
            f"UPDATE skills SET {set_clause}, updated_at = ? WHERE id = ?", values
        )
    return api_get_skill(skill_id)


@app.delete("/skills/{skill_id}", status_code=204)
def api_delete_skill(skill_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM skills WHERE id = ?", (skill_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Skill not found")
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


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
