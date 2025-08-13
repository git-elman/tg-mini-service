
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

print("Получение TG_STRING_SESSION")
api_id = int(input("API_ID: ").strip())
api_hash = input("API_HASH: ").strip()
with TelegramClient(StringSession(), api_id, api_hash) as client:
    s = client.session.save()
    print("\nTG_STRING_SESSION:")
    print(s)
    print("\nСкопируй эту строку в Secret на Render.")
