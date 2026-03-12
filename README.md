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

## Deployment automation

For a VPS deployment, use `systemd` instead of `cron`. The bot runs as a long-lived Socket Mode process, so it should restart automatically on crashes and on host reboot.

### pyenv-based service

Find the exact interpreter managed by `pyenv`:

```bash
pyenv which python
```

Example output:

```bash
/home/your-user/.pyenv/versions/3.11.9/envs/rootme-bot/bin/python
```

Create `/etc/systemd/system/slack-rootme-bot.service` with the absolute `pyenv` interpreter path:

```ini
[Unit]
Description=Root-Me Slack Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/slack_rootme_bot
EnvironmentFile=/opt/slack_rootme_bot/.env
ExecStart=/home/your-user/.pyenv/versions/3.11.9/envs/rootme-bot/bin/python /opt/slack_rootme_bot/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now slack-rootme-bot
sudo systemctl status slack-rootme-bot
```

Inspect failures with:

```bash
journalctl -xeu slack-rootme-bot.service
```

### Why not cron

`cron` can start the bot at boot with `@reboot`, but it is fragile with `pyenv` because it does not load your interactive shell environment by default. `systemd` is the recommended process manager for this project.

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
