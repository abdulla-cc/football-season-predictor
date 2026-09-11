import pandas as pd

import src.simulation as simulation


def sample_played_matches():
    return pd.DataFrame(
        {
            "HomeTeam": ["A", "C"],
            "AwayTeam": ["B", "D"],
            "FTHG": [2, 0],
            "FTAG": [1, 0],
        }
    )


def test_current_table_calculates_points_and_goal_difference():
    table = simulation.calculate_current_table(
        sample_played_matches(), ["A", "B", "C", "D"]
    )

    arsenal_like = table.loc[table["Team"] == "A"].iloc[0]
    assert arsenal_like["Points"] == 3
    assert arsenal_like["GD"] == 1
    assert arsenal_like["Wins"] == 1


def test_remaining_fixtures_exclude_already_played_matches():
    remaining = simulation.get_remaining_fixtures(
        sample_played_matches(), ["A", "B", "C", "D"]
    )

    assert len(remaining) == 10
    assert ("A", "B") not in remaining
    assert ("B", "A") in remaining


def test_season_status_is_calculated_from_loaded_matches():
    played = sample_played_matches().copy()
    played["Date"] = pd.to_datetime(["2026-08-21", "2026-08-22"])

    status = simulation.calculate_season_status(played)

    assert status == {
        "team_count": 4,
        "completed_matches": 2,
        "remaining_fixtures": 10,
        "total_fixtures": 12,
        "season_complete_pct": 16.7,
        "minimum_team_matches": 1,
        "maximum_team_matches": 1,
        "latest_result_date": "2026-08-22",
    }


def test_monte_carlo_returns_one_probability_row_per_team(monkeypatch):
    monkeypatch.setattr(simulation, "predict_match_xg", lambda model, home, away: (1.4, 1.1))

    result = simulation.run_monte_carlo_simulation(
        model=object(),
        played_df=sample_played_matches(),
        n_simulations=200,
        random_seed=7,
    )

    assert set(result["Team"]) == {"A", "B", "C", "D"}
    assert result["Title_%"].sum() == 100.0
    assert result["Top4_%"].sum() == 400.0
    assert result["Exp_Rank"].between(1, 4).all()


def test_simulation_accepts_a_fitted_dixon_coles_parameter(monkeypatch):
    monkeypatch.setattr(simulation, "predict_match_xg", lambda model, home, away: (1.2, 1.0))

    class DixonColesModel:
        dixon_coles_rho = -0.08

    result = simulation.run_monte_carlo_simulation(
        model=DixonColesModel(),
        played_df=sample_played_matches(),
        n_simulations=25,
        random_seed=3,
    )

    assert len(result) == 4
