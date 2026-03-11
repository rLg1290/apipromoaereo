import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import Message
from app.parser import parse_message
from app.models import Promotion
from app.storage import Storage


API_ID   = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
GROUP    = os.environ["TELEGRAM_GROUP"]   # username, link de convite ou ID numérico

# Preferência: StringSession (ideal para Docker/VPS, sem arquivo .session)
# Fallback: arquivo local (desenvolvimento local)
_SESSION_STRING = os.environ.get("TELEGRAM_SESSION_STRING", "")
_SESSION_NAME   = os.environ.get("SESSION_NAME", "promo_session")

_client: TelegramClient | None = None


def get_client() -> TelegramClient:
    global _client
    if _client is None:
        session = StringSession(_SESSION_STRING) if _SESSION_STRING else _SESSION_NAME
        _client = TelegramClient(session, API_ID, API_HASH)
    return _client


async def _resolve_group(client: TelegramClient):
    """Resolve the group entity, fetching dialogs first if needed."""
    try:
        return await client.get_entity(int(GROUP) if GROUP.lstrip("-").isdigit() else GROUP)
    except Exception:
        await client.get_dialogs()
        return await client.get_entity(int(GROUP) if GROUP.lstrip("-").isdigit() else GROUP)


async def fetch_history(limit: int = 200) -> list[Promotion]:
    """Fetch the last `limit` messages from the group and parse them."""
    client = get_client()
    await client.start()

    entity = await _resolve_group(client)
    promotions: list[Promotion] = []
    async for message in client.iter_messages(entity, limit=limit):
        if not isinstance(message, Message) or not message.text:
            continue
        promo = parse_message(message.text, message.id)
        if promo:
            promotions.append(promo)

    return promotions


async def listen_new_messages(storage: Storage) -> None:
    """Start listening for new messages in real-time and persist them."""
    client = get_client()
    await client.start()

    entity = await _resolve_group(client)

    @client.on(events.NewMessage(chats=entity))
    async def handler(event: events.NewMessage.Event) -> None:
        text = event.message.text
        if not text:
            return
        promo = parse_message(text, event.message.id)
        if promo:
            storage.save(promo)

    await client.run_until_disconnected()


async def stop_client() -> None:
    global _client
    if _client and _client.is_connected():
        await _client.disconnect()
    _client = None
