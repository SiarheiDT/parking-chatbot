from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pytest
from app.db.database import initialize_database


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    initialize_database()