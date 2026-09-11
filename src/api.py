import sys
import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from src.data_pipeline import load_pl_data, get_complete_training_data
from src.model import fit_poisson_model, predict_match, get_team_strengths
from src.simulation import run_monte_carlo_simulation, calculate_current_table, calculate_season_status
from src.evaluation import evaluate_chronological_holdout
from src.data_updater import update_current_season_data

# Global cache for trained model and simulation results to ensure instant responses
CACHE = {}


async def periodic_data_update():
    """Refresh results in the background while the backend is running."""
    interval_hours = float(os.getenv("DATA_UPDATE_INTERVAL_HOURS", "6"))
    while True:
        try:
            result = await asyncio.to_thread(update_current_season_data)
            if result["completed_matches"] > result["previous_matches"]:
                CACHE.clear()
                print(f"Match data updated: {result['completed_matches']} completed matches")
        except Exception as exc:
            # A temporary network/source failure must not stop the API.
            print(f"Automatic match-data update skipped: {exc}")
        await asyncio.sleep(interval_hours * 60 * 60)


@asynccontextmanager
async def lifespan(app):
    update_task = None
    if os.getenv("AUTO_UPDATE_DATA", "true").lower() not in {"0", "false", "no"}:
        update_task = asyncio.create_task(periodic_data_update())
    yield
    if update_task:
        update_task.cancel()
        try:
            await update_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Football Season Predictor API", version="1.1", lifespan=lifespan)

# Enable CORS for React frontend (Vite defaults to 5173 or 3000)
cors_setting = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
cors_origins = [origin.strip() for origin in cors_setting.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {
        "status": "ok",
        "league": "Premier League 2026/27",
        "model": "Dixon-Coles",
    }

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

@app.get("/api/season-status")
def season_status():
    played = load_pl_data(["2026-2027"])
    return calculate_season_status(played)

@app.get("/api/team-strengths")
def team_strengths():
    model = get_or_train_model()
    strengths_df = get_team_strengths(model)
    return strengths_df.to_dict(orient="records")

@app.get("/api/evaluation")
def model_evaluation():
    if "evaluation" not in CACHE:
        historical_matches = load_pl_data(["2025-2026"])
        CACHE["evaluation"] = evaluate_chronological_holdout(historical_matches)
    return CACHE["evaluation"]

@app.post("/api/update-data")
def update_data():
    try:
        result = update_current_season_data()
        CACHE.clear()
        return result
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Data update failed: {exc}")

@app.post("/api/predict-match")
def predict(req: MatchRequest):
    model = get_or_train_model()
    try:
        result = predict_match(model, req.home_team, req.away_team)
        
        # Add head-to-head random insights
        train_data = CACHE.get("train_data")
        if train_data is None:
            train_data = get_complete_training_data()
            CACHE["train_data"] = train_data
            
        from src.model import generate_h2h_insights
        insights = generate_h2h_insights(train_data, req.home_team, req.away_team)
        result["h2h_insights"] = insights
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)
