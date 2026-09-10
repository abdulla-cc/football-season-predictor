import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import itertools
import numpy as np
import pandas as pd
from src.model import predict_match_xg

def calculate_current_table(played_df, teams):
    """
    Calculates current Premier League standings from matches played so far.
    """
    table = {t: {'Played': 0, 'Wins': 0, 'Draws': 0, 'Losses': 0, 
                 'GF': 0, 'GA': 0, 'GD': 0, 'Points': 0} for t in teams}
    
    for _, row in played_df.iterrows():
        h, a = row['HomeTeam'], row['AwayTeam']
        hg, ag = int(row['FTHG']), int(row['FTAG'])
        
        table[h]['Played'] += 1
        table[a]['Played'] += 1
        table[h]['GF'] += hg
        table[h]['GA'] += ag
        table[a]['GF'] += ag
        table[a]['GA'] += hg
        
        if hg > ag:
            table[h]['Wins'] += 1
            table[h]['Points'] += 3
            table[a]['Losses'] += 1
        elif hg < ag:
            table[a]['Wins'] += 1
            table[a]['Points'] += 3
            table[h]['Losses'] += 1
        else:
            table[h]['Draws'] += 1
            table[h]['Points'] += 1
            table[a]['Draws'] += 1
            table[a]['Points'] += 1
            
    for t in teams:
        table[t]['GD'] = table[t]['GF'] - table[t]['GA']
        
    df_table = pd.DataFrame.from_dict(table, orient='index').reset_index().rename(columns={'index': 'Team'})
    df_table = df_table.sort_values(by=['Points', 'GD', 'GF'], ascending=[False, False, False]).reset_index(drop=True)
    df_table.index += 1
    return df_table

def get_remaining_fixtures(played_df, teams):
    """
    Identifies all remaining fixtures (every team plays every other team home & away).
    """
    all_possible = set(itertools.permutations(teams, 2))
    played = set(zip(played_df['HomeTeam'], played_df['AwayTeam']))
    remaining = sorted(list(all_possible - played))
    return remaining

