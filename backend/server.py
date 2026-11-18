from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
from lib.db import client, db, ensure_indexes

# Feature routers (one module per resource under backend/routers/)
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.employees import router as employees_router
from routers.schedules import router as schedules_router
from routers.records import router as records_router
from routers.timesheet import router as timesheet_router
from routers.adjustments import router as adjustments_router
from routers.dashboard import router as dashboard_router
from routers.calendar import router as calendar_router
from routers.hoursbank import router as hoursbank_router
from routers.alerts import router as alerts_router


# Startup runs before the yield, shutdown after it. Add your own setup/teardown here.
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.index_task = asyncio.create_task(ensure_indexes())  # background: a big index build must not block boot
    yield
    client.close()


# Create the main app without a prefix
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "PontoFlow API"}


# Mount the feature routers onto the /api router (never onto `app` directly)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(employees_router)
api_router.include_router(schedules_router)
api_router.include_router(records_router)
api_router.include_router(timesheet_router)
api_router.include_router(adjustments_router)
api_router.include_router(dashboard_router)
api_router.include_router(calendar_router)
api_router.include_router(hoursbank_router)
api_router.include_router(alerts_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[o.strip() for o in os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',') if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Centralised error handling (§25): the user sees a clear message, the stack trace stays in the log.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erro interno. Tente novamente em instantes."})


# Security headers (§19)
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self)"
    return response


# Include the router in the main app — must stay the last statement
app.include_router(api_router)
