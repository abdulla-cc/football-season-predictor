import pandas as pd

from src.evaluation import evaluate_chronological_holdout, match_outcome


def test_match_outcome_handles_all_three_results():
    assert match_outcome(2, 1) == "home"
    assert match_outcome(1, 1) == "draw"
    assert match_outcome(0, 2) == "away"


def test_chronological_evaluation_returns_explainable_metrics():
    fixtures = [("A", "B"), ("A", "C"), ("B", "A"), ("B", "C"), ("C", "A"), ("C", "B")]
    rows = []
    for index in range(30):
        home, away = fixtures[index % len(fixtures)]
        rows.append(
            {
                "Date": pd.Timestamp("2025-01-01") + pd.Timedelta(days=index),
                "HomeTeam": home,
                "AwayTeam": away,
                "FTHG": (index * 2 + 1) % 4,
                "FTAG": (index + 1) % 3,
            }
        )

    result = evaluate_chronological_holdout(pd.DataFrame(rows))

    assert result["training_matches"] == 24
    assert result["test_matches"] == 6
    assert 0 <= result["outcome_accuracy_pct"] <= 100
    assert 0 <= result["exact_score_accuracy_pct"] <= 100
    assert result["goal_mae"] >= 0
    assert result["log_loss"] >= 0
    assert result["baseline_log_loss"] >= 0
    assert result["brier_score"] >= 0
