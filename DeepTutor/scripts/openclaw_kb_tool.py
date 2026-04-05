#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenClaw Knowledge Base Tool Function

A simple Python function that accesses the running Knowledge Base API server via HTTP.
This provides a single entry point for querying the DeepTutor Knowledge Base API.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _http_post_json(url: str, payload: Dict[str, Any], timeout: int = 300) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def _http_get_json(url: str, timeout: int = 300) -> Dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def query_knowledge_base(
    query: str,
    kb_name: Optional[str] = None,
    mode: str = "hybrid",
    base_url: str = "http://192.168.10.115:8090",
    session_id: Optional[str] = None,
    enable_web_search: bool = False,
) -> str:
    """
    Query the DeepTutor Knowledge Base API via HTTP.

    This function can be registered as a tool in OpenClaw or other agent frameworks.
    It makes HTTP requests to the running knowledge_api_tool.py server.

    The first query can omit `session_id`; the server will create a new chat session
    automatically and return `session_id` in the response. Subsequent queries on the
    same topic can pass that `session_id` to reuse the session and preserve context.

    Args:
        query: The search query to execute
        kb_name: Name of the knowledge base to query (optional, uses default if not provided)
        mode: Search mode - "hybrid", "local", "global", or "naive"
        base_url: Base URL of the running Knowledge Base API server (default: http://192.168.10.115:8090)
        session_id: Optional session ID for conversation continuity
        enable_web_search: Whether to enable web search in addition to KB search

    Returns:
        JSON string containing the `answer`, `session_id`, and optional error information

    Example:
        result = query_knowledge_base(
            query="What is machine learning?",
            kb_name="AI_Knowledge",
        )
        print(result)
    """
    try:
        payload = {
            "query": query,
            "kb_name": kb_name,
            "mode": mode,
            "session_id": session_id,
            "history": [],
            "enable_web_search": enable_web_search,
        }
        result = _http_post_json(f"{base_url}/query", payload, timeout=600)

        if result.get("success", False):
            answer = result.get("answer", "")
            sid = result.get("session_id")
            self_response = {"answer": answer, "session_id": sid}
            logger.info(f"Query successful: '{query[:50]}...' -> {len(answer)} chars, session_id={sid}")
            return json.dumps(self_response)
        else:
            error_msg = f"Knowledge Base Query Error: {result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        error_msg = f"HTTP Error {e.code}: {error_body}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except urllib.error.URLError as e:
        error_msg = f"HTTP Request Error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Knowledge Base Tool Error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def list_knowledge_bases(base_url: str = "http://192.168.10.115:8090") -> str:
    """
    List all available knowledge bases via HTTP.

    Args:
        base_url: Base URL of the running Knowledge Base API server

    Returns:
        JSON string containing list of knowledge base names
    """
    try:
        result = _http_get_json(f"{base_url}/knowledge-bases/names", timeout=300)
        return json.dumps(result)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        error_msg = f"HTTP Error {e.code}: {error_body}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except urllib.error.URLError as e:
        error_msg = f"Error listing knowledge bases: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Knowledge Base Tool Error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def query_kb_chunks(
    query: str,
    kb_name: Optional[str] = None,
    mode: str = "hybrid",
    top_k: int = 5,
    provider: Optional[str] = None,
    base_url: str = "http://192.168.10.115:8090",
) -> str:
    """
    Query the knowledge base chunks retrieval endpoint via HTTP.

    Args:
        query: The search query to execute
        kb_name: Name of the knowledge base to query (optional)
        mode: Search mode - "hybrid", "local", "global", or "naive"
        top_k: Number of chunks to retrieve
        provider: Optional RAG provider override
        base_url: Base URL of the running Knowledge Base API server

    Returns:
        JSON string containing chunk extraction results or error message
    """
    try:
        payload = {
            "query": query,
            "kb_name": kb_name,
            "mode": mode,
            "top_k": top_k,
            "provider": provider,
        }
        result = _http_post_json(f"{base_url}/query-chunks", payload, timeout=600)
        return json.dumps(result)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        error_msg = f"HTTP Error {e.code}: {error_body}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except urllib.error.URLError as e:
        error_msg = f"HTTP Request Error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Knowledge Base Tool Error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def get_kb_info(kb_name: str, base_url: str = "http://192.168.10.115:8090") -> str:
    """
    Get detailed information about a specific knowledge base via HTTP.

    Args:
        kb_name: Name of the knowledge base
        base_url: Base URL of the running Knowledge Base API server

    Returns:
        JSON string containing KB information
    """
    try:
        result = _http_get_json(f"{base_url}/knowledge-bases/{urllib.parse.quote(kb_name)}", timeout=300)
        return json.dumps(result)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        error_msg = f"HTTP Error {e.code}: {error_body}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except urllib.error.URLError as e:
        error_msg = f"Error getting KB info: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Knowledge Base Tool Error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def get_kb_status(base_url: str = "http://192.168.10.115:8090") -> str:
    """
    Get overall knowledge base system status via HTTP.

    Args:
        base_url: Base URL of the running Knowledge Base API server

    Returns:
        JSON string containing system status
    """
    try:
        result = _http_get_json(f"{base_url}/status", timeout=300)
        return json.dumps(result)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        error_msg = f"HTTP Error {e.code}: {error_body}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except urllib.error.URLError as e:
        error_msg = f"Error getting KB status: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Knowledge Base Tool Error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def list_chat_sessions(base_url: str = "http://192.168.10.115:8090", limit: int = 20) -> str:
    """
    List chat sessions via HTTP.

    Args:
        base_url: Base URL of the running Knowledge Base API server
        limit: Maximum number of sessions to return

    Returns:
        JSON string containing list of chat sessions
    """
    try:
        query_string = urllib.parse.urlencode({"limit": limit})
        result = _http_get_json(f"{base_url}/sessions?{query_string}", timeout=300)
        return json.dumps(result)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        error_msg = f"HTTP Error {e.code}: {error_body}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except urllib.error.URLError as e:
        error_msg = f"Error listing chat sessions: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Knowledge Base Tool Error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def get_chat_session(session_id: str, base_url: str = "http://192.168.10.115:8090") -> str:
    """
    Get a specific chat session via HTTP.

    Args:
        session_id: Session ID to retrieve
        base_url: Base URL of the running Knowledge Base API server

    Returns:
        JSON string containing session information
    """
    try:
        result = _http_get_json(f"{base_url}/sessions/{urllib.parse.quote(session_id)}", timeout=300)
        return json.dumps(result)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        error_msg = f"HTTP Error {e.code}: {error_body}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except urllib.error.URLError as e:
        error_msg = f"Error getting chat session: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Knowledge Base Tool Error: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


