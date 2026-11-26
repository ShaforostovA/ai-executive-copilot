import argparse
import asyncio
import os

from copilot_api.core.config import Settings
from copilot_api.infrastructure.yandex_imap import YandexIMAPClient


async def smoke(confirm_read_only: bool, limit: int) -> None:
    if not confirm_read_only:
        raise SystemExit("Pass --confirm-read-only only after mailbox owner approval.")
    username = os.environ["YANDEX_EMAIL"]
    password = os.environ["YANDEX_APP_PASSWORD"]
    settings = Settings()
    folder = os.getenv("YANDEX_FOLDER", "INBOX")
    if folder not in settings.allowed_folder_set:
        raise SystemExit("YANDEX_FOLDER is not allowed.")
    client = YandexIMAPClient(
        settings.yandex_imap_host,
        settings.yandex_imap_port,
    )
    batch = await client.fetch_new(
        username,
        password,
        folder,
        uid_validity=None,
        last_uid=0,
        limit=limit,
    )
    print(
        f"Read-only IMAP smoke passed: UIDVALIDITY={batch.uid_validity}, "
        f"message_count={len(batch.messages)}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-read-only", action="store_true")
    parser.add_argument("--limit", type=int, default=1, choices=range(1, 6))
    args = parser.parse_args()
    asyncio.run(smoke(args.confirm_read_only, args.limit))
