# app/api/corrections.py — tone annotation correction submissions
from circuitforge_core.api import make_corrections_router
from app.db import get_db

router = make_corrections_router(get_db=get_db, product="linnet")
