import os
import pandas as pd

# The folder where our Premier League data is stored
DATA_DIR = os.path.join("data", "PL DATA")

def load_pl_data(seasons):
    """
    Loads Premier League CSV files for the given list of seasons,
    cleans them up, and combines them into one big table.
    """
    all_data = []
    
    for season in seasons:
        # Construct the file name, e.g., '2026-2027.csv'
        filename = f"{season}.csv"
        filepath = os.path.join(DATA_DIR, filename)
        
        if os.path.exists(filepath):
            print(f"Loading {filename}...")
            # We use latin1 encoding because these older files sometimes have weird characters
            df = pd.read_csv(filepath, encoding='latin1')
            
            # For our Poisson model, we only care about who played and the final score
            # FTHG = Full Time Home Goals, FTAG = Full Time Away Goals
            columns_we_need = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
            
            # Keep only the columns we need
            df = df[columns_we_need]
            
            # Add a column so we know which season this row came from
            df['Season'] = season
            
            all_data.append(df)
        else:
            print(f"Warning: Could not find {filepath}")
            
    # Combine all the individual season tables into one giant table
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        # Remove matches that haven't been played yet (where goals are missing/NaN)
        combined_df = combined_df.dropna(subset=['FTHG', 'FTAG'])
        return combined_df
    else:
        return pd.DataFrame()

if __name__ == "__main__":
    # Let's test with just the last complete season and the current one
    test_seasons = ["2025-2026", "2026-2027"]
    print("Testing data loading...\n")
    
    df = load_pl_data(test_seasons)
    
    print("\n--- Data Summary ---")
    print(f"Total matches loaded: {len(df)}")
    print("\nFirst 3 rows of our dataset:")
    print(df.head(3))
