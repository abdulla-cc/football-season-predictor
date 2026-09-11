import pandas as pd
import pytest

from src.model import (
    calculate_match_probabilities,
    dixon_coles_tau,
    fit_poisson_model,
    predict_match,
    prepare_features,
)


def test_dixon_coles_only_adjusts_low_scores():
    assert dixon_coles_tau(0, 0, 1.5, 1.0, -0.1) == pytest.approx(1.15)
    assert dixon_coles_tau(1, 1, 1.5, 1.0, -0.1) == pytest.approx(1.1)
    assert dixon_coles_tau(2, 1, 1.5, 1.0, -0.1) == 1.0


def test_dixon_coles_changes_low_score_probabilities_and_stays_normalized():
    _, poisson_matrix = calculate_match_probabilities(1.5, 1.0, rho=0.0)
    probabilities, corrected_matrix = calculate_match_probabilities(1.5, 1.0, rho=-0.1)

    assert corrected_matrix[0, 0] > poisson_matrix[0, 0]
    assert corrected_matrix[1, 1] > poisson_matrix[1, 1]
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert corrected_matrix.sum() == pytest.approx(1.0)


def test_match_probabilities_sum_to_one():
    probabilities, score_matrix = calculate_match_probabilities(1.8, 1.1)

    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert probabilities["home_win"] > probabilities["away_win"]
    assert score_matrix.shape == (11, 11)


def test_prepare_features_creates_two_observations_per_match():
    matches = pd.DataFrame(
        {"HomeTeam": ["A"], "AwayTeam": ["B"], "FTHG": [2], "FTAG": [1]}
    )

    features = prepare_features(matches)

    assert len(features) == 2
    assert features.to_dict(orient="records") == [
        {"team": "A", "opponent": "B", "goals": 2, "home": 1},
        {"team": "B", "opponent": "A", "goals": 1, "home": 0},
    ]


def test_fitted_model_returns_a_complete_match_prediction():
    matches = pd.DataFrame(
        {
            "HomeTeam": ["A", "A", "B", "B", "C", "C"] * 2,
            "AwayTeam": ["B", "C", "A", "C", "A", "B"] * 2,
            "FTHG": [2, 1, 1, 3, 0, 2, 1, 2, 2, 1, 1, 3],
            "FTAG": [1, 0, 1, 1, 2, 2, 0, 1, 1, 2, 1, 0],
        }
    )

    model = fit_poisson_model(matches)
    prediction = predict_match(model, "A", "B")

    assert prediction["home_team"] == "A"
    assert prediction["away_team"] == "B"
    assert prediction["home_xg"] > 0
    assert prediction["away_xg"] > 0
    assert -0.2 <= prediction["dixon_coles_rho"] <= 0.2
    assert len(prediction["top_scorelines"]) == 3
    assert (
        prediction["home_win_prob"]
        + prediction["draw_prob"]
        + prediction["away_win_prob"]
    ) == pytest.approx(100.0, abs=0.1)
