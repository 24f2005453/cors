from collections import defaultdict, deque
from uuid import uuid4
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware


EMAIL = "24f2005453@ds.study.iitm.ac.in"

RATE_LIMIT = 15
WINDOW_SECONDS = 10

app = FastAPI()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.buckets = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_id = request.headers.get("X-Client-Id", "anonymous")

        now = time.monotonic()
        bucket = self.buckets[client_id]

        while bucket and now - bucket[0] >= WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )

        bucket.append(now)

        return await call_next(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid4())

        request.state.request_id = request_id

        response = await call_next(request)

        # Always echo it back
        response.headers["X-Request-ID"] = request_id

        return response


# Add in this order:
# Last added = outermost
app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-6baaqu.example.com",
        "https://exam.sanand.workers.dev",
    ],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(RequestContextMiddleware)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
