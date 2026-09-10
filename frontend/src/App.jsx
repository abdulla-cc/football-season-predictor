import React, { useState, useEffect } from 'react'
import { Trophy, Shield, Swords, RefreshCw, Activity, Flame, Award, AlertTriangle } from 'lucide-react'

const API_BASE = "http://127.0.0.1:8000"

// Premier League club colors / badges preview helper
const CLUB_COLORS = {
  "Arsenal": "#EF0107",
  "Aston Villa": "#95BFE5",
  "Bournemouth": "#DA291C",
  "Brentford": "#E30613",
  "Brighton": "#0057B8",
  "Chelsea": "#034694",
  "Coventry": "#00AEEF",
  "Crystal Palace": "#1B458F",
  "Everton": "#003399",
  "Fulham": "#FFFFFF",
  "Hull": "#F5A623",
  "Ipswich": "#0047AB",
  "Leeds": "#FFCD00",
  "Liverpool": "#C8102E",
  "Man City": "#6CABDD",
  "Man United": "#DA291C",
  "Newcastle": "#241F20",
  "Nottingham Forest": "#DD0000",
  "Sunderland": "#EB172B",
  "Tottenham": "#132257"
}

export default function App() {
  const [activeTab, setActiveTab] = useState('forecast')
  const [simData, setSimData] = useState([])
  const [currentTable, setCurrentTable] = useState([])
  const [strengths, setStrengths] = useState([])
  const [teams, setTeams] = useState([])
  const [loadingSim, setLoadingSim] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)

  // Match Predictor state
  const [homeTeam, setHomeTeam] = useState('Arsenal')
  const [awayTeam, setAwayTeam] = useState('Chelsea')
  const [prediction, setPrediction] = useState(null)
  const [predicting, setPredicting] = useState(false)

  // Fetch initial data
  useEffect(() => {
    fetchSimulation()
    fetchCurrentTable()
    fetchStrengths()
    fetchTeams()
  }, [])

  const fetchTeams = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/teams`)
      const data = await res.json()
      if (data.teams) {
        setTeams(data.teams)
        if (!homeTeam && data.teams.length > 0) setHomeTeam(data.teams[0])
        if (!awayTeam && data.teams.length > 1) setAwayTeam(data.teams[1])
      }
    } catch (e) {
      console.warn("Using default teams list", e)
    }
  }

  const fetchSimulation = async (refresh = false) => {
    setLoadingSim(true)
    try {
      const url = `${API_BASE}/api/simulation${refresh ? '?refresh=true' : ''}`
      const res = await fetch(url)
      const data = await res.json()
      setSimData(data)
    } catch (e) {
      console.error("Failed to load simulation:", e)
    } finally {
      setLoadingSim(false)
      setInitialLoading(false)
    }
  }

  const fetchCurrentTable = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/current-table`)
      const data = await res.json()
      setCurrentTable(data)
    } catch (e) {
      console.error("Failed to load current table:", e)
    }
  }

  const fetchStrengths = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/team-strengths`)
      const data = await res.json()
      setStrengths(data)
    } catch (e) {
      console.error("Failed to load strengths:", e)
    }
  }

  // Predict match
  useEffect(() => {
    if (homeTeam && awayTeam && homeTeam !== awayTeam) {
      runPrediction(homeTeam, awayTeam)
    }
  }, [homeTeam, awayTeam])

  const runPrediction = async (h, a) => {
    setPredicting(true)
    try {
      const res = await fetch(`${API_BASE}/api/predict-match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ home_team: h, away_team: a })
      })
      const data = await res.json()
      setPrediction(data)
    } catch (e) {
      console.error("Prediction failed:", e)
    } finally {
      setPredicting(false)
    }
  }

  // Top Title favorite and high risk teams
  const titleFavorite = simData.length > 0 ? simData[0] : null
  const relFavorite = simData.length > 0 ? [...simData].sort((a, b) => b['Relegation_%'] - a['Relegation_%'])[0] : null

  return (
    <div className="app-container">
      {/* Brand Header */}
      <header className="header">
        <div className="brand">
          <div className="brand-icon">🦁</div>
          <div>
            <div className="brand-title">PREMIER LEAGUE PREDICTOR</div>
            <div className="brand-subtitle">
              <span>Season 2026/27</span>
              <span className="tag-badge">Monte Carlo (10k Runs)</span>
              <span className="tag-badge">Poisson MLE Engine</span>
            </div>
          </div>
        </div>

        <button 
          className="sim-btn" 
          onClick={() => fetchSimulation(true)}
          disabled={loadingSim}
        >
          <RefreshCw size={16} className={loadingSim ? 'spin' : ''} />
          {loadingSim ? 'Simulating 10,000 Seasons...' : 'Re-Run Simulation'}
        </button>
      </header>

      {/* Overview Stat Strip */}
      {simData.length > 0 && (
        <div className="stats-strip">
          <div className="stat-box title-box">
            <div className="stat-label">
              <span>Title Favorite</span>
              <Trophy size={16} color="#00ff87" />
            </div>
            <div className="stat-value">{titleFavorite?.Team}</div>
            <div className="stat-sub">{titleFavorite?.['Title_%']}% Title Probability ({titleFavorite?.Exp_Pts} pts)</div>
          </div>

          <div className="stat-box top4-box">
            <div className="stat-label">
              <span>Top 4 Lock</span>
              <Award size={16} color="#00f0ff" />
            </div>
            <div className="stat-value">{simData[1]?.Team}</div>
            <div className="stat-sub">{simData[1]?.['Top4_%']}% Champions League Odds</div>
          </div>

          <div className="stat-box rel-box">
            <div className="stat-label">
              <span>Highest Relegation Risk</span>
              <AlertTriangle size={16} color="#ff3366" />
            </div>
            <div className="stat-value">{relFavorite?.Team}</div>
            <div className="stat-sub">{relFavorite?.['Relegation_%']}% Chance of Relegation</div>
          </div>

          <div className="stat-box sim-box">
            <div className="stat-label">
              <span>Simulation Engine</span>
              <Activity size={16} color="#ffd166" />
            </div>
            <div className="stat-value">10,000 Runs</div>
            <div className="stat-sub">350 remaining fixtures played</div>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="tabs">
        <button 
          className={`tab-btn ${activeTab === 'forecast' ? 'active' : ''}`}
          onClick={() => setActiveTab('forecast')}
        >
          <Trophy size={16} /> Season Forecast (20 Teams)
        </button>

        <button 
          className={`tab-btn ${activeTab === 'predictor' ? 'active' : ''}`}
          onClick={() => setActiveTab('predictor')}
        >
          <Swords size={16} /> Match Predictor
        </button>

        <button 
          className={`tab-btn ${activeTab === 'powers' ? 'active' : ''}`}
          onClick={() => setActiveTab('powers')}
        >
          <Shield size={16} /> Attack & Defense Ratings
        </button>

        <button 
          className={`tab-btn ${activeTab === 'standings' ? 'active' : ''}`}
          onClick={() => setActiveTab('standings')}
        >
          <Activity size={16} /> Actual Standings (Played)
        </button>
      </div>

      {/* TAB 1: FULL SEASON FORECAST (ALL 20 TEAMS) */}
      {activeTab === 'forecast' && (
        <div className="table-container">
          <div className="table-header">
            <div>
              <div className="table-title">Simulated Final Standings & Probability Distribution</div>
              <div style={{ fontSize: '12px', color: '#8e99b0', marginTop: '4px' }}>
                Based on 10,000 independent season simulations combining actual 2026/27 results + Poisson match sampling.
              </div>
            </div>
          </div>

          <table className="league-table">
            <thead>
              <tr>
                <th style={{ width: '50px' }}>Pos</th>
                <th>Club</th>
                <th>Exp Pts</th>
                <th>Exp GD</th>
                <th>Exp Pos</th>
                <th style={{ width: '160px' }}>Title %</th>
                <th style={{ width: '160px' }}>Top 4 (UCL)</th>
                <th style={{ width: '160px' }}>Top 6 (UEL)</th>
                <th style={{ width: '160px' }}>Relegation %</th>
              </tr>
            </thead>
            <tbody>
              {simData.map((row, idx) => {
                const pos = idx + 1
                let zoneClass = 'row-mid'
                let rankClass = 'rank-mid'
                if (pos === 1) { zoneClass = 'row-ucl'; rankClass = 'rank-1' }
                else if (pos <= 4) { zoneClass = 'row-ucl'; rankClass = 'rank-ucl' }
                else if (pos <= 6) { zoneClass = 'row-uel'; rankClass = 'rank-uel' }
                else if (pos >= 18) { zoneClass = 'row-rel'; rankClass = 'rank-rel' }

                return (
                  <tr key={row.Team} className={zoneClass}>
                    <td>
                      <span className={`rank-badge ${rankClass}`}>{pos}</span>
                    </td>
                    <td>
                      <div className="team-cell">
                        <span 
                          style={{
                            width: '10px',
                            height: '10px',
                            borderRadius: '50%',
                            backgroundColor: CLUB_COLORS[row.Team] || '#fff',
                            display: 'inline-block'
                          }}
                        />
                        <span>{row.Team}</span>
                      </div>
                    </td>
                    <td style={{ fontWeight: '700', color: '#fff' }}>{row.Exp_Pts}</td>
                    <td>{row.Exp_GD > 0 ? `+${row.Exp_GD}` : row.Exp_GD}</td>
                    <td style={{ color: '#8e99b0' }}>{row.Exp_Rank}</td>

                    {/* Title % */}
                    <td className="prob-bar-cell">
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                        <span>{row['Title_%']}%</span>
                      </div>
                      <div className="prob-bar-bg">
                        <div 
                          className="prob-bar-fill fill-title" 
                          style={{ width: `${Math.min(100, row['Title_%'] * 1.2)}%` }} 
                        />
                      </div>
                    </td>

                    {/* Top 4 % */}
                    <td className="prob-bar-cell">
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                        <span>{row['Top4_%']}%</span>
                      </div>
                      <div className="prob-bar-bg">
                        <div 
                          className="prob-bar-fill fill-top4" 
                          style={{ width: `${row['Top4_%']}%` }} 
                        />
                      </div>
                    </td>

                    {/* Top 6 % */}
                    <td className="prob-bar-cell">
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                        <span>{row['Top6_%']}%</span>
                      </div>
                      <div className="prob-bar-bg">
                        <div 
                          className="prob-bar-fill" 
                          style={{ width: `${row['Top6_%']}%`, background: '#ffd166' }} 
                        />
                      </div>
                    </td>

                    {/* Relegation % */}
                    <td className="prob-bar-cell">
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                        <span style={{ color: row['Relegation_%'] > 20 ? '#ff3366' : 'inherit' }}>
                          {row['Relegation_%']}%
                        </span>
                      </div>
                      <div className="prob-bar-bg">
                        <div 
                          className="prob-bar-fill fill-rel" 
                          style={{ width: `${row['Relegation_%']}%` }} 
                        />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 2: MATCH PREDICTOR */}
      {activeTab === 'predictor' && (
        <div className="predictor-grid">
          <div className="fixture-selector">
            <div className="team-select-box">
              <label>Home Team</label>
              <select 
                className="select-input" 
                value={homeTeam} 
                onChange={(e) => setHomeTeam(e.target.value)}
              >
                {(teams.length > 0 ? teams : Object.keys(CLUB_COLORS)).map(t => (
                  <option key={t} value={t} disabled={t === awayTeam}>{t}</option>
                ))}
              </select>
            </div>

            <div className="vs-badge">VS</div>

            <div className="team-select-box">
              <label>Away Team</label>
              <select 
                className="select-input" 
                value={awayTeam} 
                onChange={(e) => setAwayTeam(e.target.value)}
              >
                {(teams.length > 0 ? teams : Object.keys(CLUB_COLORS)).map(t => (
                  <option key={t} value={t} disabled={t === homeTeam}>{t}</option>
                ))}
              </select>
            </div>
          </div>

          {prediction && (
            <div className="prediction-result">
              <div style={{ fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px', color: '#8e99b0' }}>
                Poisson Expected Goals (xG)
              </div>

              <div className="xg-score">
                <div className="xg-team">{prediction.home_team}</div>
                <div className="xg-num">{prediction.home_xg}</div>
                <div style={{ color: '#8e99b0', fontSize: '32px' }}>–</div>
                <div className="xg-num" style={{ color: '#00b4d8' }}>{prediction.away_xg}</div>
                <div className="xg-team">{prediction.away_team}</div>
              </div>

              {/* Probability Split Bar */}
              <div className="prob-split-bar">
                <div 
                  className="split-segment segment-home" 
                  style={{ width: `${prediction.home_win_prob}%` }}
                >
                  {prediction.home_win_prob > 12 && `${prediction.home_team} ${prediction.home_win_prob}%`}
                </div>
                <div 
                  className="split-segment segment-draw" 
                  style={{ width: `${prediction.draw_prob}%` }}
                >
                  {prediction.draw_prob > 10 && `Draw ${prediction.draw_prob}%`}
                </div>
                <div 
                  className="split-segment segment-away" 
                  style={{ width: `${prediction.away_win_prob}%` }}
                >
                  {prediction.away_win_prob > 12 && `${prediction.away_team} ${prediction.away_win_prob}%`}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-around', fontSize: '13px', color: '#8e99b0' }}>
                <span>Home Win: <strong style={{ color: '#00b4d8' }}>{prediction.home_win_prob}%</strong></span>
                <span>Draw: <strong style={{ color: '#fff' }}>{prediction.draw_prob}%</strong></span>
                <span>Away Win: <strong style={{ color: '#e63946' }}>{prediction.away_win_prob}%</strong></span>
              </div>

              {/* Most likely scorelines */}
              <div style={{ marginTop: '28px' }}>
                <div style={{ fontSize: '12px', textTransform: 'uppercase', color: '#8e99b0', letterSpacing: '0.8px', marginBottom: '12px' }}>
                  Most Likely Scorelines
                </div>
                <div className="scorelines-list">
                  {prediction.top_scorelines.map(([score, prob], i) => (
                    <div key={i} className="scoreline-pill">
                      <span className="scoreline-goals">{score}</span>
                      <span className="scoreline-pct">{(prob * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* H2H Insights */}
              {prediction.h2h_insights && prediction.h2h_insights.length > 0 && (
                <div style={{ marginTop: '36px', paddingTop: '24px', borderTop: '1px solid #23293b', textAlign: 'left' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: '#ffd166' }}>
                    <Activity size={18} />
                    <span style={{ fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Head-to-Head Facts (Since 2024)
                    </span>
                  </div>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {prediction.h2h_insights.map((fact, idx) => (
                      <li key={idx} style={{ 
                        fontSize: '14px', 
                        color: '#f0f3f8', 
                        background: 'rgba(255, 255, 255, 0.03)',
                        padding: '12px 16px',
                        borderRadius: '8px',
                        borderLeft: '3px solid #00f0ff'
                      }}>
                        {fact}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: ATTACK & DEFENSE POWER RATINGS */}
      {activeTab === 'powers' && (
        <div className="table-container">
          <div className="table-header">
            <div className="table-title">Fitted Team Attack & Defense Strengths</div>
            <div style={{ fontSize: '12px', color: '#8e99b0' }}>
              Estimates derived via Poisson Maximum Likelihood Estimation (MLE).
            </div>
          </div>

          <table className="league-table">
            <thead>
              <tr>
                <th>Club</th>
                <th>Attack Strength (α)</th>
                <th>Defense Weakness (β)</th>
                <th>Interpretation</th>
              </tr>
            </thead>
            <tbody>
              {strengths.map(s => (
                <tr key={s.Team}>
                  <td style={{ fontWeight: '700' }}>{s.Team}</td>
                  <td style={{ color: s.Attack_Strength > 0 ? '#00ff87' : '#e63946', fontWeight: '700' }}>
                    {s.Attack_Strength > 0 ? `+${s.Attack_Strength}` : s.Attack_Strength}
                  </td>
                  <td style={{ color: s.Defense_Weakness < 0.5 ? '#00f0ff' : '#ffd166' }}>
                    {s.Defense_Weakness}
                  </td>
                  <td style={{ color: '#8e99b0', fontSize: '12px' }}>
                    {s.Attack_Strength > 0.05 ? '⚡ Elite Attack' : s.Attack_Strength > -0.1 ? '⚔️ Solid Attack' : '🛡️ Low Scoring'} 
                    {' • '}
                    {s.Defense_Weakness < 0.4 ? '🧱 Rock Solid Defense' : s.Defense_Weakness > 0.7 ? '⚠️ Leaky Defense' : 'Average Defense'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 4: ACTUAL STANDINGS (SO FAR) */}
      {activeTab === 'standings' && (
        <div className="table-container">
          <div className="table-header">
            <div className="table-title">Actual Premier League 2026/27 Results (Gameweek 3)</div>
            <div style={{ fontSize: '12px', color: '#8e99b0' }}>
              Official results so far from football-data.co.uk before simulation.
            </div>
          </div>

          <table className="league-table">
            <thead>
              <tr>
                <th style={{ width: '40px' }}>#</th>
                <th>Team</th>
                <th>P</th>
                <th>W</th>
                <th>D</th>
                <th>L</th>
                <th>GF</th>
                <th>GA</th>
                <th>GD</th>
                <th>Pts</th>
              </tr>
            </thead>
            <tbody>
              {currentTable.map((r, i) => (
                <tr key={r.Team}>
                  <td><span className="rank-badge">{i + 1}</span></td>
                  <td style={{ fontWeight: '700' }}>{r.Team}</td>
                  <td>{r.Played}</td>
                  <td>{r.Wins}</td>
                  <td>{r.Draws}</td>
                  <td>{r.Losses}</td>
                  <td>{r.GF}</td>
                  <td>{r.GA}</td>
                  <td>{r.GD > 0 ? `+${r.GD}` : r.GD}</td>
                  <td style={{ fontWeight: '800', color: '#00ff87' }}>{r.Points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
