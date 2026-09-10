import numpy as np
from scipy.stats import poisson

def calculate_match_probabilities(home_xg, away_xg, max_goals=10):
    """
    Given expected goals (xG / lambda) for Home and Away teams,
    calculates the probability matrix of all possible scorelines (0-0 up to max_goals x max_goals),
    and derives the probability of Home Win, Draw, and Away Win.
    
    Parameters:
    - home_xg: expected goals for home team (float)
    - away_xg: expected goals for away team (float)
    - max_goals: maximum goals to simulate for the grid (default 10)
    
    Returns:
    - dict: {'home_win': float, 'draw': float, 'away_win': float}
    - 2D numpy array: scoreline probability grid [home_goals, away_goals]
    """
    goals = np.arange(0, max_goals + 1)
    
    # Calculate Poisson probabilities for each number of goals (0 to max_goals)
    # P(k) = (lambda^k * e^(-lambda)) / k!
    home_probs = poisson.pmf(goals, home_xg)
    away_probs = poisson.pmf(goals, away_xg)
    
    # Outer product gives the probability matrix for any scoreline (i, j)
    # P(Home=i and Away=j) = P(Home=i) * P(Away=j)
    score_matrix = np.outer(home_probs, away_probs)
    
    # Sum probabilities where home > away, home == away, home < away
    prob_home_win = np.sum(np.tril(score_matrix, -1))
    prob_draw = np.sum(np.diag(score_matrix))
    prob_away_win = np.sum(np.triu(score_matrix, 1))
    
    # Normalize slightly in case probabilities for >10 goals are truncated
    total_prob = prob_home_win + prob_draw + prob_away_win
    prob_home_win /= total_prob
    prob_draw /= total_prob
    prob_away_win /= total_prob
    
    return {
        'home_win': float(prob_home_win),
        'draw': float(prob_draw),
        'away_win': float(prob_away_win)
    }, score_matrix

def prepare_features(matches_df):
    """
    Transforms matches into team-level offensive and defensive observations.
    Each match produces two rows:
      1. Home team attacking vs Away team defending (home = 1)
      2. Away team attacking vs Home team defending (home = 0)
    """
    import pandas as pd
    home_obs = matches_df[['HomeTeam', 'AwayTeam', 'FTHG']].rename(
        columns={'HomeTeam': 'team', 'AwayTeam': 'opponent', 'FTHG': 'goals'}
    )
    home_obs['home'] = 1
    
    away_obs = matches_df[['AwayTeam', 'HomeTeam', 'FTAG']].rename(
        columns={'AwayTeam': 'team', 'HomeTeam': 'opponent', 'FTAG': 'goals'}
    )
    away_obs['home'] = 0
    
    return pd.concat([home_obs, away_obs], ignore_index=True)

def fit_poisson_model(matches_df):
    """
    Fits a Poisson Generalized Linear Model (GLM) using statsmodels.
    Log(goals) = Intercept + Home_Advantage*home + Attack_team + Defense_opponent
    """
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    
    features = prepare_features(matches_df)
    # goals ~ home + team + opponent
    model = smf.glm(
        formula="goals ~ home + team + opponent",
        data=features,
        family=sm.families.Poisson()
    ).fit()
    
    return model

def predict_match_xg(model, home_team, away_team):
    """
    Predicts expected goals (xG / lambda) for both teams in a matchup.
    """
    import pandas as pd
    home_input = pd.DataFrame([{'team': home_team, 'opponent': away_team, 'home': 1}])
    away_input = pd.DataFrame([{'team': away_team, 'opponent': home_team, 'home': 0}])
    
    home_xg = float(model.predict(home_input).values[0])
    away_xg = float(model.predict(away_input).values[0])
    
    return home_xg, away_xg

def predict_match(model, home_team, away_team):
    """
    End-to-end prediction: returns expected goals, outcome probabilities, and top scorelines.
    """
    home_xg, away_xg = predict_match_xg(model, home_team, away_team)
    probs, matrix = calculate_match_probabilities(home_xg, away_xg)
    
    # Top 3 most likely scorelines
    unraveled_indices = np.argsort(matrix, axis=None)[::-1][:3]
    top_scores = []
    for idx in unraveled_indices:
        h, a = np.unravel_index(idx, matrix.shape)
        top_scores.append((f"{h}-{a}", float(matrix[h, a])))
        
    return {
        'home_team': home_team,
        'away_team': away_team,
        'home_xg': round(home_xg, 2),
        'away_xg': round(away_xg, 2),
        'home_win_prob': round(probs['home_win'] * 100, 1),
        'draw_prob': round(probs['draw'] * 100, 1),
        'away_win_prob': round(probs['away_win'] * 100, 1),
        'top_scorelines': top_scores
    }

def get_team_strengths(model):
    """
    Extracts attacking and defensive strength coefficients for each team.
    Higher attack = scores more. Lower defense = concedes fewer.
    """
    import pandas as pd
    params = model.params
    teams = sorted(list(set(
        k.split('team[T.')[1][:-1] for k in params.index if k.startswith('team[T.')
    )))
    
    records = []
    for team in teams:
        att = params.get(f'team[T.{team}]', 0.0)
        defn = params.get(f'opponent[T.{team}]', 0.0)
        records.append({
            'Team': team,
            'Attack_Strength': round(float(att), 3),
            'Defense_Weakness': round(float(defn), 3)
        })
        
    df_strengths = pd.DataFrame(records).sort_values('Attack_Strength', ascending=False)
    return df_strengths

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    
    from src.data_pipeline import get_complete_training_data
    
    print("Loading cleaned Premier League data with promoted team anchors...")
    training_data = get_complete_training_data()
    print(f"Total training matches: {len(training_data)}")
    
    print("\nFitting Poisson GLM model...")
    model = fit_poisson_model(training_data)
    print("Model fitting complete! Converged:", model.converged)
    
    home_adv = np.exp(model.params['home'])
    print(f"Home Advantage Multiplier: {home_adv:.2f}x goals")
    
    print("\n--- Team Strengths Preview (Top 5 Attackers) ---")
    strengths = get_team_strengths(model)
    print(strengths.head(5).to_string(index=False))
    
    print("\n--- Example Match Predictions ---")
    matchups = [
        ("Arsenal", "Ipswich"),
        ("Man City", "Liverpool"),
        ("Chelsea", "Coventry")
    ]
    for h, a in matchups:
        pred = predict_match(model, h, a)
        print(f"\n{pred['home_team']} vs {pred['away_team']}:")
        print(f"  Expected Goals: {pred['home_team']} {pred['home_xg']} - {pred['away_xg']} {pred['away_team']}")
        print(f"  Win Odds: Home {pred['home_win_prob']}% | Draw {pred['draw_prob']}% | Away {pred['away_win_prob']}%")
        print(f"  Top Scoreline: {pred['top_scorelines'][0][0]} ({pred['top_scorelines'][0][1]:.1%})")


