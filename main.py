from collections import defaultdict, deque
from contextvars import ContextVar
from uuid import uuid4
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

EMAIL = "24f2005453@ds.study.iitm.ac.in"

ALLOWED_ORIGIN = "https://app-6baaqu.example.com"

# Also allow the exam page origin during grading.
# Replace this with the actual exam origin if your platform specifies one.
EXAM_ORIGIN = "https://exam.example.com"

RATE_LIMIT = 15
WINDOW_SECONDS = 10

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())

        request.state.request_id = request_id
        request_id_ctx.set(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.buckets = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_id = request.headers.get("X-Client-Id", "")

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


app = FastAPI()

# Middleware order:
# Request Context -> CORS -> Rate Limit (outermost added last)

app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        ALLOWED_ORIGIN,
        EXAM_ORIGIN,
    ],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
