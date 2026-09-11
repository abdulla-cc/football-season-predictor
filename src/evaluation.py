import math

import numpy as np

from src.model import fit_poisson_model, predict_match


OUTCOMES = ("home", "draw", "away")


def match_outcome(home_goals, away_goals):
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def _log_loss(actual_outcomes, predicted_probabilities):
    losses = []
    for actual, probabilities in zip(actual_outcomes, predicted_probabilities):
        probability = min(max(probabilities[actual], 1e-15), 1 - 1e-15)
        losses.append(-math.log(probability))
    return float(np.mean(losses))


def _brier_score(actual_outcomes, predicted_probabilities):
    scores = []
    for actual, probabilities in zip(actual_outcomes, predicted_probabilities):
        scores.append(
            sum((probabilities[outcome] - float(actual == outcome)) ** 2 for outcome in OUTCOMES)
        )
    return float(np.mean(scores))


def evaluate_chronological_holdout(matches_df, train_fraction=0.8):
    """Train on earlier matches and evaluate on later, unseen matches."""
    if not 0.5 <= train_fraction < 1.0:
        raise ValueError("train_fraction must be at least 0.5 and below 1.0")
    if len(matches_df) < 10:
        raise ValueError("At least 10 matches are required for evaluation")

    ordered = matches_df.sort_values("Date").reset_index(drop=True)
    split_index = int(len(ordered) * train_fraction)
    training = ordered.iloc[:split_index].copy()
    testing = ordered.iloc[split_index:].copy()

    training_teams = set(training["HomeTeam"]) | set(training["AwayTeam"])
    testing_teams = set(testing["HomeTeam"]) | set(testing["AwayTeam"])
    unseen_teams = sorted(testing_teams - training_teams)
    if unseen_teams:
        raise ValueError(f"Test data contains teams not present in training: {', '.join(unseen_teams)}")

    model = fit_poisson_model(training)
    actual_outcomes = []
    predicted_probabilities = []
    predicted_outcomes = []
    goal_errors = []
    exact_scores = 0

    for row in testing.itertuples(index=False):
        prediction = predict_match(model, row.HomeTeam, row.AwayTeam)
        probabilities = {
            "home": prediction["home_win_prob"] / 100.0,
            "draw": prediction["draw_prob"] / 100.0,
            "away": prediction["away_win_prob"] / 100.0,
        }
        actual = match_outcome(row.FTHG, row.FTAG)
        predicted = max(probabilities, key=probabilities.get)

        actual_outcomes.append(actual)
        predicted_probabilities.append(probabilities)
        predicted_outcomes.append(predicted)
        goal_errors.extend(
            [abs(prediction["home_xg"] - row.FTHG), abs(prediction["away_xg"] - row.FTAG)]
        )
        exact_scores += prediction["top_scorelines"][0][0] == f"{int(row.FTHG)}-{int(row.FTAG)}"

    training_outcomes = [match_outcome(row.FTHG, row.FTAG) for row in training.itertuples()]
    baseline_probabilities = {
        outcome: training_outcomes.count(outcome) / len(training_outcomes) for outcome in OUTCOMES
    }
    baseline_predictions = [baseline_probabilities] * len(testing)

    model_log_loss = _log_loss(actual_outcomes, predicted_probabilities)
    baseline_log_loss = _log_loss(actual_outcomes, baseline_predictions)

    return {
        "method": "Chronological 80/20 holdout",
        "training_matches": len(training),
        "test_matches": len(testing),
        "training_end_date": training["Date"].max().date().isoformat(),
        "test_start_date": testing["Date"].min().date().isoformat(),
        "outcome_accuracy_pct": round(np.mean(np.array(actual_outcomes) == np.array(predicted_outcomes)) * 100, 1),
        "exact_score_accuracy_pct": round(exact_scores / len(testing) * 100, 1),
        "goal_mae": round(float(np.mean(goal_errors)), 3),
        "log_loss": round(model_log_loss, 3),
        "baseline_log_loss": round(baseline_log_loss, 3),
        "log_loss_improvement_pct": round((baseline_log_loss - model_log_loss) / baseline_log_loss * 100, 1),
        "brier_score": round(_brier_score(actual_outcomes, predicted_probabilities), 3),
    }
