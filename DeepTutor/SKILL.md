---
name: DeepTutor
description: Use this skill to query the DeepTutor knowledge bases and retrieve relevant information for user questions.
---

# DeepTutor Knowledge Base Skill

## When to use this skill
- When the user asks questions that may be answered from internal knowledge bases
- When retrieving structured or stored knowledge is required

---

## Available Actions

### 1. List available knowledge bases
Use this when:
- You don’t know which knowledge base to query
- The user asks what databases are available

Command:
To Fetch the Available Knowledge Base
```bash
/usr/bin/python3 /sandbox/.openclaw-data/skills/DeepTutor/scripts/openclaw_kb_tool.py list
# {"knowledge_bases": ["Database1", "Database2"]}
```
To Fetch Detailed information about the database
```bash
/usr/bin/python3 /sandbox/.openclaw-data/skills/DeepTutor/scripts/openclaw_kb_tool.py info "Database1"
# {"name": "Database1", "path": "/app/data/knowledge_bases/Database1", "is_default": true, "metadata": {"name": "Database1", "created_at": "2026-04-03 04:35:39", "description": "Knowledge base: Database1", "version": "1.0", "rag_provider": "llamaindex", ...}}}
```
To Query the relevent Chunks for the user input.
```bash
/usr/bin/python3 /sandbox/.openclaw-data/skills/DeepTutor/scripts/openclaw_kb_tool.py chunks --kb "<Database1>" --mode hybrid --top-k 1  "User Query"
```
