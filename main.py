from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time

app = FastAPI()

EMAIL = "24f2002227@ds.study.iitm.ac.in"

ALLOWED_ORIGINS = [
    "https://app-9thw6n.example.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

clients = {}
LIMIT = 14
WINDOW = 10


@app.middleware("http")
async def middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    client = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    if client not in clients:
        clients[client] = []

    clients[client] = [t for t in clients[client] if now - t < WINDOW]

    if len(clients[client]) >= LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"X-Request-ID": request_id},
        )

    clients[client].append(now)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/")
def home():
    return {"status": "ok"}


@app.get("/ping")
def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
