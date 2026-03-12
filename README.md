# Root-Me Ranking Slack Bot

Slack bot for a private group that wants to track Root-Me progress directly from Slack.

## Milestone 1 scope

M1 provides the project bootstrap:

- Python project structure aligned with the PRD
- environment-based configuration loading
- Slack Bolt app startup in Socket Mode
- `/rootme help` slash-command support

M2 adds the live Root-Me integration for:

- `/rootme ranking`
- `/rootme profile <username>`

M3 adds tracked member management:

- `/rootme add <username>`
- `/rootme remove <username>`
- interactive delete confirmation buttons

The ranking is refreshed in the background and served from cached database snapshots instead of live Root-Me calls.

## Requirements

- Python 3.11+
- A Slack app configured for Socket Mode
- Slack credentials and a Root-Me API key exported in the environment or stored in `.env`

## Setup

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in the values.
4. In Slack, create a slash command named `/rootme`, or import the provided manifest.

Instead of configuring the app manually, you can import the manifest from [slack-app-manifest.yaml](/Users/cyrillefranchet/sas/repos/external/slack_rootme_bot/slack-app-manifest.yaml).

Recommended OAuth scopes:

- `commands`
- `chat:write`

Recommended Socket Mode setting:

- Enable Socket Mode and create an app-level token with the `connections:write` scope.
- Keep interactivity enabled in the Slack app because `/rootme remove <username>` uses buttons.

## Slack app manifest

This repository includes [slack-app-manifest.yaml](/Users/cyrillefranchet/sas/repos/external/slack_rootme_bot/slack-app-manifest.yaml) for Slack app creation.

Import it from the Slack app admin UI:

1. Go to `api.slack.com/apps`.
2. Click `Create New App`.
3. Choose `From an app manifest`.
4. Select your workspace.
5. Paste the contents of `slack-app-manifest.yaml`.
6. Create the app, then install it to the workspace.

After import, you still need to create the Socket Mode app-level token manually:

1. Open the app in Slack.
2. Go to `Basic Information`.
3. Under `App-Level Tokens`, generate a token with the `connections:write` scope.
4. Store it as `SLACK_APP_TOKEN` in `.env`.

The manifest also enables interactivity, which is required for the `/rootme remove <username>` confirmation buttons.

## Run

```bash
python main.py
```

When the bot is connected, run `/rootme help` in Slack to verify the integration.

## Commands

- `/rootme help` shows the supported commands.
- `/rootme ranking` reads cached ranking snapshots from SQLite and posts the leaderboard in-channel.
- `/rootme profile <username>` fetches a single Root-Me profile and returns the details as an ephemeral reply.
- `/rootme add <rootme_id>` fetches a Root-Me profile by numeric ID, shows the details, then requires confirmation before storing it in SQLite.
- `/rootme list` shows the tracked Root-Me members and who added them.
- `/rootme remove <username>` opens a confirmation prompt with interactive buttons before deletion.

French aliases are also supported:

- `/rootme aide`
- `/rootme classement`
- `/rootme profil <username>`
- `/rootme ajouter <rootme_id>`
- `/rootme liste`
- `/rootme supprimer <username>`

## Ranking cache

The bot refreshes ranking snapshots in the background every hour by default and stores them in SQLite. Adjust the schedule with `RANKING_REFRESH_INTERVAL_SECONDS` in `.env`.

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
