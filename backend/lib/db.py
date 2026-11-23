"""Shared Mongo handle — import client/db from here."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]
logger = logging.getLogger(__name__)

INDEXES: dict[str, list[IndexModel]] = {
    "companies": [IndexModel([("id", ASCENDING)], name="id", unique=True)],
    "users": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("email", ASCENDING)], name="email", unique=True),
        IndexModel([("company_id", ASCENDING), ("role", ASCENDING)], name="company_role"),
    ],
    "employees": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("company_id", ASCENDING), ("cpf", ASCENDING)], name="company_cpf", unique=True),
        IndexModel([("company_id", ASCENDING), ("matricula", ASCENDING)], name="company_matricula", unique=True),
        IndexModel([("company_id", ASCENDING), ("status", ASCENDING), ("name", ASCENDING)], name="company_status_name"),
        IndexModel([("company_id", ASCENDING), ("department", ASCENDING)], name="company_department"),
    ],
    "work_schedules": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("company_id", ASCENDING), ("name", ASCENDING)], name="company_name"),
    ],
    "time_records": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("company_id", ASCENDING), ("employee_id", ASCENDING), ("timestamp", DESCENDING)], name="company_employee_ts"),
        IndexModel([("company_id", ASCENDING), ("timestamp", DESCENDING)], name="company_ts"),
        IndexModel(
            [("company_id", ASCENDING), ("employee_id", ASCENDING), ("work_date", ASCENDING), ("type", ASCENDING)],
            name="company_employee_workdate_type_unique", unique=True,
            partialFilterExpression={"work_date": {"$exists": True}},
        ),
    ],
    "time_adjustment_requests": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("company_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)], name="company_status_created"),
        IndexModel([("company_id", ASCENDING), ("employee_id", ASCENDING), ("target_date", ASCENDING)], name="company_employee_date"),
    ],
    "audit_logs": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("company_id", ASCENDING), ("created_at", DESCENDING)], name="company_created"),
        IndexModel([("company_id", ASCENDING), ("action", ASCENDING), ("created_at", DESCENDING)], name="company_action_created"),
    ],
    "holidays": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("company_id", ASCENDING), ("date", ASCENDING)], name="company_date", unique=True),
    ],
    "schedule_assignments": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("company_id", ASCENDING), ("employee_id", ASCENDING), ("start_date", DESCENDING)], name="company_employee_start"),
    ],
    "hours_bank_closures": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel(
            [("company_id", ASCENDING), ("employee_id", ASCENDING), ("competence", ASCENDING)],
            name="company_employee_competence", unique=True,
        ),
        IndexModel([("company_id", ASCENDING), ("competence", ASCENDING)], name="company_competence"),
    ],
    "rate_limits": [IndexModel([("expires_at", ASCENDING)], name="rate_limit_ttl", expireAfterSeconds=0)],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
