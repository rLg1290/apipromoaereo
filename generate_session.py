"""
Rode este script UMA VEZ localmente (ou na VPS) para gerar a TELEGRAM_SESSION_STRING.
Ele autentica com sua conta pessoal e imprime a string de sessão.

Uso:
    pip install telethon python-dotenv
    python generate_session.py
"""
import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

API_ID   = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]


async def main() -> None:
    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        session_string = client.session.save()

    print("\n" + "=" * 60)
    print("✅  Adicione a linha abaixo ao seu .env:")
    print("=" * 60)
    print(f"\nTELEGRAM_SESSION_STRING={session_string}\n")
    print("=" * 60)
    print("⚠️  Guarde essa string em segurança — ela dá acesso à sua conta.")


asyncio.run(main())
