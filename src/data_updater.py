import argparse
import io
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


CURRENT_SEASON_URL = "https://www.football-data.co.uk/mmz4281/2627/E0.csv"
DEFAULT_DESTINATION = Path("data") / "PL DATA" / "2026-2027.csv"
REQUIRED_COLUMNS = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"}


def _validate_download(content):
    if not content:
        raise ValueError("The downloaded file is empty")

    try:
        dataframe = pd.read_csv(io.BytesIO(content), encoding="latin1")
    except Exception as exc:
        raise ValueError("The downloaded file is not a readable CSV") from exc

    missing = REQUIRED_COLUMNS - set(dataframe.columns)
    if missing:
        raise ValueError(f"Downloaded CSV is missing columns: {', '.join(sorted(missing))}")

    played = dataframe.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
    if played.empty:
        raise ValueError("The downloaded CSV contains no completed matches")
    if len(played) > 380:
        raise ValueError("The downloaded CSV contains more than 380 completed matches")

    teams = set(played["HomeTeam"]) | set(played["AwayTeam"])
    if len(played) >= 10 and len(teams) != 20:
        raise ValueError(f"Expected 20 Premier League teams but found {len(teams)}")

    return dataframe, played


def update_current_season_data(destination=DEFAULT_DESTINATION, url=CURRENT_SEASON_URL, session=requests):
    """Download, validate, back up, and atomically replace the current-season CSV."""
    destination = Path(destination)
    response = session.get(url, timeout=30)
    response.raise_for_status()
    dataframe, played = _validate_download(response.content)

    existing_match_count = 0
    if destination.exists():
        existing = pd.read_csv(destination, encoding="latin1")
        existing_match_count = len(existing.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"]))
        if len(played) < existing_match_count:
            raise ValueError(
                f"Refusing to replace {existing_match_count} local matches with only {len(played)} downloaded matches"
            )

    destination.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if destination.exists() and response.content != destination.read_bytes():
        backup_dir = destination.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = backup_dir / f"{destination.stem}-{timestamp}.csv"
        shutil.copy2(destination, backup_path)

    temporary_path = destination.with_suffix(".csv.tmp")
    temporary_path.write_bytes(response.content)
    os.replace(temporary_path, destination)

    return {
        "status": "updated" if len(played) > existing_match_count else "up_to_date",
        "previous_matches": existing_match_count,
        "completed_matches": len(played),
        "latest_result_date": pd.to_datetime(played["Date"], dayfirst=True, format="mixed").max().date().isoformat(),
        "backup_created": str(backup_path) if backup_path else None,
        "source": url,
    }


def main():
    parser = argparse.ArgumentParser(description="Update the current Premier League results CSV")
    parser.add_argument("--url", default=CURRENT_SEASON_URL)
    parser.add_argument("--destination", default=str(DEFAULT_DESTINATION))
    args = parser.parse_args()
    result = update_current_season_data(args.destination, args.url)
    print(
        f"{result['status']}: {result['completed_matches']} completed matches "
        f"(latest result {result['latest_result_date']})"
    )


if __name__ == "__main__":
    main()
