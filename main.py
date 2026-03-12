from __future__ import annotations

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import Settings
from db.database import initialize_database
from slack_handlers.commands import register_commands
from slack_handlers.interactions import register_interactions


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_app(settings: Settings) -> App:
    app = App(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
    )
    register_commands(app, settings)
    register_interactions(app, settings)
    return app


def main() -> None:
    settings = Settings.from_env()
    initialize_database(settings.database_path)
    app = create_app(settings)
    handler = SocketModeHandler(app, settings.slack_app_token)
    handler.start()


if __name__ == "__main__":
    main()
