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

if __name__ == "__main__":
    # Quick sanity test:
    # Say Arsenal (home) has an xG of 1.75 against Chelsea (away) with an xG of 1.10
    home_expected = 1.75
    away_expected = 1.10
    
    probs, matrix = calculate_match_probabilities(home_expected, away_expected)
    
    print("--- Testing Poisson Probability Model ---")
    print(f"Inputs -> Home xG: {home_expected}, Away xG: {away_expected}\n")
    print(f"P(Home Win): {probs['home_win']:.2%}")
    print(f"P(Draw):     {probs['draw']:.2%}")
    print(f"P(Away Win): {probs['away_win']:.2%}")
    print(f"Total Sum:   {(probs['home_win'] + probs['draw'] + probs['away_win']):.4f}")
    
    # Most likely scorelines
    # Find the top 3 highest probability cells
    unraveled_indices = np.argsort(matrix, axis=None)[::-1][:3]
    print("\nTop 3 Most Likely Scorelines:")
    for idx in unraveled_indices:
        h, a = np.unravel_index(idx, matrix.shape)
        print(f"  {h} - {a} : {matrix[h, a]:.2%}")

