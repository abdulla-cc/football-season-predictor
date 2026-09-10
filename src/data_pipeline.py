import os
import pandas as pd

# The folders where our data is stored
PL_DATA_DIR = os.path.join("data", "PL DATA")
CHAMP_DATA_DIR = os.path.join("data", "CHAMP DATA")

# Dictionary to standardize team names across different data sources
TEAM_NAME_MAPPINGS = {
    "Man Utd": "Man United",
    "Manchester United": "Man United",
    "Man City": "Man City",
    "Manchester City": "Man City",
    "Spurs": "Tottenham",
    "Nott'm Forest": "Nottingham Forest",
    "Nottingham": "Nottingham Forest",
    "Newcastle Utd": "Newcastle",
    "Sheffield Utd": "Sheffield United",
    "Luton Town": "Luton"
}

def standardize_teams(df):
    """
    Standardizes team names in the DataFrame to prevent the model from 
    treating 'Man Utd' and 'Man United' as different teams.
    """
    df['HomeTeam'] = df['HomeTeam'].replace(TEAM_NAME_MAPPINGS)
    df['AwayTeam'] = df['AwayTeam'].replace(TEAM_NAME_MAPPINGS)
    return df

def load_pl_data(seasons):
    """
    Loads Premier League CSV files for the given list of seasons,
    cleans them up, and combines them into one big table.
    """
    all_data = []
    
    for season in seasons:
        # Construct the file name, e.g., '2026-2027.csv'
        filename = f"{season}.csv"
        filepath = os.path.join(PL_DATA_DIR, filename)
        
        if os.path.exists(filepath):
            print(f"Loading PL season {filename}...")
            # We use latin1 encoding because these older files sometimes have weird characters
            df = pd.read_csv(filepath, encoding='latin1')
            
            # For our Poisson model, we only care about who played and the final score
            # FTHG = Full Time Home Goals, FTAG = Full Time Away Goals
            columns_we_need = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
            
            # Keep only the columns we need
            df = df[columns_we_need]
            
            # Add a column so we know which season this row came from
            df['Season'] = season
            df['League'] = 'Premier League'
            
            all_data.append(df)
        else:
            print(f"Warning: Could not find {filepath}")
            
    # Combine all the individual season tables into one giant table
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        # Remove matches that haven't been played yet (where goals are missing/NaN)
        combined_df = combined_df.dropna(subset=['FTHG', 'FTAG'])
        return standardize_teams(combined_df)
    else:
        return pd.DataFrame()

def load_promoted_teams_data(season="2025-2026", promoted_teams=["Coventry", "Ipswich", "Hull"]):
    """
    Loads the Championship data for the promoted teams.
    This gives them some historical data so our math model doesn't think they are ghost teams.
    """
    filepath = os.path.join(CHAMP_DATA_DIR, f"{season}.csv")
    
    if not os.path.exists(filepath):
        print(f"Warning: Championship data not found at {filepath}")
        return pd.DataFrame()
        
    print(f"Loading Championship season {season}.csv...")
    df = pd.read_csv(filepath, encoding='latin1')
    
    columns_we_need = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
    df = df[columns_we_need]
    
    # Keep only matches where a promoted team was playing
    mask = df['HomeTeam'].isin(promoted_teams) | df['AwayTeam'].isin(promoted_teams)
    promoted_df = df[mask].copy()
    
    promoted_df['Season'] = season
    promoted_df['League'] = 'Championship'
    
    return standardize_teams(promoted_df)

if __name__ == "__main__":
    # Let's test loading both PL and Championship data
    pl_seasons = ["2025-2026", "2026-2027"]
    print("Testing data loading...\n")
    
    pl_df = load_pl_data(pl_seasons)
    champ_df = load_promoted_teams_data()
    
    # Combine them
    final_df = pd.concat([pl_df, champ_df], ignore_index=True)
    
    print("\n--- Data Summary ---")
    print(f"Total PL matches loaded: {len(pl_df)}")
    print(f"Total Championship matches loaded for promoted teams: {len(champ_df)}")
    print(f"Total Combined matches: {len(final_df)}")
    
    print("\nLet's verify we have Ipswich data:")
    ipswich_matches = final_df[(final_df['HomeTeam'] == 'Ipswich') | (final_df['AwayTeam'] == 'Ipswich')]
    print(f"Matches involving Ipswich: {len(ipswich_matches)}")