# ============================================================================
# OpenClaw Tool Registration Helper
# ============================================================================

def create_openclaw_tool(base_url: str = "http://192.168.10.115:8090", default_kb: Optional[str] = None):
    """
    Create a tool configuration for OpenClaw registration.

    Args:
        base_url: Base URL of the running Knowledge Base API server
        default_kb: Default knowledge base name to use

    Returns:
        Dictionary containing tool configuration for OpenClaw
    """
    def query_tool(
        query: str,
        kb_name: Optional[str] = None,
        mode: str = "hybrid",
        session_id: Optional[str] = None,
    ) -> str:
        """OpenClaw tool function for querying knowledge base."""
        kb = kb_name or default_kb
        return query_knowledge_base(
            query=query,
            kb_name=kb,
            mode=mode,
            session_id=session_id,
            base_url=base_url
        )

    def list_tool() -> str:
        """OpenClaw tool function for listing knowledge bases."""
        return list_knowledge_bases(base_url=base_url)

    def info_tool(kb_name: str) -> str:
        """OpenClaw tool function for getting KB information."""
        return get_kb_info(kb_name=kb_name, base_url=base_url)

    def chunks_tool(
        query: str,
        kb_name: Optional[str] = None,
        mode: str = "hybrid",
        top_k: int = 5,
        provider: Optional[str] = None,
    ) -> str:
        """OpenClaw tool function for querying KB chunks."""
        return query_kb_chunks(
            query=query,
            kb_name=kb_name,
            mode=mode,
            top_k=top_k,
            provider=provider,
            base_url=base_url,
        )

    def status_tool() -> str:
        """OpenClaw tool function for getting system status."""
        return get_kb_status(base_url=base_url)

    def list_sessions_tool(limit: int = 20) -> str:
        """OpenClaw tool function for listing chat sessions."""
        return list_chat_sessions(base_url=base_url, limit=limit)

    def get_session_tool(session_id: str) -> str:
        """OpenClaw tool function for getting session information."""
        return get_chat_session(session_id=session_id, base_url=base_url)

    return {
        "name": "knowledge_base",
        "description": "Query and manage DeepTutor knowledge bases via HTTP API",
        "functions": {
            "query": {
                "callable": query_tool,
                "description": "Search a knowledge base with a query",
                "parameters": {
                    "query": {"type": "string", "description": "What to search for", "required": True},
                    "kb_name": {"type": "string", "description": "Knowledge base name (optional)", "required": False},
                    "mode": {"type": "string", "description": "Search mode", "default": "hybrid", "required": False},
                    "session_id": {"type": "string", "description": "Optional conversation session ID for context reuse", "required": False},
                },
            },
            "list": {
                "callable": list_tool,
                "description": "List all available knowledge bases",
                "parameters": {},
            },
            "info": {
                "callable": info_tool,
                "description": "Get information about a specific knowledge base",
                "parameters": {
                    "kb_name": {"type": "string", "description": "Knowledge base name", "required": True},
                },
            },
            "chunks": {
                "callable": chunks_tool,
                "description": "Extract retrieval chunks for a query from the knowledge base",
                "parameters": {
                    "query": {"type": "string", "description": "Search query", "required": True},
                    "kb_name": {"type": "string", "description": "Knowledge base name (optional)", "required": False},
                    "mode": {"type": "string", "description": "Search mode", "default": "hybrid", "required": False},
                    "top_k": {"type": "integer", "description": "Number of chunks to retrieve", "default": 5, "required": False},
                    "provider": {"type": "string", "description": "Optional RAG provider override", "required": False},
                },
            },
            "status": {
                "callable": status_tool,
                "description": "Get overall system status",
                "parameters": {},
            },
            "list_sessions": {
                "callable": list_sessions_tool,
                "description": "List chat sessions",
                "parameters": {
                    "limit": {"type": "integer", "description": "Maximum sessions to return", "default": 20, "required": False},
                },
            },
            "get_session": {
                "callable": get_session_tool,
                "description": "Get information about a specific chat session",
                "parameters": {
                    "session_id": {"type": "string", "description": "Session ID", "required": True},
                },
            },
        }
    }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="OpenClaw Knowledge Base Tool - HTTP client for DeepTutor KB API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python openclaw_kb_tool.py --help
  python openclaw_kb_tool.py --list-functions
  python openclaw_kb_tool.py --test
  python openclaw_kb_tool.py query "What is machine learning?" --kb "AI_KB"
  python openclaw_kb_tool.py list
  python openclaw_kb_tool.py info "NVIDIA"
        """
    )

    parser.add_argument(
        "--url",
        default="http://192.168.10.115:8090",
        help="API server URL (default: http://192.168.10.115:8090)"
    )

    parser.add_argument(
        "--list-functions",
        action="store_true",
        help="List all available functions and their parameters"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run basic connectivity test"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query a knowledge base")
    query_parser.add_argument("query", help="Search query")
    query_parser.add_argument("--kb", help="Knowledge base name")
    query_parser.add_argument(
        "--mode",
        default="hybrid",
        choices=["hybrid", "local", "global", "naive"],
        help="Search mode (default: hybrid)"
    )
    query_parser.add_argument("--session-id", help="Session ID for conversation continuity")

    # List command
    subparsers.add_parser("list", help="List all knowledge bases")

    # Info command
    info_parser = subparsers.add_parser("info", help="Get knowledge base information")
    info_parser.add_argument("kb_name", help="Knowledge base name")

    # Chunks command
    chunks_parser = subparsers.add_parser("chunks", help="Extract knowledge base chunks for a query")
    chunks_parser.add_argument("query", help="Search query")
    chunks_parser.add_argument("--kb", help="Knowledge base name")
    chunks_parser.add_argument(
        "--mode",
        default="hybrid",
        choices=["hybrid", "local", "global", "naive"],
        help="Search mode (default: hybrid)"
    )
    chunks_parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    chunks_parser.add_argument("--provider", help="Optional RAG provider override")

    # Status command
    subparsers.add_parser("status", help="Get system status")

    # Sessions command
    sessions_parser = subparsers.add_parser("sessions", help="List chat sessions")
    sessions_parser.add_argument("--limit", type=int, default=20, help="Maximum sessions to return")

    # Session command
    session_parser = subparsers.add_parser("session", help="Get session information")
    session_parser.add_argument("session_id", help="Session ID")

    args = parser.parse_args()

    if args.list_functions:
        print("OpenClaw Knowledge Base Tool - Available Functions")
        print("=" * 60)

        tool = create_openclaw_tool(base_url=args.url)

        for func_name, func_config in tool["functions"].items():
            print(f"\n{func_name.upper()}:")
            print(f"  Description: {func_config['description']}")
            print("  Parameters:")

            params = func_config.get("parameters", {})
            if params:
                for param_name, param_info in params.items():
                    required = " (required)" if param_info.get("required", False) else ""
                    default = f" (default: {param_info.get('default', 'None')})" if "default" in param_info else ""
                    print(f"    - {param_name}: {param_info.get('description', '')}{required}{default}")
            else:
                print("    - None")

            print(f"  Returns: {func_config.get('returns', 'String')}")

        print(f"\nAPI Server: {args.url}")
        print("\nTo use in OpenClaw:")
        print("from openclaw_kb_tool import create_openclaw_tool")
        print("tool = create_openclaw_tool()")
        print("# Register tool['functions'] with your agent")

    elif args.test:
        print("OpenClaw Knowledge Base Tool - Connectivity Test")
        print("=" * 50)

        try:
            # Test health endpoint
            print("\n1. Testing API connectivity...")
            status = get_kb_status(args.url)
            status_data = json.loads(status)
            if "error" not in status_data:
                print("✓ API server is accessible")
                print(f"  Health: {status_data.get('health', {}).get('status', 'unknown')}")
                print(f"  Knowledge bases: {status_data.get('total_kbs', 0)}")
            else:
                print(f"✗ API server error: {status_data['error']}")
                exit(1)

            # Test list KBs
            print("\n2. Testing knowledge base listing...")
            kb_list = list_knowledge_bases(args.url)
            kb_data = json.loads(kb_list)
            if "error" not in kb_data:
                kbs = kb_data.get("knowledge_bases", [])
                print(f"✓ Found {len(kbs)} knowledge bases: {kbs}")
            else:
                print(f"✗ KB listing error: {kb_data['error']}")

            # Test query (if KBs available)
            if "error" not in kb_data and kb_data.get("knowledge_bases"):
                print("\n3. Testing query functionality...")
                kb_name = kb_data["knowledge_bases"][0]
                result = query_knowledge_base("test query", kb_name=kb_name, base_url=args.url)
                if "Error" not in result:
                    print(f"✓ Query successful ({len(result)} chars)")
                else:
                    print(f"⚠ Query returned: {result[:100]}...")

            print("\n✓ All tests completed!")

        except Exception as e:
            print(f"✗ Test failed: {e}")
            exit(1)

    elif args.command == "query":
        result = query_knowledge_base(
            query=args.query,
            kb_name=args.kb,
            mode=args.mode,
            session_id=getattr(args, 'session_id', None),
            base_url=args.url
        )
        print(result)

    elif args.command == "list":
        result = list_knowledge_bases(args.url)
        print(result)

    elif args.command == "info":
        result = get_kb_info(args.kb_name, args.url)
        print(result)

    elif args.command == "chunks":
        result = query_kb_chunks(
            query=args.query,
            kb_name=args.kb,
            mode=args.mode,
            top_k=args.top_k,
            provider=args.provider,
            base_url=args.url,
        )
        print(result)

    elif args.command == "status":
        result = get_kb_status(args.url)
        print(result)

    elif args.command == "sessions":
        result = list_chat_sessions(args.url, args.limit)
        print(result)

    elif args.command == "session":
        result = get_chat_session(args.session_id, args.url)
        print(result)

    else:
        # Default behavior - show help
        parser.print_help()