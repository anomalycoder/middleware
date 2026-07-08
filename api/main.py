from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid

app = FastAPI()

RATE_LIMIT_BUCKET_SIZE = 14
RATE_LIMIT_WINDOW_SECONDS = 10
USER_EMAIL = "24f2002227@ds.study.iitm.ac.in"

ALLOWED_ORIGINS = [
    "https://app-9thw6n.example.com",
    "https://tds.study.iitm.ac.in"
]

client_request_history = {}

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        client_id = request.headers.get("X-Client-Id")
        if client_id:
            current_time = time.time()
            history = client_request_history.get(client_id, [])
            history = [t for t in history if current_time - t < RATE_LIMIT_WINDOW_SECONDS]
            
            if len(history) >= RATE_LIMIT_BUCKET_SIZE:
                return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})
            
            history.append(current_time)
            client_request_history[client_id] = history
            
        return await call_next(request)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

@app.get("/ping")
async def ping(request: Request):
    return {
        "email": USER_EMAIL,
        "request_id": request.state.request_id
    }