# Root-Me Ranking Slack Bot

Slack bot for a private group that wants to track Root-Me progress directly from Slack.

## Milestone 1 scope

M1 provides the project bootstrap:

- Python project structure aligned with the PRD
- environment-based configuration loading
- Slack Bolt app startup in Socket Mode
- `/rootme help` slash-command support

The ranking, profile, and member management features are intentionally left for later milestones.

## Requirements

- Python 3.11+
- A Slack app configured for Socket Mode
- Slack credentials and a Root-Me API key exported in the environment or stored in `.env`

## Setup

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in the values.
4. In Slack, create a slash command named `/rootme`.

Recommended OAuth scopes:

- `commands`
- `chat:write`

Recommended Socket Mode setting:

- Enable Socket Mode and create an app-level token with the `connections:write` scope.

## Run

```bash
python main.py
```

When the bot is connected, run `/rootme help` in Slack to verify the integration.

## Project layout

```text
.
├── config.py
├── main.py
├── db/
├── services/
├── slack_handlers/
├── tests/
└── utils/
```
