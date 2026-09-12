import React, { useState, useEffect } from 'react'
import './editorial.css'
import { Trophy, Shield, Swords, RefreshCw, Activity, Award, AlertTriangle, BarChart3 } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
const SERVER_WAKE_TIMEOUT_MS = 75_000
const HEALTH_RETRY_DELAY_MS = 3_000

const wait = (milliseconds) => new Promise(resolve => setTimeout(resolve, milliseconds))

async function fetchJson(path, options, timeoutMs = 120_000) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('The prediction server is taking longer than expected to respond.')
    }
    throw new Error('Cannot reach the prediction server. Wait a moment and try again.')
  } finally {
    clearTimeout(timeout)
  }
  let data
  try {
    data = await response.json()
  } catch {
    throw new Error(`Server returned an unreadable response (${response.status}).`)
  }
  if (!response.ok) {
    throw new Error(data.detail || `Request failed with status ${response.status}.`)
  }
  return data
}

// Crest source: https://www.footylogos.com/competition/premier-league
const CLUB_BADGES = {
  "Arsenal": "arsenal",
  "Aston Villa": "aston-villa",
  "Bournemouth": "afc-bournemouth",
  "Brentford": "brentford",
  "Brighton": "brighton-and-hove-albion",
  "Chelsea": "chelsea",
  "Coventry": "coventry-city",
  "Crystal Palace": "crystal-palace",
  "Everton": "everton",
  "Fulham": "fulham",
  "Hull": "hull-city",
  "Ipswich": "ipswich-town",
  "Leeds": "leeds-united",
  "Liverpool": "liverpool-fc",
  "Man City": "manchester-city",
  "Man United": "manchester-united",
  "Newcastle": "newcastle-united",
  "Nottingham Forest": "nottingham-forest",
  "Sunderland": "sunderland",
  "Tottenham": "tottenham-hotspur"
}

function ClubBadge({ team }) {
  const slug = CLUB_BADGES[team]
  return slug ? <img className="club-badge" src={`https://assets.footylogos.com/previews/${slug}/${slug}-logo-footylogos-320.webp`} alt={`${team} crest`} /> : null
}

