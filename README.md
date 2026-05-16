# ⚽ Footy TUI — Live Football Score Ticker

A snappy terminal football ticker with full match stats, goal feed, league tables and a clean TUI — powered by the **free** `football-data.org` API.

---

## Leagues Covered
| # | League | Country |
|---|--------|---------|
| 1 | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League | England |
| 2 | 🇪🇸 La Liga | Spain |
| 3 | 🇩🇪 Bundesliga | Germany |
| 4 | 🇮🇹 Serie A | Italy |
| 5 | 🇫🇷 Ligue 1 | France |
| 6 | ⭐ UEFA Champions League | Europe |

---

## Setup

### 1. Install dependencies
```bash
pip install rich requests
```

### 2. Get a FREE API key
Register at **https://www.football-data.org/client/register**  
- No credit card required
- Free forever for top competitions
- 10 requests/minute limit

### 3. Set your API key
```bash
export FOOTY_API_KEY=your_key_here
```

### 4. Run it
```bash
python3 footy.py           # uses env var
python3 footy.py --key YOUR_KEY
python3 footy.py --demo    # no API key, rich mock data
```

---

## Controls

| Key | Action |
|-----|--------|
| `↑` `↓` | Navigate matches |
| `Enter` | Open match detail (goals + full stats + lineups) |
| `1`–`6` | Filter by league |
| `0` | Show all leagues |
| `s` | View league standings |
| `r` | Force refresh |
| `b` / `Esc` | Go back |
| `q` | Quit |

---

## Features

- **Live scores** — updates every 30s automatically
- **Match detail** — goals with minute, scorer, assist, type (penalty/OG)
- **Full stats** — possession, shots, SoT, corners, fouls, cards, offsides, passes, pass accuracy, tackles, saves
- **Lineups** — starting XI for both teams (when available)
- **Standings** — full league table with W/D/L, GD, points, and 5-match form
- **Goal ticker** — scrolling live goal feed at the bottom
- **League filter** — one-key filter to any league
- **Status icons** — 🔴 live, ✅ FT, ⏸ HT, 🕐 scheduled, ⚠️ suspended

---

## Options

```
python3 footy.py --help

  --key KEY        API key (or use FOOTY_API_KEY env var)
  --demo           Run with mock data (no key needed)
  --refresh N      Auto-refresh interval in seconds (default: 30)
```

---

## Notes

- The free API tier gives **10 req/min** — the app batches calls efficiently to stay under this.
- Stats (possession, shots etc.) are available for most top-flight matches during and after games.
- Lineups are exposed in the demo; with the real API they appear ~1 hour before kickoff.
- If you're close to the rate limit, increase `--refresh 60` to reduce calls.
