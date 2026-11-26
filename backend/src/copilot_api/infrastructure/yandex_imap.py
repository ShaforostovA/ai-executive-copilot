import asyncio
import email
import imaplib
import ssl
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import Protocol

from pydantic import BaseModel


class YandexIMAPError(Exception):
    pass


class YandexIMAPAuthenticationError(YandexIMAPError):
    pass


class MailboxMessage(BaseModel):
    uid: int
    uid_validity: str
    external_id: str
    subject: str
    content: str
    timestamp: datetime


class MailboxBatch(BaseModel):
    uid_validity: str
    messages: list[MailboxMessage]


class IMAPClient(Protocol):
    async def fetch_new(
        self,
        username: str,
        password: str,
        folder: str,
        uid_validity: str | None,
        last_uid: int,
        limit: int,
    ) -> MailboxBatch:
        pass


class YandexIMAPClient:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    async def fetch_new(
        self,
        username: str,
        password: str,
        folder: str,
        uid_validity: str | None,
        last_uid: int,
        limit: int,
    ) -> MailboxBatch:
        return await asyncio.to_thread(
            self._fetch_sync,
            username,
            password,
            folder,
            uid_validity,
            last_uid,
            limit,
        )

    def _fetch_sync(
        self,
        username: str,
        password: str,
        folder: str,
        uid_validity: str | None,
        last_uid: int,
        limit: int,
    ) -> MailboxBatch:
        client = imaplib.IMAP4_SSL(
            self.host,
            self.port,
            ssl_context=ssl.create_default_context(),
        )
        try:
            client.login(username, password)
            status, _ = client.select(folder, readonly=True)
            if status != "OK":
                raise YandexIMAPError("Mailbox folder cannot be opened read-only.")
            raw_validity = client.response("UIDVALIDITY")[1]
            current_validity = (
                raw_validity[0].decode("ascii") if raw_validity and raw_validity[0] else "unknown"
            )
            if uid_validity is not None and uid_validity != current_validity:
                last_uid = 0
            status, data = client.uid("search", None, f"UID {last_uid + 1}:*")
            if status != "OK":
                raise YandexIMAPError("Mailbox UID search failed.")
            uids = sorted(int(value) for value in data[0].split())[:limit]
            messages = [self._fetch_message(client, uid, current_validity) for uid in uids]
            return MailboxBatch(uid_validity=current_validity, messages=messages)
        except imaplib.IMAP4.error as exc:
            raise YandexIMAPAuthenticationError("Mailbox authentication failed.") from exc
        except (imaplib.IMAP4.abort, OSError) as exc:
            raise YandexIMAPError("Mailbox connection failed.") from exc
        finally:
            try:
                client.logout()
            except (imaplib.IMAP4.error, OSError):
                pass

    @staticmethod
    def _fetch_message(
        client: imaplib.IMAP4_SSL,
        uid: int,
        uid_validity: str,
    ) -> MailboxMessage:
        status, data = client.uid("fetch", str(uid), "(RFC822)")
        if status != "OK":
            raise YandexIMAPError("Mailbox message fetch failed.")
        raw = next(
            (item[1] for item in data if isinstance(item, tuple) and isinstance(item[1], bytes)),
            None,
        )
        if raw is None:
            raise YandexIMAPError("Mailbox returned an empty message.")
        message = email.message_from_bytes(raw)
        timestamp = parsedate_to_datetime(message.get("Date"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        return MailboxMessage(
            uid=uid,
            uid_validity=uid_validity,
            external_id=f"{uid_validity}:{uid}",
            subject=str(make_header(decode_header(message.get("Subject", "No subject")))),
            content=_plain_text(message),
            timestamp=timestamp,
        )


def _plain_text(message: Message) -> str:
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.get_content_type() == "text/plain" and not part.get_filename():
            payload = part.get_payload(decode=True) or b""
            return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    return "(No plain-text content)"
