import sqlite3
import json
import os
from contextlib import contextmanager
from datetime import datetime
import uuid

DB_PATH = os.getenv("DB_PATH", "skills.db")

SAMPLE_SKILLS = [
    {
        "id": "skill-web-search",
        "name": "Web Search",
        "description": "Search the web for current information and retrieve relevant results using multiple search engines",
        "category": "Research",
        "icon": "🔍",
        "icon_bg_color": "#3b82f6",
        "tags": ["search", "web", "research", "information", "internet"],
        "version": "1.2.0",
        "author": "System",
        "status": "active",
        "tools": [
            {"name": "web_search", "description": "Search the web with a query string", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}}},
            {"name": "fetch_url", "description": "Fetch content from a URL", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}}}
        ],
        "prompts": [],
        "resources": [],
        "mcp_config": {"transport": "stdio"},
        "source": "manual",
        "metadata": {"popularity": 95}
    },
    {
        "id": "skill-code-review",
        "name": "Code Review",
        "description": "Analyze and review code for quality, security vulnerabilities, and best practices across multiple languages",
        "category": "Development",
        "icon": "👨‍💻",
        "icon_bg_color": "#10b981",
        "tags": ["code", "review", "quality", "security", "best-practices"],
        "version": "2.0.0",
        "author": "System",
        "status": "active",
        "tools": [
            {"name": "review_code", "description": "Review code for issues", "input_schema": {"type": "object", "properties": {"code": {"type": "string"}, "language": {"type": "string"}}}},
            {"name": "suggest_improvements", "description": "Suggest code improvements", "input_schema": {"type": "object", "properties": {"code": {"type": "string"}}}}
        ],
        "prompts": [
            {"name": "code_review_prompt", "description": "Standard code review prompt", "template": "Review the following {language} code for quality and security..."}
        ],
        "resources": [],
        "mcp_config": {"transport": "stdio"},
        "source": "manual",
        "metadata": {"popularity": 88}
    },
    {
        "id": "skill-data-analysis",
        "name": "Data Analysis",
        "description": "Analyze datasets, generate insights, create visualizations, and produce statistical summaries",
        "category": "Analytics",
        "icon": "📊",
        "icon_bg_color": "#f59e0b",
        "tags": ["data", "analytics", "visualization", "statistics", "insights"],
        "version": "1.5.0",
        "author": "System",
        "status": "active",
        "tools": [
            {"name": "analyze_data", "description": "Run statistical analysis on data", "input_schema": {"type": "object", "properties": {"data": {"type": "array"}, "analysis_type": {"type": "string"}}}},
            {"name": "create_chart", "description": "Generate chart from data", "input_schema": {"type": "object", "properties": {"data": {"type": "array"}, "chart_type": {"type": "string"}}}}
        ],
        "prompts": [],
        "resources": [],
        "mcp_config": {"transport": "sse", "url": "http://localhost:8002/mcp"},
        "source": "manual",
        "metadata": {"popularity": 75}
    },
    {
        "id": "skill-document-writer",
        "name": "Document Writer",
        "description": "Create professional documents, reports, and technical documentation with proper formatting",
        "category": "Productivity",
        "icon": "📝",
        "icon_bg_color": "#8b5cf6",
        "tags": ["writing", "documents", "reports", "documentation", "content"],
        "version": "1.0.0",
        "author": "System",
        "status": "active",
        "tools": [
            {"name": "write_document", "description": "Create a document from template", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}, "format": {"type": "string"}}}},
            {"name": "format_text", "description": "Format and structure text content", "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "style": {"type": "string"}}}}
        ],
        "prompts": [
            {"name": "document_outline", "description": "Generate document outline", "template": "Create an outline for a document about {topic}..."}
        ],
        "resources": [],
        "mcp_config": {"transport": "stdio"},
        "source": "manual",
        "metadata": {"popularity": 82}
    },
    {
        "id": "skill-security-scanner",
        "name": "Security Scanner",
        "description": "Scan systems, code, and configurations for security vulnerabilities and compliance issues",
        "category": "Security",
        "icon": "🛡️",
        "icon_bg_color": "#ef4444",
        "tags": ["security", "scanner", "vulnerability", "compliance", "audit"],
        "version": "3.1.0",
        "author": "System",
        "status": "active",
        "tools": [
            {"name": "scan_code", "description": "Scan code for security vulnerabilities", "input_schema": {"type": "object", "properties": {"code": {"type": "string"}, "language": {"type": "string"}}}},
            {"name": "check_config", "description": "Check configuration for security issues", "input_schema": {"type": "object", "properties": {"config": {"type": "object"}, "config_type": {"type": "string"}}}}
        ],
        "prompts": [],
        "resources": [],
        "mcp_config": {"transport": "stdio"},
        "source": "manual",
        "metadata": {"popularity": 91}
    },
    {
        "id": "skill-ai-image-gen",
        "name": "AI Image Generation",
        "description": "Generate, edit, and transform images using AI models with detailed prompting capabilities",
        "category": "Creative",
        "icon": "🎨",
        "icon_bg_color": "#ec4899",
        "tags": ["ai", "image", "generation", "creative", "art", "stable-diffusion"],
        "version": "2.3.0",
        "author": "System",
        "status": "active",
        "tools": [
            {"name": "generate_image", "description": "Generate image from text prompt", "input_schema": {"type": "object", "properties": {"prompt": {"type": "string"}, "style": {"type": "string"}, "size": {"type": "string"}}}},
            {"name": "edit_image", "description": "Edit existing image with instructions", "input_schema": {"type": "object", "properties": {"image_url": {"type": "string"}, "instruction": {"type": "string"}}}}
        ],
        "prompts": [],
        "resources": [],
        "mcp_config": {"transport": "sse", "url": "http://localhost:8003/mcp"},
        "source": "manual",
        "metadata": {"popularity": 79}
    }
]


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for field in ["tags", "tools", "prompts", "resources", "mcp_config", "metadata"]:
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = [] if field in ["tags", "tools", "prompts", "resources"] else {}
    return d


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'General',
                icon TEXT DEFAULT '🔧',
                icon_bg_color TEXT DEFAULT '#6366f1',
                tags TEXT DEFAULT '[]',
                version TEXT DEFAULT '1.0.0',
                author TEXT DEFAULT 'Unknown',
                status TEXT DEFAULT 'active',
                tools TEXT DEFAULT '[]',
                prompts TEXT DEFAULT '[]',
                resources TEXT DEFAULT '[]',
                mcp_config TEXT DEFAULT '{}',
                source TEXT DEFAULT 'manual',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        for skill in SAMPLE_SKILLS:
            now = datetime.utcnow().isoformat()
            existing = conn.execute("SELECT id FROM skills WHERE id = ?", (skill["id"],)).fetchone()
            if not existing:
                conn.execute("""
                    INSERT INTO skills
                    (id, name, description, category, icon, icon_bg_color, tags, version, author, status,
                     tools, prompts, resources, mcp_config, source, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    skill["id"], skill["name"], skill.get("description", ""),
                    skill.get("category", "General"), skill.get("icon", "🔧"),
                    skill.get("icon_bg_color", "#6366f1"),
                    json.dumps(skill.get("tags", [])),
                    skill.get("version", "1.0.0"), skill.get("author", "Unknown"),
                    skill.get("status", "active"),
                    json.dumps(skill.get("tools", [])),
                    json.dumps(skill.get("prompts", [])),
                    json.dumps(skill.get("resources", [])),
                    json.dumps(skill.get("mcp_config", {})),
                    skill.get("source", "manual"),
                    json.dumps(skill.get("metadata", {})),
                    now, now
                ))
