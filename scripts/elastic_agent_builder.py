#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool = True) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y", "on")


class AgentBuilderClient:
    """Elastic Agent Builder (Kibana) API client.

    Endpoints:
    - GET /api/agent_builder/agents
    - POST /api/agent_builder/converse
    """

    def __init__(
        self,
        kibana_url: str,
        api_key: str,
        space_id: Optional[str] = None,
        verify_ssl: bool = True,
        timeout_s: int = 300,
    ):
        self.kibana_url = kibana_url.rstrip("/")
        self.space_id = space_id
        self.verify_ssl = verify_ssl
        self.timeout_s = timeout_s
        self.base_path = f"/s/{space_id}" if space_id else ""

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"ApiKey {api_key}",
                "Content-Type": "application/json",
                "kbn-xsrf": "true",
            }
        )

    def _url(self, path: str) -> str:
        return f"{self.kibana_url}{self.base_path}{path}"

    def list_agents(self) -> List[Dict[str, Any]]:
        url = self._url("/api/agent_builder/agents")
        resp = self.session.get(url, verify=self.verify_ssl, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, dict):
            if isinstance(data.get("results"), list):
                return data["results"]
            if isinstance(data.get("agents"), list):
                return data["agents"]
            return [data]
        if isinstance(data, list):
            return data
        return []

    def converse(
        self,
        input_text: str,
        agent_id: str,
        conversation_id: Optional[str] = None,
        connector_id: Optional[str] = None,
        configuration_overrides: Optional[Dict[str, Any]] = None,
        prompts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = self._url("/api/agent_builder/converse")
        payload: Dict[str, Any] = {"input": input_text, "agent_id": agent_id}
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if connector_id:
            payload["connector_id"] = connector_id
        if configuration_overrides:
            payload["configuration_overrides"] = configuration_overrides
        if prompts:
            payload["prompts"] = prompts

        resp = self.session.post(
            url,
            data=json.dumps(payload),
            verify=self.verify_ssl,
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        return resp.json()


def format_agent_row(agent: Dict[str, Any]) -> Tuple[str, str, str]:
    agent_id = str(agent.get("id") or agent.get("agent_id") or agent.get("uuid") or "")
    name = str(agent.get("name") or agent.get("title") or agent.get("display_name") or "(unnamed)")
    desc = str(agent.get("description") or agent.get("summary") or "")
    return agent_id, name, desc


def print_help() -> None:
    print(
        "Commands:\n"
        "  /elastic-agents  List agents and choose one\n"
        "  /elastic-agent   Show current agent\n"
        "  /elastic-new     Start a new conversation\n"
        "  /elastic-help    Show this help\n"
        "  /exit            Quit"
    )


def choose_agent_interactively(client: AgentBuilderClient) -> Optional[Tuple[str, str]]:
    agents = client.list_agents()
    if not agents:
        print("No agents found from /api/agent_builder/agents")
        return None

    rows = [format_agent_row(a) for a in agents]
    print("Available agents:")
    for idx, (aid, name, desc) in enumerate(rows, start=1):
        short_desc = (desc[:80] + "…") if len(desc) > 80 else desc
        if short_desc:
            print(f"  [{idx}] {name} ({aid}) — {short_desc}")
        else:
            print(f"  [{idx}] {name} ({aid})")

    while True:
        raw = input("Pick agent number (Enter to cancel): ").strip()
        if raw == "":
            return None
        if not raw.isdigit():
            print("Please enter a number")
            continue
        n = int(raw)
        if n < 1 or n > len(rows):
            print(f"Choose a number between 1 and {len(rows)}")
            continue
        agent_id, name, _ = rows[n - 1]
        if not agent_id:
            print("Selected agent has no id, choose another")
            continue
        return agent_id, name


def _safe_error_body(e: Exception) -> str:
    if isinstance(e, requests.HTTPError) and getattr(e, "response", None) is not None:
        try:
            return e.response.text
        except Exception:
            return str(e)
    return str(e)


def _extract_assistant_text(resp: Dict[str, Any]) -> str:
    for key in ["response", "output", "text", "message", "answer"]:
        v = resp.get(key)
        if isinstance(v, str) and v.strip():
            return v
    if isinstance(resp.get("messages"), list):
        msgs = resp["messages"]
        for m in reversed(msgs):
            if isinstance(m, dict):
                content = m.get("content")
                if isinstance(content, str) and content.strip():
                    return content
    return json.dumps(resp, ensure_ascii=False)


def _build_client() -> AgentBuilderClient:
    kibana_url = os.getenv("ELASTICSEARCH_URL") or os.getenv("KIBANA_URL")
    api_key = os.getenv("ELASTICSEARCH_API_KEY") or os.getenv("KIBANA_API_KEY") or os.getenv("API_KEY")

    if not kibana_url or not api_key:
        print(
            "Missing KIBANA_URL/ELASTICSEARCH_URL or KIBANA_API_KEY/ELASTICSEARCH_API_KEY\n"
            "Add to .env:\n"
            "  KIBANA_URL=https://your-kibana:5601\n"
            "  KIBANA_API_KEY=...\n"
            "Optional:\n"
            "  KIBANA_SPACE_ID=default\n"
            "  KIBANA_VERIFY_SSL=true\n"
            "  DEFAULT_AGENT_ID=elastic-ai-agent"
        )
        raise SystemExit(1)

    space_id = os.getenv("ELASTIC_SPACE_ID") or os.getenv("KIBANA_SPACE_ID") or None
    verify_ssl = _bool_env("ELASTIC_VERIFY_SSL", _bool_env("KIBANA_VERIFY_SSL", True))
    timeout_s = int(os.getenv("ELASTIC_TIMEOUT_S", os.getenv("KIBANA_TIMEOUT_S", "300")))

    return AgentBuilderClient(
        kibana_url=kibana_url,
        api_key=api_key,
        space_id=space_id,
        verify_ssl=verify_ssl,
        timeout_s=timeout_s,
    )


def run_chat(client: AgentBuilderClient) -> None:
    current_agent_id = os.getenv("DEFAULT_AGENT_ID", "elastic-ai-agent").strip()
    current_agent_name = current_agent_id
    conversation_id: Optional[str] = None

    print("Connected to Kibana")
    print_help()
    print(f"Current agent: {current_agent_name} ({current_agent_id})")

    while True:
        user_input = input("you> ").strip()
        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("/exit", "/quit"):
            print("Bye!")
            break
        if cmd == "/elastic-help":
            print_help()
            continue
        if cmd == "/elastic-new":
            conversation_id = None
            print("(Started new conversation)")
            continue
        if cmd == "/elastic-agent":
            print(f"Current agent: {current_agent_name} ({current_agent_id})")
            continue
        if cmd == "/elastic-agents":
            try:
                picked = choose_agent_interactively(client)
            except Exception as e:
                print("agent> [failed to list agents]")
                print(_safe_error_body(e))
                continue
            if picked is None:
                print("(No change)")
                continue
            current_agent_id, current_agent_name = picked
            conversation_id = None
            print(f"(Selected agent: {current_agent_name} ({current_agent_id}); conversation reset)")
            continue

        try:
            data = client.converse(
                input_text=user_input,
                agent_id=current_agent_id,
                conversation_id=conversation_id,
            )
        except Exception as e:
            print("agent> [chat failed]")
            print(_safe_error_body(e))
            continue

        conversation_id = data.get("conversation_id") or conversation_id
        message = (data.get("response") or {}).get("message") if isinstance(data, dict) else None
        if message is None:
            print("agent> [no response.message found; dumping full response]")
            print(json.dumps(data, indent=2))
        else:
            print(f"agent> {message}")


def main():
    parser = argparse.ArgumentParser(description="Elastic Agent Builder API CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-agents", help="List Agent Builder agents")
    sub.add_parser("chat", help="Interactive chat with /elastic-* commands")

    c = sub.add_parser("converse", help="Send a converse request")
    c.add_argument("--agent-id", required=True)
    c.add_argument("--input", required=True)
    c.add_argument("--conversation-id")
    c.add_argument("--connector-id")
    c.add_argument("--configuration-overrides", help="JSON object")
    c.add_argument("--prompts", help="JSON object")

    args = parser.parse_args()
    client = _build_client()

    if args.command == "list-agents":
        print(json.dumps(client.list_agents(), indent=2))
        return

    if args.command == "chat":
        run_chat(client)
        return

    configuration_overrides = json.loads(args.configuration_overrides) if args.configuration_overrides else None
    prompts = json.loads(args.prompts) if args.prompts else None

    result = client.converse(
        input_text=args.input,
        agent_id=args.agent_id,
        conversation_id=args.conversation_id,
        connector_id=args.connector_id,
        configuration_overrides=configuration_overrides,
        prompts=prompts,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
