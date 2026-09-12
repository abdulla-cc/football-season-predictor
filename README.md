# Premier League Season Predictor

A full-season forecasting application for the 2026/27 English Premier League. It estimates team strengths, predicts individual match scorelines, and simulates the remaining league schedule 10,000 times to produce title, European qualification, and relegation probabilities.

## Live application

- Dashboard: https://football-season-predictor.vercel.app
- API health check: https://football-season-predictor-api.onrender.com/api/health
- Interactive API documentation: https://football-season-predictor-api.onrender.com/docs

The API uses Render's free service tier, so the first request after inactivity can take about a minute while the service starts.

## Features

- Simulated final standings for all 20 Premier League teams
- Title, top-four, top-six, and relegation probabilities
- Expected points, goal difference, and finishing position
- Individual match outcome and likely-score predictions
- Attack and defence power ratings
- Current league table calculated from completed results
- Historical model backtesting with understandable accuracy metrics
- Automatic current-season data updates with validation and backups
- Visible loading, failure, and retry states in the dashboard

## How it works

The prediction pipeline has two stages:

1. A Poisson regression estimates each team's attacking strength, defensive weakness, and the effect of playing at home.
2. A fitted Dixon-Coles correction adjusts the unusually correlated low-scoring results: 0-0, 1-0, 0-1, and 1-1.

For every unplayed fixture, the model produces a corrected score distribution. The simulation engine samples from those distributions across 10,000 complete seasons and aggregates the final league positions.

Newly promoted teams are seeded using their previous Championship performance, adjusted toward Premier League expectations. This prevents a promoted club's rating from depending on only its first few top-flight matches.

## Backtest results

The model is trained on the first 304 matches of the 2025/26 season and evaluated on the final 76 matches, which remain unseen during training.

| Metric | Result |
| --- | ---: |
| Match outcome accuracy | 51.3% |
| Exact score accuracy | 11.8% |
| Mean absolute goal error | 0.899 |
| Log loss | 1.008 |
| Simple-baseline log loss | 1.065 |
| Log-loss improvement over baseline | 5.3% |
| Brier score | 0.596 |

The chronological split prevents future results from leaking into model training. These figures measure historical performance; they do not guarantee future accuracy.

## Architecture

```text
Football-Data CSV files
        |
        v
Data cleaning and promoted-team priors
        |
        v
Poisson team-strength model + Dixon-Coles correction
        |
        +-----------------> Individual match predictions
        |
        v
10,000-run Monte Carlo season simulation
        |
        v
FastAPI backend on Render
        |
        v
React dashboard on Vercel
```

## Technology

- Backend: Python 3.12, FastAPI, pandas, NumPy, SciPy, statsmodels
- Frontend: React 19, Vite, Lucide React
- Testing: pytest and Oxlint
- Hosting: Render and Vercel
- Results source: [Football-Data](https://www.football-data.co.uk/englandm.php)

## Run locally on Windows with Git Bash

```bash
git clone https://github.com/abdulla-cc/football-season-predictor.git
cd football-season-predictor
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python -m uvicorn src.api:app --reload
```

The API will be available at http://127.0.0.1:8000. Keep that terminal running.

In a second Git Bash terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173.

## Test the project

Run the backend suite from the repository root:

```bash
./.venv/Scripts/python.exe -m pytest
```

Check and build the frontend:

```bash
cd frontend
npm run lint
npm run build
```

## Update match data

The deployed API checks for fresh results every six hours. To update the local CSV manually:

```bash
./.venv/Scripts/python.exe -m src.data_updater
```

The updater validates the schema and team count, refuses older datasets, and creates a backup before replacing changed data.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service and model status |
| `GET` | `/api/teams` | Current Premier League teams |
| `GET` | `/api/season-status` | Completed and remaining fixture counts |
| `GET` | `/api/current-table` | Standings from completed matches |
| `GET` | `/api/team-strengths` | Fitted attack and defence ratings |
| `GET` | `/api/evaluation` | Historical backtest metrics |
| `GET` | `/api/simulation` | Public cached full-season forecast |
| `POST` | `/api/predict-match` | Individual fixture prediction |
| `POST` | `/api/admin/update-data` | Protected current-results update |
| `POST` | `/api/admin/simulation/refresh` | Protected simulation refresh |

Admin endpoints require the `X-Admin-Key` request header. The key is generated and stored by Render and is never included in frontend code or source control.

## Current limitations

- Forecast quality is limited by the model features and available match history.
- Injuries, transfers, lineups, player-level data, and expected-goals feeds are not included.
- The Render free service can be slow on the first request after inactivity.
- The API currently permits cross-origin requests broadly until production CORS is restricted.
- La Liga and Serie A are planned but not implemented.

## Disclaimer

This is a portfolio and educational project. Its forecasts are probabilistic estimates and should not be used as betting or financial advice.
