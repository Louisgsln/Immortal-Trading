import json
from pathlib import Path

import pytest

from trading_radar.config import Company, load_config
from trading_radar.models import RawJob
from trading_radar.normalizer import normalize
from trading_radar.scoring import score_job
from trading_radar.storage import Repository


@pytest.fixture
def config():
    cfg = load_config()
    cfg.settings.alerts_enabled = True
    cfg.companies = {"test": Company(name="Demo Bank", ats="fixture", enabled=True)}
    return cfg


@pytest.fixture
def repo(tmp_path):
    repository = Repository(f"sqlite:///{tmp_path / 'jobs.db'}")
    yield repository
    repository.close()


@pytest.fixture
def raw():
    data = json.loads(Path("tests/fixtures/jobs.json").read_text())[0]
    return RawJob(**data, source="test", source_type="official")


@pytest.fixture
def job(raw, config):
    return score_job(normalize(raw), config.keywords)
