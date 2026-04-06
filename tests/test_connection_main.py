from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.stage1

from app.db.connection import get_connection
from app.main import main


def test_get_connection_creates_parent_directory(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "sample.db"
    conn = get_connection(db_path)
    conn.close()
    assert db_path.parent.exists()


def test_get_connection_returns_working_sqlite_connection(tmp_path: Path) -> None:
    db_path = tmp_path / "sample.db"
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    row = cur.fetchone()
    conn.close()
    assert row == (1,)


@patch("app.main.initialize_database")
@patch("app.main.route", return_value="hello")
@patch("builtins.input", side_effect=["Hi", "exit"])
@patch("builtins.print")
def test_main_runs_single_interaction_then_exits(
    mock_print, _mock_input, _mock_route, mock_init_db
) -> None:
    main()
    assert mock_init_db.called
    printed = " ".join(" ".join(map(str, c.args)) for c in mock_print.call_args_list)
    assert "Welcome to Central Parking Wroclaw Assistant." in printed


@patch("app.main.initialize_database")
@patch("app.main.route")
@patch("builtins.input", side_effect=["", "exit"])
@patch("builtins.print")
def test_main_rejects_empty_input(mock_print, _mock_input, mock_route, _mock_init_db) -> None:
    main()
    mock_route.assert_not_called()
    assert any("Please enter a message." in str(call) for call in mock_print.call_args_list)
