from pathlib import Path

import pandas as pd
import pytest

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic_sites.csv"


@pytest.fixture
def sites():
    return pd.read_csv(DATA)