def run_monte_carlo_simulation(model, played_df, n_simulations=10000, random_seed=42):
    """
    Runs full-season Monte Carlo simulations for remaining fixtures.
    Aggregates final league standing distributions across all runs.
    """
    if random_seed is not None:
        np.random.seed(random_seed)
        
    teams = sorted(list(set(played_df['HomeTeam'].unique()) | set(played_df['AwayTeam'].unique())))
    n_teams = len(teams)
    team_to_idx = {t: i for i, t in enumerate(teams)}
    
    # 1. Base standings from completed games
    curr_table = calculate_current_table(played_df, teams)
    base_points = np.zeros(n_teams)
    base_gf = np.zeros(n_teams)
    base_ga = np.zeros(n_teams)
    
    for _, row in curr_table.iterrows():
        idx = team_to_idx[row['Team']]
        base_points[idx] = row['Points']
        base_gf[idx] = row['GF']
        base_ga[idx] = row['GA']
        
    # 2. Remaining fixtures and their expected goals (xG)
    remaining_fixtures = get_remaining_fixtures(played_df, teams)
    n_remaining = len(remaining_fixtures)
    
    if n_remaining == 0:
        print("All fixtures already played!")
        return curr_table
        
    home_indices = np.array([team_to_idx[h] for h, a in remaining_fixtures])
    away_indices = np.array([team_to_idx[a] for h, a in remaining_fixtures])
    
    home_xg_list = []
    away_xg_list = []
    for h, a in remaining_fixtures:
        h_xg, a_xg = predict_match_xg(model, h, a)
        home_xg_list.append(h_xg)
        away_xg_list.append(a_xg)
        
    home_xg_arr = np.array(home_xg_list)
    away_xg_arr = np.array(away_xg_list)
    
    # 3. Vectorized simulation: sample goals for all remaining matches across n_simulations
    # Shape: (n_remaining, n_simulations)
    sim_home_goals = np.random.poisson(home_xg_arr[:, None], size=(n_remaining, n_simulations))
    sim_away_goals = np.random.poisson(away_xg_arr[:, None], size=(n_remaining, n_simulations))
    
    # Points earned in simulated matches
    home_win = (sim_home_goals > sim_away_goals).astype(int)
    away_win = (sim_home_goals < sim_away_goals).astype(int)
    draw = (sim_home_goals == sim_away_goals).astype(int)
    
    home_pts = home_win * 3 + draw * 1
    away_pts = away_win * 3 + draw * 1
    
    # 4. Tally totals across all teams for each simulation run
    # Shape: (n_teams, n_simulations)
    sim_points = np.tile(base_points[:, None], (1, n_simulations))
    sim_gf = np.tile(base_gf[:, None], (1, n_simulations))
    sim_ga = np.tile(base_ga[:, None], (1, n_simulations))
    
    np.add.at(sim_points, home_indices, home_pts)
    np.add.at(sim_points, away_indices, away_pts)
    
    np.add.at(sim_gf, home_indices, sim_home_goals)
    np.add.at(sim_gf, away_indices, sim_away_goals)
    
    np.add.at(sim_ga, home_indices, sim_away_goals)
    np.add.at(sim_ga, away_indices, sim_home_goals)
    
    sim_gd = sim_gf - sim_ga
    
    # 5. Determine league table ranks for each simulation
    # Premier League tiebreakers: Points > GD > GF
    # We combine them into a composite score: Points * 10,000 + GD * 100 + GF
    composite_score = sim_points * 100000.0 + sim_gd * 100.0 + sim_gf * 0.1
    # Adding tiny random noise to break any identical ties
    composite_score += np.random.uniform(0, 0.001, size=composite_score.shape)
    
    # ranks: 1 to 20 for each simulation run (lower rank number is better)
    # argsort descending gives 0-indexed order
    sorted_order = np.argsort(-composite_score, axis=0)
    ranks = np.zeros_like(sorted_order)
    for sim_idx in range(n_simulations):
        ranks[sorted_order[:, sim_idx], sim_idx] = np.arange(1, n_teams + 1)
        
    # 6. Aggregate probabilities per team
    summary_records = []
    for team_name, idx in team_to_idx.items():
        team_ranks = ranks[idx, :]
        team_pts = sim_points[idx, :]
        team_gd = sim_gd[idx, :]
        
        title_pct = np.mean(team_ranks == 1) * 100.0
        top4_pct = np.mean(team_ranks <= 4) * 100.0
        top6_pct = np.mean(team_ranks <= 6) * 100.0
        relegation_pct = np.mean(team_ranks >= 18) * 100.0
        exp_pts = float(np.mean(team_pts))
        exp_rank = float(np.mean(team_ranks))
        exp_gd = float(np.mean(team_gd))
        
        summary_records.append({
            'Team': team_name,
            'Exp_Pts': round(exp_pts, 1),
            'Exp_GD': round(exp_gd, 1),
            'Exp_Rank': round(exp_rank, 1),
            'Title_%': round(title_pct, 1),
            'Top4_%': round(top4_pct, 1),
            'Top6_%': round(top6_pct, 1),
            'Relegation_%': round(relegation_pct, 1),
        })
        
    summary_df = pd.DataFrame(summary_records).sort_values(
        by=['Title_%', 'Top4_%', 'Exp_Pts'], ascending=[False, False, False]
    ).reset_index(drop=True)
    summary_df.index += 1
    
    return summary_df

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    
    from src.data_pipeline import load_pl_data, get_complete_training_data
    from src.model import fit_poisson_model
    
    print("Fitting model for 2026/27 season simulation...")
    training_data = get_complete_training_data()
    model = fit_poisson_model(training_data)
    
    played_2627 = load_pl_data(['2026-2027'])
    print(f"Loaded {len(played_2627)} matches played so far in 2026/27.")
    
    print("\nRunning 10,000 Monte Carlo Season Simulations...")
    sim_results = run_monte_carlo_simulation(model, played_2627, n_simulations=10000)
    
    print("\n=== 2026/27 Premier League Season Forecast (10,000 Simulations) ===")
    print(sim_results.to_string())
