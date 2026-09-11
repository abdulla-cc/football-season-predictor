import pandas as pd

from src.data_pipeline import create_promoted_team_anchors, standardize_teams


def test_standardize_teams_normalizes_known_aliases():
    matches = pd.DataFrame(
        {
            "HomeTeam": ["Man Utd", "Spurs"],
            "AwayTeam": ["Nott'm Forest", "Newcastle Utd"],
        }
    )

    result = standardize_teams(matches)

    assert result["HomeTeam"].tolist() == ["Man United", "Tottenham"]
    assert result["AwayTeam"].tolist() == ["Nottingham Forest", "Newcastle"]


def test_promoted_team_anchors_create_home_and_away_priors():
    championship_matches = pd.DataFrame(
        {
            "HomeTeam": ["Ipswich", "Other"],
            "AwayTeam": ["Other", "Ipswich"],
            "FTHG": [2, 1],
            "FTAG": [0, 1],
        }
    )

    anchors = create_promoted_team_anchors(
        championship_matches,
        promoted_teams=["Ipswich"],
        baseline_opponent="Everton",
    )

    assert len(anchors) == 6
    assert (anchors["HomeTeam"] == "Ipswich").sum() == 3
    assert (anchors["AwayTeam"] == "Ipswich").sum() == 3
    assert (anchors[["FTHG", "FTAG"]] >= 1).all().all()
