import time
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# ==========================================
# CONFIGURATION - UPDATE THESE VALUES
# ==========================================
RATE_LIMIT_BUCKET_SIZE = 14
RATE_LIMIT_WINDOW_SECONDS = 10

# Note: You MUST add the exam page's exact origin to this list.
# You can find it by opening your browser's Developer Tools (Network tab), 
# triggering the verification, and looking at the "Origin" request header.
ALLOWED_ORIGINS = [
    "https://app-9thw6n.example.com",
    "https://exam.sanand.workers.dev/tds-2026-05-ga2" # <-- REPLACE THIS with the exam page origin
]

USER_EMAIL = "24f2002227@ds.study.iitm.ac.in" # <-- REPLACE THIS with your logged-in email

# In-memory store for rate limiting: { "client_id": [timestamp1, timestamp2, ...] }
client_request_history = {}


# ==========================================
# MIDDLEWARE 1: REQUEST CONTEXT
# ==========================================
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Check for existing header; generate fresh UUID4 if missing
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = str(uuid.uuid4())
        
        # 2. Store in request state for the endpoint to use
        request.state.request_id = req_id
        
        # 3. Call the next layer
        response = await call_next(request)
        
        # 4. Attach to outgoing response headers
        response.headers["X-Request-ID"] = req_id
        return response


# ==========================================
# MIDDLEWARE 3 (Order context): RATE LIMITING
# ==========================================
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Bypass rate limiting for CORS preflight (OPTIONS) requests
        if request.method == "OPTIONS":
            return await call_next(request)

        client_id = request.headers.get("X-Client-Id")
        
        if client_id:
            current_time = time.time()
            # Fetch history, defaulting to empty list
            history = client_request_history.get(client_id, [])
            
            # Prune timestamps older than our 10-second window
            history = [t for t in history if current_time - t < RATE_LIMIT_WINDOW_SECONDS]
            
            # Check if bucket is full (14 requests)
            if len(history) >= RATE_LIMIT_BUCKET_SIZE:
                return JSONResponse(
                    status_code=429, 
                    content={"detail": "Too Many Requests"}
                )
            
            # Log the new request and update the bucket
            history.append(current_time)
            client_request_history[client_id] = history
            
        return await call_next(request)


# ==========================================
# MIDDLEWARE REGISTRATION
# ==========================================
# Note: In FastAPI/Starlette, middleware is executed in the REVERSE order 
# of how it's added. The last one added is the outermost wrapper.

# 3. Innermost: Request Context
app.add_middleware(RequestContextMiddleware)

# 2. Middle: Rate Limiting
app.add_middleware(RateLimitMiddleware)

# 1. Outermost: CORS (Middleware 2)
# Handles preflight OPTIONS immediately before hitting rate limits or context.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# ENDPOINT
# ==========================================
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": USER_EMAIL,
        "request_id": request.state.request_id
    }
