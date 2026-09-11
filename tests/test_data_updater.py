from pathlib import Path

import pandas as pd
import pytest

from src.data_updater import update_current_season_data


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, content):
        self.content = content

    def get(self, url, timeout):
        assert timeout == 30
        return FakeResponse(self.content)


def csv_bytes(match_count=10):
    teams = [f"Team {index}" for index in range(20)]
    rows = []
    for index in range(match_count):
        rows.append(
            {
                "Date": f"{index + 1:02d}/08/2026",
                "HomeTeam": teams[index],
                "AwayTeam": teams[index + 10],
                "FTHG": index % 3,
                "FTAG": (index + 1) % 3,
            }
        )
    return pd.DataFrame(rows).to_csv(index=False).encode("latin1")


def test_updater_downloads_and_validates_current_results(tmp_path):
    destination = tmp_path / "2026-7.csv"

    result = update_current_season_data(
        destination=destination,
        url="https://example.test/results.csv",
        session=FakeSession(csv_bytes()),
    )

    assert result["status"] == "updated"
    assert result["completed_matches"] == 10
    assert destination.exists()


def test_updater_refuses_to_replace_newer_local_data(tmp_path):
    destination = tmp_path / "2026-2027.csv"
    destination.write_bytes(csv_bytes(10))

    with pytest.raises(ValueError, match="Refusing to replace"):
        update_current_season_data(
            destination=destination,
            session=FakeSession(csv_bytes(5)),
        )

    assert len(pd.read_csv(destination)) == 10


def test_updater_rejects_invalid_download(tmp_path):
    with pytest.raises(ValueError, match="missing columns"):
        update_current_season_data(
            destination=tmp_path / "results.csv",
            session=FakeSession(b"wrong,column\n1,2\n"),
        )
