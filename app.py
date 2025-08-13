
import os
from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import UsernameInvalidError

# ---- ENV ----
API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
STRING = os.environ["TG_STRING_SESSION"]        # generated once locally
API_KEY = os.environ.get("API_KEY", "")         # simple shared key for n8n requests

# ---- TELETHON CLIENT ----
client = TelegramClient(StringSession(STRING), API_ID, API_HASH)

# ---- FASTAPI ----
app = FastAPI(title="tg-mini", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Post(BaseModel):
    date: str
    channel: str
    link: str
    views: int
    forwards: int
    text: str

@app.middleware("http")
async def check_api_key(request: Request, call_next):
    # optional lightweight protection
    if API_KEY and request.headers.get("x-api-key") != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)

@app.on_event("startup")
async def _startup():
    # Will reuse saved StringSession from env
    await client.start()

@app.get("/", tags=["health"])
async def root():
    return {"ok": True, "service": "tg-mini", "time": datetime.utcnow().isoformat()}

@app.get("/healthz", tags=["health"])
async def healthz():
    return {"ok": True}

@app.get("/posts", response_model=List[Post], tags=["data"])
async def get_posts(channel: str, days: int = 7):
    """Return posts from a public channel for the last N days with views/forwards."""
    try:
        entity = await client.get_entity(channel)
    except Exception as e:
        if isinstance(e, UsernameInvalidError):
            raise HTTPException(status_code=404, detail="Channel not found")
        raise HTTPException(status_code=400, detail=str(e))

    since = datetime.utcnow() - timedelta(days=days)
    items = []
    async for m in client.iter_messages(entity):
        if not getattr(m, "date", None):
            continue
        if m.date.replace(tzinfo=None) < since:
            break
        views = int(getattr(m, "views", 0) or 0)
        forwards = int(getattr(m, "forwards", 0) or 0)
        uname = getattr(entity, "username", None)
        link = f"https://t.me/{uname}/{m.id}" if uname else ""
        text = (m.message or "")[:180].replace("\n", " ")
        items.append({
            "date": m.date.isoformat(),
            "channel": f"@{uname}" if uname else str(entity.id),
            "link": link,
            "views": views,
            "forwards": forwards,
            "text": text
        })
    return items
