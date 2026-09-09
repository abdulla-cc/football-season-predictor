# Football Season Predictor — Project Plan

## Overview
Portfolio ML project (next after the Job Application Tracker). Predicts the 2026/27 season outcome for the **Premier League**, with **La Liga** and **Serie A** planned as extensions once the EPL pipeline is proven.

Goal isn't just "predict a match" — it's a full **season simulation system** that outputs live probabilities: title odds, top-4 odds, relegation odds, per team, updating as real results come in each gameweek.

## Framing
Two possible ML framings were considered:
- **Match-by-match predictor** — simpler; predicts each upcoming fixture in isolation.
- **Full season Monte Carlo simulation** *(chosen)* — a match-outcome model feeds a simulation engine that plays out the rest of the season thousands of times, producing a probability distribution over final league standings. This is the approach used by outlets like FiveThirtyEight's SPI, and is a stronger portfolio piece because it's a two-stage system (predictive model → probabilistic simulation), not just a classifier.

## Sequencing
Build the **EPL pipeline fully end-to-end first** (data → model → simulation → dashboard), then generalize to La Liga and Serie A — the feature engineering and simulation logic should transfer with minimal rework once the pipeline is solid.

## Technical Approach

### 1. Match outcome model
Use a **Poisson / Dixon-Coles model**: each team gets an attack strength and defense strength rating; predict *expected goals* for each side in a fixture. Two Poisson distributions derive P(home win) / P(draw) / P(away win) and likely scorelines. This is more standard in football analytics than a raw classifier, and plugs directly into the simulation step — goals are sampled straight from the fitted distributions.

### 2. Monte Carlo simulation
For every remaining fixture in the season, simulate results thousands of times (e.g. 10,000 full-season run-throughs) using the model's probabilities, tally final points/goal difference each run, and aggregate. Output per team: title win %, top-4 %, relegation %.

### 3. Dashboard
Live probability table/chart, updated as real results come in each gameweek. Streamlit (used twice before — fast) or a small React frontend for variety.

### Known wrinkle: promoted teams
Coventry City, Ipswich Town, and Hull City were just promoted and have **no Premier League history** — their attack/defense ratings would be unreliable if trained only on PL data. Plan: seed their initial ratings from last season's Championship stats, shrunk toward the league average, then let the model update as real 2026/27 results accumulate.

## Data Sources
- **Historical results** (for fitting strength ratings): football-data.co.uk — free CSVs, decades of history, includes odds data
- **2026/27 season results-so-far + upcoming fixtures**: same site's current-season CSV (updated weekly), or API-Football (free tier, rate-limited) for fresher data

## Milestones (EPL only, ~2-4 hrs/week pace)
1. **Data pipeline** — pull historical + current-season EPL data into one clean dataset
2. **Poisson/Dixon-Coles model** — fit attack/defense ratings, validate against actual 2026/27 results so far
3. **Simulation engine** — Monte Carlo the remaining fixtures, output title/top-4/relegation probabilities
4. **Dashboard** — Streamlit or React, deployed
5. *(Later)* Extend the same pipeline to La Liga and Serie A

## Context
- Season started **21 August 2026**; as of project kickoff, ~3 gameweeks played.
- Follows the Job Application Tracker (FastAPI + SQLModel + React + Groq), pushed to GitHub at github.com/abdulla-cc/job-tracker.
