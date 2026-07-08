from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time

app = FastAPI()

EMAIL = "24f2002227@ds.study.iitm.ac.in"

# Replace the second origin with your actual exam page origin if needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-9thw6n.example.com",
        "https://exam.sanand.workers.dev"
    ],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

LIMIT = 14
WINDOW = 10
buckets = {}


@app.middleware("http")
async def request_context_and_rate_limit(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    client = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    if client not in buckets:
        buckets[client] = []

    buckets[client] = [
        t for t in buckets[client]
        if now - t < WINDOW
    ]

    if len(buckets[client]) >= LIMIT:

        return JSONResponse(
            status_code=429,
            headers={
                "X-Request-ID": request_id
            },
            content={
                "detail": "Rate limit exceeded"
            },
        )

    buckets[client].append(now)

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/ping")
def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }
