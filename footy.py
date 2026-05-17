#!/usr/bin/env python3
"""
FOOTY - Live Football Score Ticker
Powered by Bzzoiro Sports Data (BSD) — free, no rate limits, no credit card.
Register at: https://sports.bzzoiro.com/register/

Usage:
    python3 footy.py --demo                  # mock data, no key needed
    python3 footy.py --key YOUR_KEY          # live data
    export BSD_API_KEY=xxx && python3 footy.py
"""

import curses
import os
import sys
import time
import threading
import requests
import argparse
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# League config  (BSD league IDs from sports.bzzoiro.com/leagues/)
# ---------------------------------------------------------------------------

LEAGUES = {
    1:  {"name": "Premier League",    "short": "PL",  "country": "ENG"},
    3:  {"name": "La Liga",           "short": "LL",  "country": "ESP"},
    5:  {"name": "Bundesliga",        "short": "BL",  "country": "GER"},
    4:  {"name": "Serie A",           "short": "SA",  "country": "ITA"},
    6:  {"name": "Ligue 1",           "short": "L1",  "country": "FRA"},
    7:  {"name": "Champions League",  "short": "UCL", "country": "EUR"},
}
LEAGUE_IDS   = list(LEAGUES.keys())
LEAGUE_SHORTS = {lid: info["short"] for lid, info in LEAGUES.items()}

STATUS_SHORT = {
    "notstarted": "SOON",
    "inprogress": "LIVE",
    "halftime":   "HT  ",
    "finished":   "FT  ",
    "postponed":  "POST",
    "cancelled":  "CANC",
    "suspended":  "SUSP",
    "penalties":  "PENS",
}
STATUS_ORDER = {
    "inprogress": 0, "halftime": 1, "penalties": 2,
    "finished": 3, "notstarted": 4,
    "postponed": 5, "cancelled": 6, "suspended": 7,
}

BASE = "https://sports.bzzoiro.com/api/v2"

# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

DEMO_EVENTS = [
    {"id": 101, "league_id": 1, "home_team": "Arsenal",       "away_team": "Man City",
     "home_score": 2, "away_score": 1, "home_score_ht": 1, "away_score_ht": 0,
     "status": "inprogress", "period": "2nd_half", "current_minute": 67,
     "event_date": "2026-05-17T14:00:00Z"},
    {"id": 102, "league_id": 3, "home_team": "Real Madrid",   "away_team": "Barcelona",
     "home_score": 3, "away_score": 2, "home_score_ht": 1, "away_score_ht": 1,
     "status": "finished",   "period": "FT",      "current_minute": 90,
     "event_date": "2026-05-17T10:00:00Z"},
    {"id": 103, "league_id": 5, "home_team": "Bayern Munich", "away_team": "B. Dortmund",
     "home_score": 1, "away_score": 0, "home_score_ht": 0, "away_score_ht": 0,
     "status": "inprogress", "period": "1st_half", "current_minute": 34,
     "event_date": "2026-05-17T14:30:00Z"},
    {"id": 104, "league_id": 4, "home_team": "Inter Milan",   "away_team": "AC Milan",
     "home_score": None,    "away_score": None,   "home_score_ht": None, "away_score_ht": None,
     "status": "notstarted", "period": None,       "current_minute": None,
     "event_date": "2026-05-17T19:45:00Z"},
    {"id": 105, "league_id": 6, "home_team": "PSG",           "away_team": "Marseille",
     "home_score": 1, "away_score": 1, "home_score_ht": 1, "away_score_ht": 1,
     "status": "halftime",   "period": "halftime", "current_minute": 45,
     "event_date": "2026-05-17T16:00:00Z"},
    {"id": 106, "league_id": 1, "home_team": "Chelsea",       "away_team": "Tottenham",
     "home_score": 0, "away_score": 0, "home_score_ht": 0, "away_score_ht": 0,
     "status": "inprogress", "period": "2nd_half", "current_minute": 78,
     "event_date": "2026-05-17T14:00:00Z"},
    {"id": 107, "league_id": 7, "home_team": "Atletico Madrid","away_team": "Liverpool",
     "home_score": 1, "away_score": 2, "home_score_ht": 0, "away_score_ht": 0,
     "status": "finished",   "period": "FT",       "current_minute": 90,
     "event_date": "2026-05-17T19:00:00Z"},
    {"id": 108, "league_id": 1, "home_team": "Man United",    "away_team": "Newcastle",
     "home_score": None,    "away_score": None,   "home_score_ht": None, "away_score_ht": None,
     "status": "notstarted", "period": None,        "current_minute": None,
     "event_date": "2026-05-17T17:30:00Z"},
]

DEMO_INCIDENTS = {
    101: [
        {"type": "goal",         "minute": 23, "player": "Saka",       "team": "home", "description": "Right foot shot", "assist": "Odegaard", "score_home": 1, "score_away": 0},
        {"type": "goal",         "minute": 41, "player": "Haaland",    "team": "away", "description": "Header",          "assist": None,       "score_home": 1, "score_away": 1},
        {"type": "card",         "minute": 44, "player": "Rodri",      "team": "away", "card_type": "yellow"},
        {"type": "goal",         "minute": 58, "player": "Odegaard",   "team": "home", "description": "Penalty",         "assist": None,       "score_home": 2, "score_away": 1},
        {"type": "substitution", "minute": 62, "player_out": "Trossard","player_in": "Nketiah", "team": "home"},
        {"type": "card",         "minute": 65, "player": "Akanji",     "team": "away", "card_type": "yellow"},
    ],
    102: [
        {"type": "goal",         "minute": 12, "player": "Vinicius Jr","team": "home", "description": "Left foot",  "assist": "Bellingham", "score_home": 1, "score_away": 0},
        {"type": "goal",         "minute": 29, "player": "Yamal",      "team": "away", "description": "Right foot", "assist": None,         "score_home": 1, "score_away": 1},
        {"type": "goal",         "minute": 44, "player": "Bellingham", "team": "home", "description": "Header",     "assist": "Modric",     "score_home": 2, "score_away": 1},
        {"type": "card",         "minute": 55, "player": "Gavi",       "team": "away", "card_type": "yellow"},
        {"type": "goal",         "minute": 71, "player": "Raphinha",   "team": "away", "description": "Free kick",  "assist": None,         "score_home": 2, "score_away": 2},
        {"type": "substitution", "minute": 75, "player_out": "Modric", "player_in": "Camavinga", "team": "home"},
        {"type": "goal",         "minute": 88, "player": "Mbappe",     "team": "home", "description": "Right foot", "assist": "Vinicius Jr","score_home": 3, "score_away": 2},
        {"type": "card",         "minute": 90, "player": "Araujo",     "team": "away", "card_type": "red"},
    ],
}

DEMO_STATS = {
    101: {"stats": {
        "home": {"ball_possession": 48, "total_shots": 9,  "shots_on_goal": 5,
                 "corner_kicks": 4, "fouls": 11, "yellow_cards": 1, "red_cards": 0,
                 "offsides": 2, "pass_accuracy_pct": 81, "dangerous_attack": 44, "attack": 89},
        "away": {"ball_possession": 52, "total_shots": 14, "shots_on_goal": 6,
                 "corner_kicks": 7, "fouls": 9,  "yellow_cards": 2, "red_cards": 0,
                 "offsides": 3, "pass_accuracy_pct": 88, "dangerous_attack": 59, "attack": 101},
    }},
}

DEMO_LINEUPS = {
    101: {
        "home": [
            {"name": "Raya",       "position": "G", "shirt_number": 22, "is_starter": True},
            {"name": "White",      "position": "D", "shirt_number": 2,  "is_starter": True},
            {"name": "Saliba",     "position": "D", "shirt_number": 12, "is_starter": True},
            {"name": "Gabriel",    "position": "D", "shirt_number": 6,  "is_starter": True},
            {"name": "Timber",     "position": "D", "shirt_number": 17, "is_starter": True},
            {"name": "Rice",       "position": "M", "shirt_number": 41, "is_starter": True},
            {"name": "Partey",     "position": "M", "shirt_number": 5,  "is_starter": True},
            {"name": "Odegaard",   "position": "M", "shirt_number": 8,  "is_starter": True},
            {"name": "Saka",       "position": "F", "shirt_number": 7,  "is_starter": True},
            {"name": "Trossard",   "position": "F", "shirt_number": 19, "is_starter": True},
            {"name": "Havertz",    "position": "F", "shirt_number": 29, "is_starter": True},
        ],
        "away": [
            {"name": "Ederson",    "position": "G", "shirt_number": 31, "is_starter": True},
            {"name": "Walker",     "position": "D", "shirt_number": 2,  "is_starter": True},
            {"name": "Dias",       "position": "D", "shirt_number": 3,  "is_starter": True},
            {"name": "Akanji",     "position": "D", "shirt_number": 25, "is_starter": True},
            {"name": "Gvardiol",   "position": "D", "shirt_number": 24, "is_starter": True},
            {"name": "Rodri",      "position": "M", "shirt_number": 16, "is_starter": True},
            {"name": "De Bruyne",  "position": "M", "shirt_number": 17, "is_starter": True},
            {"name": "Bernardo",   "position": "M", "shirt_number": 20, "is_starter": True},
            {"name": "Doku",       "position": "F", "shirt_number": 11, "is_starter": True},
            {"name": "Foden",      "position": "F", "shirt_number": 47, "is_starter": True},
            {"name": "Haaland",    "position": "F", "shirt_number": 9,  "is_starter": True},
        ],
    },
}

# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class FootballAPI:
    def __init__(self, api_key, demo=False):
        self.api_key   = api_key
        self.demo      = demo
        self.last_error = ""
        self.session   = requests.Session()
        self.session.headers["Authorization"] = f"Token {api_key}"
        self._cache    = {}
        self._cache_ts = {}
        self._lock     = threading.Lock()

    def _get(self, path, ttl=60):
        now = time.time()
        with self._lock:
            if path in self._cache and now - self._cache_ts.get(path, 0) < ttl:
                return self._cache[path]
        try:
            r = self.session.get(f"{BASE}{path}", timeout=10)
            if r.status_code == 401:
                self.last_error = "Invalid API key (401) — check your BSD key"
                return None
            if r.status_code == 429:
                self.last_error = "Rate limited (429) — press r to retry"
                return None
            if not r.ok:
                self.last_error = f"HTTP {r.status_code}: {r.text[:80]}"
                return None
            data = r.json()
            with self._lock:
                self._cache[path] = data
                self._cache_ts[path] = now
            return data
        except requests.exceptions.ConnectionError:
            self.last_error = "No internet connection"
            return None
        except requests.exceptions.Timeout:
            self.last_error = "Request timed out"
            return None
        except Exception as e:
            self.last_error = str(e)
            return None

    def _today_range(self):
        local_today = datetime.now().date()
        d_from = (local_today - timedelta(days=1)).isoformat()
        d_to   = (local_today + timedelta(days=1)).isoformat()
        return d_from, d_to, local_today

    def get_matches(self):
        if self.demo:
            return list(DEMO_EVENTS)
        self.last_error = ""
        d_from, d_to, local_today = self._today_range()

        all_matches = []
        for lid in LEAGUE_IDS:
            data = self._get(
                f"/events/?league_id={lid}&date_from={d_from}&date_to={d_to}&limit=200",
                ttl=30
            )
            if data and "results" in data:
                for m in data["results"]:
                    m["league_id"] = lid
                all_matches.extend(data["results"])

        # filter to local today
        def is_today(m):
            try:
                dt = datetime.fromisoformat(m["event_date"].replace("Z", "+00:00"))
                return dt.astimezone().date() == local_today
            except Exception:
                return True
        return [m for m in all_matches if is_today(m)]

    def get_incidents(self, event_id):
        if self.demo:
            return DEMO_INCIDENTS.get(event_id, [])
        data = self._get(f"/events/{event_id}/incidents/", ttl=20)
        if not data:
            return []
        return data.get("incidents", [])

    def get_stats(self, event_id):
        if self.demo:
            return DEMO_STATS.get(event_id, {}).get("stats", {})
        data = self._get(f"/events/{event_id}/stats/", ttl=20)
        if not data:
            return {}
        return data.get("stats", {})

    def get_lineups(self, event_id):
        if self.demo:
            return DEMO_LINEUPS.get(event_id, {})
        data = self._get(f"/events/{event_id}/lineups/", ttl=60)
        if not data:
            return {}
        # BSD returns {"home": [...], "away": [...]} each a list of player dicts
        return data

    def get_standings(self, league_id):
        if self.demo:
            return None
        # need current season_id — fetch league detail first
        league = self._get(f"/leagues/{league_id}/season/", ttl=3600)
        if not league:
            return None
        season_id = league.get("id") or league.get("season_id")
        if not season_id:
            return None
        return self._get(f"/leagues/{league_id}/standings/?season_id={season_id}", ttl=300)

# ---------------------------------------------------------------------------
# Curses helpers
# ---------------------------------------------------------------------------

COL_DEFAULT  = 0
COL_HEADER   = 1
COL_LIVE     = 2
COL_DIM      = 3
COL_SELECTED = 4
COL_WIN      = 5
COL_WARN     = 6
COL_TITLE    = 7

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COL_HEADER,   curses.COLOR_BLACK,  curses.COLOR_WHITE)
    curses.init_pair(COL_LIVE,     curses.COLOR_GREEN,  -1)
    curses.init_pair(COL_DIM,      curses.COLOR_WHITE,  -1)
    curses.init_pair(COL_SELECTED, curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(COL_WIN,      curses.COLOR_GREEN,  -1)
    curses.init_pair(COL_WARN,     curses.COLOR_YELLOW, -1)
    curses.init_pair(COL_TITLE,    curses.COLOR_CYAN,   -1)

def ss(win, y, x, text, attr=0):
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w - 1:
        return
    try:
        win.addstr(y, x, text[:w - x - 1], attr)
    except curses.error:
        pass

def hl(win, y, x, n):
    h, w = win.getmaxyx()
    if y < 0 or y >= h:
        return
    n = min(n, w - x - 1)
    if n > 0:
        try:
            win.hline(y, x, ord("-"), n)
        except curses.error:
            pass

def fmt_ko(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%H:%M")
    except Exception:
        return "  -  "

def fmt_score(m):
    h, a = m.get("home_score"), m.get("away_score")
    if h is None or a is None:
        return " - "
    return f"{h}-{a}"

def sort_matches(matches, league_filter=None):
    out = [m for m in matches if league_filter is None or m.get("league_id") == league_filter]
    return sorted(out, key=lambda m: (
        STATUS_ORDER.get(m.get("status", ""), 9),
        m.get("event_date", "")
    ))

# ---------------------------------------------------------------------------
# Draw: top bar
# ---------------------------------------------------------------------------

def draw_topbar(win, matches, next_refresh, filter_lid):
    h, w = win.getmaxyx()
    win.bkgd(ord(" "), curses.color_pair(COL_HEADER) | curses.A_BOLD)
    win.erase()
    now_str = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    live_n  = sum(1 for m in matches if m.get("status") in ("inprogress", "halftime", "penalties"))
    title   = "FOOTY - Live Football"
    right   = f"LIVE:{live_n}  refresh:{next_refresh}s"
    if filter_lid:
        right = f"[{LEAGUES[filter_lid]['short']}]  " + right
    ss(win, 0, 1, title, curses.color_pair(COL_HEADER) | curses.A_BOLD)
    ss(win, 0, w // 2 - len(now_str) // 2, now_str, curses.color_pair(COL_HEADER))
    ss(win, 0, max(1, w - len(right) - 2), right, curses.color_pair(COL_HEADER))

# ---------------------------------------------------------------------------
# Draw: league tab bar
# ---------------------------------------------------------------------------

def draw_leaguebar(win, filter_lid):
    win.erase()
    h, w = win.getmaxyx()
    x = 1
    items = [("0", "ALL", None)] + [(str(i+1), LEAGUES[lid]["short"], lid) for i, lid in enumerate(LEAGUE_IDS)]
    for key, label, lid in items:
        tag  = f"[{key}]{label}"
        sel  = (filter_lid == lid) or (filter_lid is None and lid is None)
        attr = curses.A_BOLD | curses.color_pair(COL_TITLE) if sel else curses.color_pair(COL_DIM) | curses.A_DIM
        if x + len(tag) + 2 >= w:
            break
        ss(win, 0, x, tag, attr)
        x += len(tag) + 3

# ---------------------------------------------------------------------------
# Draw: controls bar
# ---------------------------------------------------------------------------

def draw_controls(win, view):
    h, w = win.getmaxyx()
    win.erase()
    hl(win, 0, 0, w - 1)
    if view == "main":
        ctrl = "UP/DOWN:navigate  ENTER:detail  0-6:filter  s:standings  r:refresh  q:quit"
    elif view == "detail":
        ctrl = "b/ESC:back  r:refresh  q:quit"
    else:
        ctrl = "b/ESC:back  q:quit"
    ss(win, 1, 1, ctrl, curses.color_pair(COL_DIM))

# ---------------------------------------------------------------------------
# Draw: goals ticker strip
# ---------------------------------------------------------------------------

def draw_ticker(win, matches, incidents_cache):
    win.erase()
    h, w = win.getmaxyx()
    goals = []
    for m in matches:
        if m.get("status") in ("notstarted",):
            continue
        home = m.get("home_team", "?")
        away = m.get("away_team", "?")
        for inc in incidents_cache.get(m["id"], []):
            if inc.get("type") == "goal":
                player = inc.get("player", "?")
                minute = inc.get("minute", "?")
                team   = home if inc.get("team") == "home" else away
                goals.append(f"{minute}' {player} ({team})")
    text = "GOALS: " + ("  |  ".join(goals) if goals else "none yet")
    ss(win, 0, 0, text, curses.color_pair(COL_DIM))

# ---------------------------------------------------------------------------
# Draw: match list
# ---------------------------------------------------------------------------

def draw_matches(win, matches, selected_idx, filter_lid, last_error=""):
    win.erase()
    h, w = win.getmaxyx()
    ms = sort_matches(matches, filter_lid)

    C_SEL = 1; C_LEA = 4; C_STAT = 4; C_MIN = 4; C_SCORE = 5; C_KO = 5
    GAPS  = 7 * 2
    C_TEAM = max(8, (w - C_SEL - C_LEA - C_STAT - C_MIN - C_SCORE - C_KO - GAPS) // 2)

    hdr = (f"{'':>{C_SEL}} {'LEA':<{C_LEA}} {'HOME':<{C_TEAM}} {'SCR':^{C_SCORE}} "
           f"{'AWAY':<{C_TEAM}} {'ST':^{C_STAT}} {'MIN':^{C_MIN}} {'KO':^{C_KO}}")
    ss(win, 0, 0, hdr, curses.color_pair(COL_HEADER) | curses.A_BOLD)
    hl(win, 1, 0, w - 1)

    for i, m in enumerate(ms):
        row = i + 2
        if row >= h:
            break
        status  = m.get("status", "")
        lid     = m.get("league_id")
        lea     = LEAGUES.get(lid, {}).get("short", "?")
        home    = m.get("home_team", "?")[:C_TEAM]
        away    = m.get("away_team", "?")[:C_TEAM]
        score   = fmt_score(m)
        st      = STATUS_SHORT.get(status, status[:4]).strip()
        minute  = str(m.get("current_minute", "")) if m.get("current_minute") else ""
        ko      = fmt_ko(m.get("event_date", ""))
        sel     = ">" if i == selected_idx else " "
        is_live = status in ("inprogress", "halftime", "penalties")
        is_sel  = (i == selected_idx)

        if is_sel:
            attr = curses.color_pair(COL_SELECTED) | curses.A_BOLD
        elif is_live:
            attr = curses.color_pair(COL_LIVE) | curses.A_BOLD
        elif status == "finished":
            attr = curses.color_pair(COL_DEFAULT)
        else:
            attr = curses.color_pair(COL_DIM) | curses.A_DIM

        line = (f"{sel:>{C_SEL}} {lea:<{C_LEA}} {home:<{C_TEAM}} {score:^{C_SCORE}} "
                f"{away:<{C_TEAM}} {st:^{C_STAT}} {minute:^{C_MIN}} {ko:^{C_KO}}")
        ss(win, row, 0, line, attr)

    if not ms:
        ss(win, 3, 2, "No matches found for today.", curses.color_pair(COL_DIM))
        if last_error:
            ss(win, 4, 2, f"Error: {last_error}", curses.color_pair(COL_WARN) | curses.A_BOLD)
            ss(win, 5, 2, "Press r to retry.", curses.color_pair(COL_DIM))

# ---------------------------------------------------------------------------
# Draw: match detail
# ---------------------------------------------------------------------------

def draw_detail(win, match, incidents, stats, lineups):
    win.erase()
    h, w = win.getmaxyx()

    if not match:
        ss(win, 1, 1, "Could not load match.", curses.A_BOLD)
        return

    home    = match.get("home_team", "?")
    away    = match.get("away_team", "?")
    status  = match.get("status", "")
    lid     = match.get("league_id")
    comp    = LEAGUES.get(lid, {}).get("name", "?")
    h_sc    = match.get("home_score", "-")
    a_sc    = match.get("away_score", "-")
    ht_h    = match.get("home_score_ht")
    ht_a    = match.get("away_score_ht")
    st      = STATUS_SHORT.get(status, status).strip()
    minute  = match.get("current_minute")
    period  = match.get("period", "")

    row = 0

    banner = f"{home}  {h_sc} - {a_sc}  {away}"
    ss(win, row, max(0, w // 2 - len(banner) // 2), banner,
       curses.A_BOLD | curses.color_pair(COL_TITLE)); row += 1

    sub = f"{comp}   {st}"
    if minute:
        sub += f"  {minute}'"
    if ht_h is not None:
        sub += f"   HT:{ht_h}-{ht_a}"
    ss(win, row, max(0, w // 2 - len(sub) // 2), sub, curses.color_pair(COL_DIM)); row += 1
    hl(win, row, 0, w - 1); row += 1

    # ── INCIDENTS (goals / cards / subs) ────────────────────────────────────
    goals = [i for i in incidents if i.get("type") == "goal"]
    cards = [i for i in incidents if i.get("type") == "card"]
    subs  = [i for i in incidents if i.get("type") == "substitution"]

    # Goals
    ss(win, row, 1, "GOALS", curses.A_BOLD); row += 1
    if not goals:
        ss(win, row, 3, "none yet" if status != "notstarted" else "not started",
           curses.color_pair(COL_DIM)); row += 1
    else:
        for g in sorted(goals, key=lambda x: x.get("minute", 0)):
            if row >= h - 2: break
            mn     = g.get("minute", "?")
            player = g.get("player", "?")
            team   = home if g.get("team") == "home" else away
            desc   = g.get("description", "")
            assist = g.get("assist", "")
            sh     = g.get("score_home", ""), g.get("score_away", "")
            suffix = f" [{desc}]" if desc else ""
            astr   = f"  ast:{assist}" if assist else ""
            scstr  = f"  ({sh[0]}-{sh[1]})" if sh[0] != "" else ""
            line   = f"  {mn:>3}'  {player}{suffix}  ({team}){astr}{scstr}"
            attr   = curses.color_pair(COL_LIVE) if g.get("team") == "home" else curses.color_pair(COL_WARN)
            ss(win, row, 0, line, attr); row += 1

    hl(win, row, 0, w - 1); row += 1

    # Cards
    if cards and row < h - 3:
        ss(win, row, 1, "CARDS", curses.A_BOLD); row += 1
        for c in sorted(cards, key=lambda x: x.get("minute", 0)):
            if row >= h - 2: break
            mn     = c.get("minute", "?")
            player = c.get("player", "?")
            team   = home if c.get("team") == "home" else away
            ct     = c.get("card_type", "")
            badge  = "Y" if ct == "yellow" else "R" if ct == "red" else "Y/R"
            line   = f"  {mn:>3}'  [{badge}]  {player}  ({team})"
            attr   = curses.color_pair(COL_WARN) if ct == "yellow" else curses.color_pair(COL_LIVE) | curses.A_BOLD
            ss(win, row, 0, line, attr); row += 1
        hl(win, row, 0, w - 1); row += 1

    # Subs
    if subs and row < h - 3:
        ss(win, row, 1, "SUBSTITUTIONS", curses.A_BOLD); row += 1
        for s in sorted(subs, key=lambda x: x.get("minute", 0)):
            if row >= h - 2: break
            mn  = s.get("minute", "?")
            on  = s.get("player_in", "?")
            off = s.get("player_out", "?")
            team = home if s.get("team") == "home" else away
            line = f"  {mn:>3}'  {on} on / {off} off  ({team})"
            ss(win, row, 0, line, curses.color_pair(COL_DIM)); row += 1
        hl(win, row, 0, w - 1); row += 1

    # ── STATS ────────────────────────────────────────────────────────────────
    hs = stats.get("home", {})
    as_ = stats.get("away", {})
    stat_defs = [
        ("Possession %",     "ball_possession"),
        ("Shots",            "total_shots"),
        ("Shots on Target",  "shots_on_goal"),
        ("Corners",          "corner_kicks"),
        ("Fouls",            "fouls"),
        ("Yellow Cards",     "yellow_cards"),
        ("Red Cards",        "red_cards"),
        ("Offsides",         "offsides"),
        ("Pass Accuracy %",  "pass_accuracy_pct"),
        ("Attacks",          "attack"),
        ("Dangerous Attacks","dangerous_attack"),
        ("xG",               "xg"),
    ]
    available = [(lbl, key) for lbl, key in stat_defs if key in hs or key in as_]
    if available and row < h - 3:
        LW = 20
        ss(win, row, 1, "MATCH STATS", curses.A_BOLD); row += 1
        ss(win, row, 0, f"  {'Stat':<{LW}}  {home:<18}  {away:<18}", curses.A_BOLD); row += 1
        for lbl, key in available:
            if row >= h - 2: break
            hv = hs.get(key)
            av = as_.get(key)
            # xg may be a dict
            if isinstance(hv, dict): hv = hv.get("actual", hv.get("value"))
            if isinstance(av, dict): av = av.get("actual", av.get("value"))
            # ratio stat shape: {"value":x, "total":y, "pct":z}
            if isinstance(hv, dict): hv = hv.get("value")
            if isinstance(av, dict): av = av.get("value")
            hvs = f"{hv:.1f}" if isinstance(hv, float) else str(hv) if hv is not None else "-"
            avs = f"{av:.1f}" if isinstance(av, float) else str(av) if av is not None else "-"
            try:
                h_win = float(hv) > float(av)
                a_win = float(av) > float(hv)
            except Exception:
                h_win = a_win = False
            line = f"  {lbl:<{LW}}  {hvs:<18}  {avs:<18}"
            ss(win, row, 0, line, curses.color_pair(COL_DEFAULT))
            hx = 2 + LW + 2; ax = hx + 20
            if h_win: ss(win, row, hx, f"{hvs:<18}", curses.color_pair(COL_WIN) | curses.A_BOLD)
            if a_win: ss(win, row, ax, f"{avs:<18}", curses.color_pair(COL_WIN) | curses.A_BOLD)
            row += 1
        hl(win, row, 0, w - 1); row += 1
    elif row < h - 3:
        ss(win, row, 3, "Stats not available yet.", curses.color_pair(COL_DIM)); row += 1
        hl(win, row, 0, w - 1); row += 1

    # ── LINEUPS ──────────────────────────────────────────────────────────────
    home_lu = lineups.get("home", [])
    away_lu = lineups.get("away", [])
    starters_h = [p for p in home_lu if p.get("is_starter")]
    starters_a = [p for p in away_lu if p.get("is_starter")]
    if (starters_h or starters_a) and row < h - 3:
        ss(win, row, 1, "LINEUPS  (starters)", curses.A_BOLD); row += 1
        CW = max(18, w // 2 - 4)
        ss(win, row, 0, f"  {home:<{CW}}  {away:<{CW}}", curses.A_BOLD); row += 1
        for i in range(max(len(starters_h), len(starters_a))):
            if row >= h - 1: break
            def fmt_p(p):
                if not p: return ""
                num = p.get("shirt_number", "")
                pos = p.get("position", "")
                nm  = p.get("name", "?")
                return f"{num:>2} {pos:<1} {nm}"
            hp = fmt_p(starters_h[i] if i < len(starters_h) else None)
            ap = fmt_p(starters_a[i] if i < len(starters_a) else None)
            ss(win, row, 0, f"  {hp:<{CW}}  {ap:<{CW}}", curses.color_pair(COL_DEFAULT))
            row += 1

# ---------------------------------------------------------------------------
# Draw: standings
# ---------------------------------------------------------------------------

def draw_standings(win, data, league_id):
    win.erase()
    h, w = win.getmaxyx()
    info  = LEAGUES.get(league_id, {})
    title = f"STANDINGS: {info.get('name', str(league_id))}"
    ss(win, 0, w // 2 - len(title) // 2, title, curses.A_BOLD | curses.color_pair(COL_TITLE))
    hl(win, 1, 0, w - 1)

    if not data:
        ss(win, 3, 2, "Standings not available (demo mode, or fetch a key first).", curses.color_pair(COL_DIM))
        return

    # BSD standings structure: {"standings": [{"position":1,"team_name":"...","points":...}]}
    table = []
    if isinstance(data, dict):
        table = data.get("standings", data.get("table", data.get("results", [])))
    elif isinstance(data, list):
        table = data

    if not table:
        ss(win, 3, 2, "No standings data.", curses.color_pair(COL_DIM)); return

    hdr = f"{'#':>3}  {'Team':<24}  {'MP':>3}  {'W':>3}  {'D':>3}  {'L':>3}  {'GF':>4}  {'GA':>4}  {'GD':>4}  {'Pts':>4}"
    ss(win, 2, 0, hdr, curses.A_BOLD)
    hl(win, 3, 0, w - 1)

    total = len(table)
    for idx, entry in enumerate(table):
        row = 4 + idx
        if row >= h - 1: break
        pos  = entry.get("position", idx + 1)
        team = (entry.get("team_name") or entry.get("team", {}).get("name", "?"))[:24]
        mp   = entry.get("played",        entry.get("games_played",   0))
        w_   = entry.get("won",           entry.get("wins",            0))
        d    = entry.get("drawn",         entry.get("draws",           0))
        l_   = entry.get("lost",          entry.get("losses",          0))
        gf   = entry.get("goals_scored",  entry.get("goals_for",       0))
        ga   = entry.get("goals_against", 0)
        gd   = entry.get("goal_diff",     entry.get("goal_difference", gf - ga))
        pts  = entry.get("points", 0)
        gds  = f"+{gd}" if gd > 0 else str(gd)
        line = f"{pos:>3}  {team:<24}  {mp:>3}  {w_:>3}  {d:>3}  {l_:>3}  {gf:>4}  {ga:>4}  {gds:>4}  {pts:>4}"
        if pos <= 4:   attr = curses.color_pair(COL_WIN) | curses.A_BOLD
        elif pos >= total - 2: attr = curses.color_pair(COL_WARN)
        else:          attr = curses.color_pair(COL_DEFAULT)
        ss(win, row, 0, line, attr)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main(stdscr, api, refresh_interval):
    curses.curs_set(0)
    stdscr.timeout(200)
    init_colors()

    matches         = []
    view            = "main"
    selected_idx    = 0
    filter_lid      = None
    detail_match    = None
    detail_incidents= []
    detail_stats    = {}
    detail_lineups  = {}
    standings_data  = None
    standings_lid   = None
    last_refresh    = 0.0
    incidents_cache = {}   # id -> list, for ticker

    def do_refresh():
        nonlocal matches, last_refresh
        matches = api.get_matches()
        last_refresh = time.time()
        # prime incidents cache for any live match (for ticker)
        for m in matches:
            if m.get("status") in ("inprogress", "halftime", "penalties", "finished"):
                mid = m["id"]
                if mid not in incidents_cache:
                    inc = api.get_incidents(mid)
                    if inc:
                        incidents_cache[mid] = inc

    def load_detail(match_id):
        nonlocal detail_match, detail_incidents, detail_stats, detail_lineups
        detail_match     = next((m for m in matches if m["id"] == match_id), None)
        detail_incidents = api.get_incidents(match_id)
        incidents_cache[match_id] = detail_incidents
        detail_stats     = api.get_stats(match_id)
        detail_lineups   = api.get_lineups(match_id)

    do_refresh()

    while True:
        h, w = stdscr.getmaxyx()
        now  = time.time()
        nr   = max(0, int(refresh_interval - (now - last_refresh)))

        TB = 1; LB = 1; TK = 1; CT = 2
        BH = max(4, h - TB - LB - TK - CT)

        top_w  = curses.newwin(TB, w, 0,          0)
        lea_w  = curses.newwin(LB, w, TB,         0)
        bod_w  = curses.newwin(BH, w, TB + LB,    0)
        tic_w  = curses.newwin(TK, w, TB+LB+BH,   0)
        ctl_w  = curses.newwin(CT, w, TB+LB+BH+TK,0)

        draw_topbar(top_w,  matches, nr, filter_lid)
        draw_leaguebar(lea_w, filter_lid)
        draw_controls(ctl_w, view)
        draw_ticker(tic_w, matches, incidents_cache)

        if view == "main":
            draw_matches(bod_w, matches, selected_idx, filter_lid,
                         getattr(api, "last_error", ""))
        elif view == "detail":
            draw_detail(bod_w, detail_match, detail_incidents,
                        detail_stats, detail_lineups)
        elif view == "standings":
            draw_standings(bod_w, standings_data, standings_lid or LEAGUE_IDS[0])

        top_w.noutrefresh(); lea_w.noutrefresh(); bod_w.noutrefresh()
        tic_w.noutrefresh(); ctl_w.noutrefresh()
        curses.doupdate()

        if now - last_refresh >= refresh_interval:
            do_refresh()

        key = stdscr.getch()
        if key == -1:
            continue

        fm = sort_matches(matches, filter_lid)

        if key in (ord("q"), ord("Q")):
            break
        elif key in (ord("r"), ord("R")):
            do_refresh()
            if view == "detail" and detail_match:
                load_detail(detail_match["id"])
        elif key in (ord("b"), 27):
            if view != "main":
                view = "main"
        elif view == "main":
            if key == curses.KEY_UP:
                if fm: selected_idx = (selected_idx - 1) % len(fm)
            elif key == curses.KEY_DOWN:
                if fm: selected_idx = (selected_idx + 1) % len(fm)
            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                if fm and selected_idx < len(fm):
                    load_detail(fm[selected_idx]["id"])
                    view = "detail"
            elif key == ord("0"):
                filter_lid = None; selected_idx = 0
            elif key in (ord("s"), ord("S")):
                standings_lid  = filter_lid or LEAGUE_IDS[0]
                standings_data = api.get_standings(standings_lid)
                view = "standings"
            else:
                for i, lid in enumerate(LEAGUE_IDS, 1):
                    if key == ord(str(i)):
                        filter_lid = lid; selected_idx = 0; break

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    parser = argparse.ArgumentParser(description="FOOTY - Live Football Score Ticker (BSD API)")
    parser.add_argument("--key", "-k",  help="BSD API key (or set BSD_API_KEY env var)")
    parser.add_argument("--demo", "-d", action="store_true", help="Run with demo data")
    parser.add_argument("--refresh",    type=int, default=30, help="Refresh interval in seconds (default 30)")
    args = parser.parse_args()

    demo    = args.demo
    api_key = args.key or os.environ.get("BSD_API_KEY", "")

    if not demo and not api_key:
        print("No API key found.\n")
        print("Get a FREE key (no credit card, no rate limits) at:")
        print("  https://sports.bzzoiro.com/register/\n")
        print("Then run:")
        print("  export BSD_API_KEY=your_key")
        print("  python3 footy.py\n")
        print("  or: python3 footy.py --key YOUR_KEY\n")
        print("Or try demo mode:")
        print("  python3 footy.py --demo")
        sys.exit(1)

    api = FootballAPI(api_key=api_key or "demo", demo=demo)

    try:
        curses.wrapper(main, api, args.refresh)
    except KeyboardInterrupt:
        pass
    print("Goodbye.")

if __name__ == "__main__":
    run()
