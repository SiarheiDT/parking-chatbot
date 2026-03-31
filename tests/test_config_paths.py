from pathlib import Path

from app import paths
from app.config import get_config


def test_get_config_uses_defaults(monkeypatch) -> None:
    monkeypatch.delenv("DB_PATH", raising=False)
    monkeypatch.delenv("VECTOR_DB_PATH", raising=False)
    monkeypatch.delenv("TOP_K", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)

    cfg = get_config()
    assert cfg.DB_PATH == Path("data/db/parking_dev.db")
    assert cfg.TOP_K == 3


def test_get_config_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("DB_PATH", "tmp/db.sqlite")
    monkeypatch.setenv("TOP_K", "7")
    cfg = get_config()
    assert cfg.DB_PATH == Path("tmp/db.sqlite")
    assert cfg.TOP_K == 7


def test_paths_are_built_from_base_dir() -> None:
    assert paths.DATA_DIR == paths.BASE_DIR / "data"
    assert paths.RAW_DATA_DIR == paths.DATA_DIR / "raw"


def test_processed_data_dir_suffix() -> None:
    assert str(paths.PROCESSED_DATA_DIR).endswith("data/processed")