export default function App() {
  const [activeTab, setActiveTab] = useState('forecast')
  const [simData, setSimData] = useState([])
  const [currentTable, setCurrentTable] = useState([])
  const [strengths, setStrengths] = useState([])
  const [teams, setTeams] = useState([])
  const [evaluation, setEvaluation] = useState(null)
  const [seasonStatus, setSeasonStatus] = useState(null)
  const [loadingSim, setLoadingSim] = useState(true)
  const [loadingTable, setLoadingTable] = useState(true)
  const [loadingStrengths, setLoadingStrengths] = useState(false)
  const [loadingEvaluation, setLoadingEvaluation] = useState(false)
  const [requestErrors, setRequestErrors] = useState({})
  const [serverStatus, setServerStatus] = useState('waking')

  // Match Predictor state
  const [homeTeam, setHomeTeam] = useState('Arsenal')
  const [awayTeam, setAwayTeam] = useState('Chelsea')
  const [prediction, setPrediction] = useState(null)
  const [predicting, setPredicting] = useState(false)
  const [predictionError, setPredictionError] = useState('')

  const setRequestError = (key, error = null) => {
    setRequestErrors(current => {
      const next = { ...current }
      if (error) next[key] = error.message || String(error)
      else delete next[key]
      return next
    })
  }

  const fetchTeams = async () => {
    try {
      setRequestError('teams')
      const data = await fetchJson('/api/teams')
      if (data.teams) {
        setTeams(data.teams)
        if (!homeTeam && data.teams.length > 0) setHomeTeam(data.teams[0])
        if (!awayTeam && data.teams.length > 1) setAwayTeam(data.teams[1])
      }
    } catch (e) {
      setRequestError('teams', e)
      console.warn("Using default teams list", e)
    }
  }

  const fetchSimulation = async () => {
    setLoadingSim(true)
    try {
      setRequestError('simulation')
      const data = await fetchJson('/api/simulation')
      setSimData(data)
    } catch (e) {
      setRequestError('simulation', e)
      console.error("Failed to load simulation:", e)
    } finally {
      setLoadingSim(false)
    }
  }

  const fetchCurrentTable = async () => {
    setLoadingTable(true)
    try {
      setRequestError('standings')
      const data = await fetchJson('/api/current-table')
      setCurrentTable(data)
    } catch (e) {
      setRequestError('standings', e)
      console.error("Failed to load current table:", e)
    } finally {
      setLoadingTable(false)
    }
  }

  const fetchStrengths = async () => {
    setLoadingStrengths(true)
    try {
      setRequestError('strengths')
      const data = await fetchJson('/api/team-strengths')
      setStrengths(data)
    } catch (e) {
      setRequestError('strengths', e)
      console.error("Failed to load strengths:", e)
    } finally {
      setLoadingStrengths(false)
    }
  }

  const fetchEvaluation = async () => {
    setLoadingEvaluation(true)
    try {
      setRequestError('evaluation')
      const data = await fetchJson('/api/evaluation')
      setEvaluation(data)
    } catch (e) {
      setRequestError('evaluation', e)
      console.error("Failed to load model evaluation:", e)
    } finally {
      setLoadingEvaluation(false)
    }
  }

  const fetchSeasonStatus = async () => {
    try {
      setRequestError('season status')
      const data = await fetchJson('/api/season-status')
      setSeasonStatus(data)
    } catch (e) {
      setRequestError('season status', e)
      console.error("Failed to load season status:", e)
    }
  }

  const wakeServerAndLoad = async () => {
    setServerStatus('waking')
    const deadline = Date.now() + SERVER_WAKE_TIMEOUT_MS

    while (Date.now() < deadline) {
      try {
        await fetchJson('/api/health', undefined, 12_000)
        setServerStatus('ready')
        await Promise.allSettled([
          fetchSimulation(),
          fetchCurrentTable(),
          fetchTeams(),
          fetchSeasonStatus()
        ])
        return
      } catch {
        if (Date.now() < deadline) await wait(HEALTH_RETRY_DELAY_MS)
      }
    }

    setLoadingSim(false)
    setLoadingTable(false)
    setServerStatus('failed')
  }

  const runPrediction = async (h, a) => {
    setPredicting(true)
    setPredictionError('')
    try {
      const data = await fetchJson('/api/predict-match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ home_team: h, away_team: a })
      })
      setPrediction(data)
    } catch (e) {
      setPredictionError(e.message || 'Prediction failed.')
      console.error("Prediction failed:", e)
    } finally {
      setPredicting(false)
    }
  }

  // These effects intentionally react to view state; request functions are kept
  // outside their dependency lists so a state update cannot retrigger a fetch loop.
  useEffect(() => {
    wakeServerAndLoad()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (serverStatus !== 'ready') return
    if (activeTab === 'powers' && strengths.length === 0) fetchStrengths()
    if (activeTab === 'evaluation' && !evaluation) fetchEvaluation()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, strengths.length, evaluation, serverStatus])

  useEffect(() => {
    if (serverStatus === 'ready' && activeTab === 'predictor' && homeTeam && awayTeam && homeTeam !== awayTeam) {
      runPrediction(homeTeam, awayTeam)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, homeTeam, awayTeam, serverStatus])

  const retryVisibleData = () => {
    wakeServerAndLoad()
  }

  // Top Title favorite and high risk teams
  const titleFavorite = simData.length > 0 ? simData[0] : null
  const relFavorite = simData.length > 0 ? [...simData].sort((a, b) => b['Relegation_%'] - a['Relegation_%'])[0] : null

  return (
    <div className="app-container">
      {/* Brand Header */}
      <header className="header">
        <div className="brand">
          <img className="brand-icon" src="https://assets.footylogos.com/logos/premier-league-england/premier-league-england-logo-footylogos.svg" alt="Premier League" />
          <div>
            <div className="brand-title">Premier League forecast</div>
            <div className="brand-subtitle">
              <span>Season 2026/27</span>
              <span className="tag-badge">Monte Carlo (10k Runs)</span>
              <span className="tag-badge">Dixon-Coles Engine</span>
            </div>
          </div>
        </div>

      </header>

      {serverStatus === 'waking' && (
        <div className="server-banner" role="status">
          <RefreshCw className="spin" size={20} />
          <div>
            <strong>Waking the prediction server…</strong>
            <span>Render’s free service can take up to a minute after inactivity. The dashboard will load automatically.</span>
          </div>
        </div>
      )}

      {serverStatus === 'failed' && (
        <div className="error-banner" role="alert">
          <AlertTriangle size={20} />
          <div>
            <strong>The prediction server did not wake in time.</strong>
            <span>Render may still be starting. Wait a moment, then try again.</span>
          </div>
          <button className="retry-btn" onClick={wakeServerAndLoad}>Try Again</button>
        </div>
      )}

      {Object.keys(requestErrors).length > 0 && (
        <div className="error-banner" role="alert">
          <AlertTriangle size={20} />
          <div>
            <strong>Some dashboard data could not be loaded.</strong>
            <span>{Object.entries(requestErrors).map(([key, message]) => `${key}: ${message}`).join(' · ')}</span>
          </div>
          <button className="retry-btn" onClick={retryVisibleData}>Try Again</button>
        </div>
      )}

      {/* Overview Stat Strip */}
      {simData.length > 0 && (
        <div className="stats-strip">
          <div className="stat-box title-box">
            <div className="stat-label">
              <span>Title Favorite</span>
              <Trophy size={16} color="#00ff87" />
            </div>
            <div className="stat-value"><ClubBadge team={titleFavorite?.Team} />{titleFavorite?.Team}</div>
            <div className="stat-sub">{titleFavorite?.['Title_%']}% Title Probability ({titleFavorite?.Exp_Pts} pts)</div>
          </div>

          <div className="stat-box top4-box">
            <div className="stat-label">
              <span>Top-four contender</span>
              <Award size={16} color="#00f0ff" />
            </div>
            <div className="stat-value"><ClubBadge team={simData[1]?.Team} />{simData[1]?.Team}</div>
            <div className="stat-sub">{simData[1]?.['Top4_%']}% Champions League Odds</div>
          </div>

          <div className="stat-box rel-box">
            <div className="stat-label">
              <span>Highest Relegation Risk</span>
              <AlertTriangle size={16} color="#ff3366" />
            </div>
            <div className="stat-value"><ClubBadge team={relFavorite?.Team} />{relFavorite?.Team}</div>
            <div className="stat-sub">{relFavorite?.['Relegation_%']}% Chance of Relegation</div>
          </div>

          <div className="stat-box sim-box">
            <div className="stat-label">
              <span>Simulation Engine</span>
              <Activity size={16} color="#ffd166" />
            </div>
            <div className="stat-value">10,000 Runs</div>
            <div className="stat-sub">
              {seasonStatus
                ? `${seasonStatus.remaining_fixtures} remaining fixtures · ${seasonStatus.season_complete_pct}% complete`
                : 'Calculating season progress...'}
            </div>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="tabs">
        <button 
          className={`tab-btn ${activeTab === 'forecast' ? 'active' : ''}`}
          onClick={() => setActiveTab('forecast')}
        >
          <Trophy size={16} /> Season forecast
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

        <button
          className={`tab-btn ${activeTab === 'evaluation' ? 'active' : ''}`}
          onClick={() => setActiveTab('evaluation')}
        >
          <BarChart3 size={16} /> Model Accuracy
        </button>
      </div>

      {/* TAB 1: FULL SEASON FORECAST (ALL 20 TEAMS) */}
      {activeTab === 'forecast' && (
        <div className="table-container">
          <div className="table-header">
            <div>
              <div className="table-title">How the season could finish</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Based on 10,000 independent season simulations combining actual 2026/27 results + Dixon-Coles score sampling.
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
              {loadingSim && simData.length === 0 ? (
                <tr><td colSpan="9"><div className="table-state"><RefreshCw className="spin" size={22} />Running the first season simulation…</div></td></tr>
              ) : requestErrors.simulation && simData.length === 0 ? (
                <tr><td colSpan="9"><div className="table-state error-text">Season forecast is unavailable. Use “Try Again” above.</div></td></tr>
              ) : simData.map((row, idx) => {
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
                        <ClubBadge team={row.Team} />
                        <span>{row.Team}</span>
                      </div>
                    </td>
                    <td style={{ fontWeight: '700', color: 'var(--text-main)' }}>{row.Exp_Pts}</td>
                    <td>{row.Exp_GD > 0 ? `+${row.Exp_GD}` : row.Exp_GD}</td>
                    <td style={{ color: 'var(--text-muted)' }}>{row.Exp_Rank}</td>

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
                          style={{ width: `${row['Top6_%']}%`, background: 'var(--gold)' }}
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
                {(teams.length > 0 ? teams : Object.keys(CLUB_BADGES)).map(t => (
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
                {(teams.length > 0 ? teams : Object.keys(CLUB_BADGES)).map(t => (
                  <option key={t} value={t} disabled={t === homeTeam}>{t}</option>
                ))}
              </select>
            </div>
          </div>

          {predicting && (
            <div className="section-state"><RefreshCw className="spin" size={22} />Calculating match probabilities…</div>
          )}

          {predictionError && !predicting && (
            <div className="section-state error-text" role="alert">
              <AlertTriangle size={22} />
              <span>{predictionError}</span>
              <button className="retry-btn" onClick={() => runPrediction(homeTeam, awayTeam)}>Try Again</button>
            </div>
          )}

          {prediction && !predicting && !predictionError && (
            <div className="prediction-result">
              <div style={{ fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-muted)' }}>
                Dixon-Coles Expected Goals (xG)
              </div>

              <div className="xg-score">
                <div className="xg-team"><ClubBadge team={prediction.home_team} />{prediction.home_team}</div>
                <div className="xg-num">{prediction.home_xg}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '32px' }}>–</div>
                <div className="xg-num" style={{ color: '#00b4d8' }}>{prediction.away_xg}</div>
                <div className="xg-team"><ClubBadge team={prediction.away_team} />{prediction.away_team}</div>
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

              <div style={{ display: 'flex', justifyContent: 'space-around', fontSize: '13px', color: 'var(--text-muted)' }}>
                <span>Home Win: <strong style={{ color: '#00b4d8' }}>{prediction.home_win_prob}%</strong></span>
                <span>Draw: <strong style={{ color: 'var(--text-main)' }}>{prediction.draw_prob}%</strong></span>
                <span>Away Win: <strong style={{ color: '#e63946' }}>{prediction.away_win_prob}%</strong></span>
              </div>

              {/* Most likely scorelines */}
              <div style={{ marginTop: '28px' }}>
                <div style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.8px', marginBottom: '12px' }}>
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
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: 'var(--gold)' }}>
                    <Activity size={18} />
                    <span style={{ fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Head-to-Head Facts (Since 2024)
                    </span>
                  </div>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {prediction.h2h_insights.map((fact, idx) => (
                      <li key={idx} style={{ 
                        fontSize: '14px', 
                        color: 'var(--text-main)',
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
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Estimates derived via Poisson MLE with a fitted Dixon-Coles low-score correction.
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
              {loadingStrengths && strengths.length === 0 ? (
                <tr><td colSpan="4"><div className="table-state"><RefreshCw className="spin" size={22} />Loading team ratings…</div></td></tr>
              ) : requestErrors.strengths && strengths.length === 0 ? (
                <tr><td colSpan="4"><div className="table-state error-text">Team ratings are unavailable. Use “Try Again” above.</div></td></tr>
              ) : strengths.map(s => (
                <tr key={s.Team}>
                  <td style={{ fontWeight: '700' }}><div className="team-cell"><ClubBadge team={s.Team} />{s.Team}</div></td>
                  <td style={{ color: s.Attack_Strength > 0 ? 'var(--primary)' : '#e63946', fontWeight: '700' }}>
                    {s.Attack_Strength > 0 ? `+${s.Attack_Strength}` : s.Attack_Strength}
                  </td>
                  <td style={{ color: s.Defense_Weakness < 0.5 ? 'var(--cyan)' : 'var(--gold)' }}>
                    {s.Defense_Weakness}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                    {s.Attack_Strength > 0.05 ? 'Strong attack' : s.Attack_Strength > -0.1 ? 'Solid attack' : 'Low scoring'}
                    {' • '}
                    {s.Defense_Weakness < 0.4 ? 'Strong defence' : s.Defense_Weakness > 0.7 ? 'Vulnerable defence' : 'Average defence'}
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
            <div className="table-title">
              Actual Premier League 2026/27 Results
              {seasonStatus ? ` (${seasonStatus.completed_matches} Matches Played)` : ''}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {seasonStatus?.latest_result_date
                ? `Results through ${new Date(`${seasonStatus.latest_result_date}T00:00:00`).toLocaleDateString()}.`
                : 'Official results so far from football-data.co.uk before simulation.'}
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
              {loadingTable && currentTable.length === 0 ? (
                <tr><td colSpan="10"><div className="table-state"><RefreshCw className="spin" size={22} />Loading current standings…</div></td></tr>
              ) : requestErrors.standings && currentTable.length === 0 ? (
                <tr><td colSpan="10"><div className="table-state error-text">Current standings are unavailable. Use “Try Again” above.</div></td></tr>
              ) : currentTable.map((r, i) => (
                <tr key={r.Team}>
                  <td><span className="rank-badge">{i + 1}</span></td>
                  <td style={{ fontWeight: '700' }}><div className="team-cell"><ClubBadge team={r.Team} />{r.Team}</div></td>
                  <td>{r.Played}</td>
                  <td>{r.Wins}</td>
                  <td>{r.Draws}</td>
                  <td>{r.Losses}</td>
                  <td>{r.GF}</td>
                  <td>{r.GA}</td>
                  <td>{r.GD > 0 ? `+${r.GD}` : r.GD}</td>
                  <td style={{ fontWeight: '800', color: 'var(--primary)' }}>{r.Points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'evaluation' && loadingEvaluation && !evaluation && (
        <div className="section-state"><RefreshCw className="spin" size={22} />Running historical backtest…</div>
      )}

      {activeTab === 'evaluation' && requestErrors.evaluation && !loadingEvaluation && !evaluation && (
        <div className="section-state error-text">Model evaluation is unavailable. Use “Try Again” above.</div>
      )}

      {activeTab === 'evaluation' && evaluation && (
        <div className="evaluation-panel">
          <div className="table-header">
            <div>
              <div className="table-title">Historical Backtest</div>
              <div className="evaluation-description">
                The model trained on {evaluation.training_matches} earlier matches and was tested on {evaluation.test_matches} later matches it had never seen.
              </div>
            </div>
            <span className="tag-badge">{evaluation.method}</span>
          </div>

          <div className="evaluation-grid">
            <div className="metric-card">
              <span className="metric-label">Correct result</span>
              <strong className="metric-value">{evaluation.outcome_accuracy_pct}%</strong>
              <span className="metric-help">Correctly chose home win, draw, or away win.</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Exact score</span>
              <strong className="metric-value">{evaluation.exact_score_accuracy_pct}%</strong>
              <span className="metric-help">The most likely score exactly matched the result.</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Goal error</span>
              <strong className="metric-value">{evaluation.goal_mae}</strong>
              <span className="metric-help">Average goals missed per team; lower is better.</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Probability score</span>
              <strong className="metric-value">{evaluation.log_loss}</strong>
              <span className="metric-help">Log loss; lower means better probabilities.</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Simple baseline</span>
              <strong className="metric-value">{evaluation.baseline_log_loss}</strong>
              <span className="metric-help">Log loss from using only historical result frequencies.</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Improvement</span>
              <strong className={`metric-value ${evaluation.log_loss_improvement_pct >= 0 ? 'positive' : 'negative'}`}>
                {evaluation.log_loss_improvement_pct > 0 ? '+' : ''}{evaluation.log_loss_improvement_pct}%
              </strong>
              <span className="metric-help">Model improvement over the simple baseline.</span>
            </div>
          </div>

          <div className="evaluation-note">
            Training ended {evaluation.training_end_date}; testing began {evaluation.test_start_date}. This time-based split prevents future results from leaking into training.
          </div>
        </div>
      )}
    </div>
  )
}
