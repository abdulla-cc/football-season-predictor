import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from src.data_pipeline import load_pl_data, get_complete_training_data
from src.model import fit_poisson_model, predict_match, get_team_strengths
from src.simulation import run_monte_carlo_simulation, calculate_current_table

app = FastAPI(title="Football Season Predictor API", version="1.0")

# Enable CORS for React frontend (Vite defaults to 5173 or 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global cache for trained model and simulation results to ensure instant responses
CACHE = {}

def get_or_train_model():
    if "model" not in CACHE:
        print("Training model...")
        train_data = get_complete_training_data()
        CACHE["model"] = fit_poisson_model(train_data)
    return CACHE["model"]

def get_cached_simulation():
    if "simulation" not in CACHE:
        print("Running Monte Carlo simulation cache...")
        model = get_or_train_model()
        played = load_pl_data(['2026-2027'])
        sim_df = run_monte_carlo_simulation(model, played, n_simulations=10000)
        CACHE["simulation"] = sim_df
    return CACHE["simulation"]

class MatchRequest(BaseModel):
    home_team: str
    away_team: str

@app.get("/api/health")
def health():
    return {"status": "ok", "league": "Premier League 2026/27"}

@app.get("/api/teams")
def get_teams():
    played = load_pl_data(['2026-2027'])
    teams = sorted(list(set(played['HomeTeam'].unique()) | set(played['AwayTeam'].unique())))
    return {"teams": teams}

@app.get("/api/simulation")
def get_simulation(refresh: bool = False):
    if refresh and "simulation" in CACHE:
        del CACHE["simulation"]
    df = get_cached_simulation()
    return df.to_dict(orient="records")

@app.get("/api/current-table")
def get_current_standings():
    played = load_pl_data(['2026-2027'])
    teams = sorted(list(set(played['HomeTeam'].unique()) | set(played['AwayTeam'].unique())))
    table_df = calculate_current_table(played, teams)
    return table_df.to_dict(orient="records")

@app.get("/api/team-strengths")
def team_strengths():
    model = get_or_train_model()
    strengths_df = get_team_strengths(model)
    return strengths_df.to_dict(orient="records")

@app.post("/api/predict-match")
def predict(req: MatchRequest):
    model = get_or_train_model()
    try:
        result = predict_match(model, req.home_team, req.away_team)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)

