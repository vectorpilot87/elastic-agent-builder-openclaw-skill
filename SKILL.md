---
name: elastic-agent-builder
description: Query and converse with Elastic Agent Builder APIs using environment-based auth from a .env file. Use when users want to list Agent Builder agents or send converse requests to Kibana endpoints /api/agent_builder/agents and /api/agent_builder/converse.
---

# elastic-agent-builder

Use this skill to call Elastic Agent Builder APIs with credentials from `.env`.

## Required env vars

Create `.env` in the working directory (or where the script runs):

```env
KIBANA_URL=https://your-kibana-host
KIBANA_API_KEY=your_api_key_here
KIBANA_SPACE_ID=default
KIBANA_VERIFY_SSL=true
KIBANA_TIMEOUT_S=300
DEFAULT_AGENT_ID=elastic-ai-agent
```

Aliases supported:
- `ELASTICSEARCH_URL` instead of `KIBANA_URL`
- `ELASTICSEARCH_API_KEY` or `API_KEY` instead of `KIBANA_API_KEY`
- `ELASTIC_SPACE_ID` instead of `KIBANA_SPACE_ID`
- `ELASTIC_VERIFY_SSL` instead of `KIBANA_VERIFY_SSL`
- `ELASTIC_TIMEOUT_S` instead of `KIBANA_TIMEOUT_S`

## Commands

List agents:

```bash
python3 /home/username/.openclaw/workspace/skills/elastic-agent-builder/scripts/elastic_agent_builder.py list-agents
```

Converse:

```bash
python3 /home/usernsame/.openclaw/workspace/skills/elastic-agent-builder/scripts/elastic_agent_builder.py \
  converse \
  --agent-id "<agent_id>" \
  --input "Hello from Agent Builder"
```

Interactive chat mode:

```bash
python3 /home/username/.openclaw/workspace/skills/elastic-agent-builder/scripts/elastic_agent_builder.py chat
```

Chat commands:
- `/elastic-agents` list and choose agent
- `/elastic-agent` show current agent
- `/elastic-new` reset conversation id
- `/elastic-help` help
- `/exit` quit

Optional converse fields:
- `--conversation-id`
- `--connector-id`
- `--configuration-overrides '{"key":"value"}'`
- `--prompts '{"system":"..."}'`

## Notes

- Uses `kbn-xsrf: true` for POST requests.
- Supports Kibana Spaces via `ELASTIC_SPACE_ID`.
- Prints JSON response to stdout.
