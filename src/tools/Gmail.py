import re
import threading

from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.create_draft import CreateDraftSchema
from langchain_google_community.gmail.get_message import SearchArgsSchema as GetMessageSchema
from langchain_google_community.gmail.get_thread import GetThreadSchema
from langchain_google_community.gmail.search import SearchArgsSchema
from langchain_google_community.gmail.send_message import SendMessageSchema
from langchain_google_community.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)
from langchain_core.tools import StructuredTool

from dotenv import load_dotenv

load_dotenv(override=True)

_gmail_lock = threading.RLock()
_SENSITIVE_PATTERNS = [
    (re.compile(r"\b(password|passcode|pin)\s*(?:is|:)?\s*[\w-]+", re.IGNORECASE), r"\1 [REDACTED]"),
    (re.compile(r"\b(registration number)\s*(?:is|:)?\s*[\w-]+", re.IGNORECASE), r"\1 [REDACTED]"),
    (re.compile(r"\b\d{6}\b"), "[REDACTED_CODE]"),
]


def gmail_toolkit():
    """Create Gmail tools for reading, searching, drafting, and sending email."""

    credentials = get_gmail_credentials(
        token_file="token.json",
        scopes=["https://mail.google.com/"],
        client_sercret_file="credentials.json",
    )

    api_resource = build_resource_service(
        credentials=credentials
    )

    toolkit = GmailToolkit(
        api_resource=api_resource
    )
    
    return toolkit


def _invoke_gmail_tool(tool_name: str, tool_input: dict):
    """Run Gmail tools with a fresh API resource in the current worker thread."""
    with _gmail_lock:
        tools = gmail_toolkit().get_tools()
        gmail_tool = next(tool for tool in tools if tool.name == tool_name)
        return gmail_tool.invoke(tool_input)


def _redact_sensitive_text(value: str) -> str:
    for pattern, replacement in _SENSITIVE_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _compact_message(message: dict) -> dict:
    compact = {
        "id": message.get("id"),
        "threadId": message.get("threadId"),
        "sender": message.get("sender"),
        "subject": message.get("subject"),
        "snippet": message.get("snippet"),
    }
    return {
        key: _redact_sensitive_text(value) if isinstance(value, str) else value
        for key, value in compact.items()
        if value
    }


def _compact_search_gmail(**kwargs):
    results = _invoke_gmail_tool("search_gmail", kwargs)
    if isinstance(results, list):
        return [_compact_message(result) for result in results]
    return str(results)[:5000]


def _get_gmail_message(**kwargs):
    return _invoke_gmail_tool("get_gmail_message", kwargs)


def _get_gmail_thread(**kwargs):
    return _invoke_gmail_tool("get_gmail_thread", kwargs)


def _create_gmail_draft(**kwargs):
    return _invoke_gmail_tool("create_gmail_draft", kwargs)


def _send_gmail_message(**kwargs):
    return _invoke_gmail_tool("send_gmail_message", kwargs)


def gmail_tools():
    """Create Gmail tools that do not share httplib2 resources across threads."""
    return [
        StructuredTool.from_function(
            func=_compact_search_gmail,
            name="compact_search_gmail",
            description="Search Gmail with compact output. The input must be a valid Gmail query.",
            args_schema=SearchArgsSchema,
        ),
        StructuredTool.from_function(
            func=_get_gmail_message,
            name="get_gmail_message",
            description=(
                "Use this tool to fetch an email by message ID. Returns the "
                "thread ID, snippet, body, subject, and sender."
            ),
            args_schema=GetMessageSchema,
        ),
        StructuredTool.from_function(
            func=_get_gmail_thread,
            name="get_gmail_thread",
            description=(
                "Use this tool to search for email messages. The input must be "
                "a valid Gmail query. The output is a JSON list of messages."
            ),
            args_schema=GetThreadSchema,
        ),
        StructuredTool.from_function(
            func=_create_gmail_draft,
            name="create_gmail_draft",
            description="Use this tool to create a draft email with the provided message fields.",
            args_schema=CreateDraftSchema,
        ),
        StructuredTool.from_function(
            func=_send_gmail_message,
            name="send_gmail_message",
            description="Use this tool to send email messages. The input is the message and recipients.",
            args_schema=SendMessageSchema,
        ),
    ]
