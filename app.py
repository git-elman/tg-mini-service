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
app = FastAPI(title="tg-mini", version="1.2.0")
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
    coef_pct: float
    text: str

def _sanitize_username(s: str) -> str:
    """Возвращает username без @ и хвостов пути (из @user или https://t.me/user/123)."""
    s = (s or "").strip()
    s = s.replace("https://t.me/", "").replace("http://t.me/", "")
    s = s.replace("https://telegram.me/", "").replace("http://telegram.me/", "")
    s = s.lstrip("@")
    return s.split("/")[0]

@app.middleware("http")
async def check_api_key(request: Request, call_next):
    if API_KEY and request.headers.get("x-api-key") != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)

@app.on_event("startup")
async def _startup():
    await client.start()

@app.get("/", tags=["health"])
async def root():
    return {"ok": True, "service": "tg-mini", "time": datetime.utcnow().isoformat()}

@app.get("/healthz", tags=["health"])
async def healthz():
    return {"ok": True}

@app.get("/posts", response_model=List[Post], tags=["data"])
async def get_posts(
    channel: str,
    days: int = 7,
    min_coef: float = 3.0,
    max_chars: int = 0,     # 0 -> полный текст; >0 -> обрезать до указанного кол-ва символов
):
    """
    Вернёт посты публичного канала за N дней с метриками и коэффициентом.
    Фильтрует по coef_pct >= min_coef. Текст по умолчанию полный (max_chars=0).
    """
    try:
        entity = await client.get_entity(channel)
    except Exception as e:
        if isinstance(e, UsernameInvalidError):
            raise HTTPException(status_code=404, detail="Channel not found")
        raise HTTPException(status_code=400, detail=str(e))

    requested = _sanitize_username(channel)
    uname = getattr(entity, "username", None) or requested

    since = datetime.utcnow() - timedelta(days=days)
    items: List[Post] = []
    async for m in client.iter_messages(entity):
        if not getattr(m, "date", None):
            continue
        if m.date.replace(tzinfo=None) < since:
            break

        views = int(getattr(m, "views", 0) or 0)
        forwards = int(getattr(m, "forwards", 0) or 0)
        coef = (forwards / views * 100.0) if views else 0.0
        if coef < float(min_coef):
            continue

        link = f"https://t.me/{uname}/{m.id}" if uname else ""

        raw_text = (m.message or "")
        if max_chars and max_chars > 0:
            raw_text = raw_text[:max_chars]
        text = raw_text.replace("\n", " ")

        items.append(Post(
            date=m.date.isoformat(),
            channel=f"@{uname}" if uname else "",
            link=link,
            views=views,
            forwards=forwards,
            coef_pct=round(coef, 2),
            text=text
        ))
    return items
