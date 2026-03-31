from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.init_db import initialize_database


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    initialize_database(Path("data/db/parking_dev.db"))