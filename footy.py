#!/usr/bin/env python3
"""
FOOTY - Live Football Score Ticker
Uses football-data.org free API (register at football-data.org/client/register)

Usage:
    python3 footy.py --demo               # no API key, runs with mock data
    python3 footy.py --key YOUR_KEY       # live data
    export FOOTY_API_KEY=xxx && python3 footy.py
"""

import curses
import os
import sys
import time
import threading
import requests
import argparse
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LEAGUES = {
    "PL":  {"id": 2021, "name": "Premier League",   "country": "ENG"},
    "PD":  {"id": 2014, "name": "La Liga",           "country": "ESP"},
    "BL1": {"id": 2002, "name": "Bundesliga",        "country": "GER"},
    "SA":  {"id": 2019, "name": "Serie A",           "country": "ITA"},
    "FL1": {"id": 2015, "name": "Ligue 1",           "country": "FRA"},
    "CL":  {"id": 2001, "name": "Champions League",  "country": "EUR"},
}

LEAGUE_KEYS = list(LEAGUES.keys())

STATUS_SHORT = {
    "SCHEDULED": "SOON",
    "TIMED":     "SOON",
    "IN_PLAY":   "LIVE",
    "PAUSED":    "LIVE",
    "HALF_TIME": "HT  ",
    "FINISHED":  "FT  ",
    "SUSPENDED": "SUSP",
    "POSTPONED": "POST",
    "CANCELLED": "CANC",
    "AWARDED":   "AWD ",
}

STATUS_ORDER = {
    "IN_PLAY": 0, "PAUSED": 0, "HALF_TIME": 1,
    "FINISHED": 2, "SCHEDULED": 3, "TIMED": 3,
    "SUSPENDED": 4, "POSTPONED": 5, "CANCELLED": 6,
}

# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

DEMO_MATCHES = [
    {"id": 101, "status": "IN_PLAY",   "minute": 67, "competition": {"code": "PL"},
     "homeTeam": {"name": "Arsenal",       "shortName": "ARS"},
     "awayTeam": {"name": "Man City",      "shortName": "MCI"},
     "score": {"fullTime": {"home": 2, "away": 1}, "halfTime": {"home": 1, "away": 0}},
     "utcDate": "2026-05-17T14:00:00Z",
     "goals": [
         {"minute": 23, "team": {"name": "Arsenal"},  "scorer": {"name": "Saka"},     "type": "REGULAR", "assist": None},
         {"minute": 41, "team": {"name": "Man City"},  "scorer": {"name": "Haaland"}, "type": "REGULAR", "assist": None},
         {"minute": 58, "team": {"name": "Arsenal"},  "scorer": {"name": "Odegaard"}, "type": "PENALTY", "assist": None},
     ]},
    {"id": 102, "status": "FINISHED",  "minute": 90, "competition": {"code": "PD"},
     "homeTeam": {"name": "Real Madrid", "shortName": "RMA"},
     "awayTeam": {"name": "Barcelona",   "shortName": "BAR"},
     "score": {"fullTime": {"home": 3, "away": 2}, "halfTime": {"home": 1, "away": 1}},
     "utcDate": "2026-05-17T10:00:00Z",
     "goals": [
         {"minute": 12, "team": {"name": "Real Madrid"}, "scorer": {"name": "Vinicius Jr"}, "type": "REGULAR", "assist": None},
         {"minute": 29, "team": {"name": "Barcelona"},   "scorer": {"name": "Yamal"},        "type": "REGULAR", "assist": None},
         {"minute": 44, "team": {"name": "Real Madrid"}, "scorer": {"name": "Bellingham"},   "type": "REGULAR", "assist": None},
         {"minute": 71, "team": {"name": "Barcelona"},   "scorer": {"name": "Raphinha"},     "type": "REGULAR", "assist": None},
         {"minute": 88, "team": {"name": "Real Madrid"}, "scorer": {"name": "Mbappe"},       "type": "REGULAR", "assist": None},
     ]},
    {"id": 103, "status": "IN_PLAY",   "minute": 34, "competition": {"code": "BL1"},
     "homeTeam": {"name": "Bayern Munich", "shortName": "FCB"},
     "awayTeam": {"name": "B. Dortmund",   "shortName": "BVB"},
     "score": {"fullTime": {"home": 1, "away": 0}, "halfTime": {"home": 0, "away": 0}},
     "utcDate": "2026-05-17T14:30:00Z",
     "goals": [
         {"minute": 19, "team": {"name": "Bayern Munich"}, "scorer": {"name": "Kane"}, "type": "REGULAR", "assist": None},
     ]},
    {"id": 104, "status": "SCHEDULED", "minute": None, "competition": {"code": "SA"},
     "homeTeam": {"name": "Inter Milan", "shortName": "INT"},
     "awayTeam": {"name": "AC Milan",    "shortName": "MIL"},
     "score": {"fullTime": {"home": None, "away": None}, "halfTime": {"home": None, "away": None}},
     "utcDate": "2026-05-17T19:45:00Z",
     "goals": []},
    {"id": 105, "status": "HALF_TIME", "minute": 45, "competition": {"code": "FL1"},
     "homeTeam": {"name": "PSG",       "shortName": "PSG"},
     "awayTeam": {"name": "Marseille", "shortName": "OM"},
     "score": {"fullTime": {"home": 1, "away": 1}, "halfTime": {"home": 1, "away": 1}},
     "utcDate": "2026-05-17T16:00:00Z",
     "goals": [
         {"minute": 33, "team": {"name": "PSG"},       "scorer": {"name": "Dembele"},    "type": "REGULAR", "assist": None},
         {"minute": 42, "team": {"name": "Marseille"}, "scorer": {"name": "Aubameyang"}, "type": "REGULAR", "assist": None},
     ]},
    {"id": 106, "status": "IN_PLAY",   "minute": 78, "competition": {"code": "PL"},
     "homeTeam": {"name": "Chelsea",   "shortName": "CHE"},
     "awayTeam": {"name": "Tottenham", "shortName": "TOT"},
     "score": {"fullTime": {"home": 0, "away": 0}, "halfTime": {"home": 0, "away": 0}},
     "utcDate": "2026-05-17T14:00:00Z",
     "goals": []},
    {"id": 107, "status": "FINISHED",  "minute": 90, "competition": {"code": "CL"},
     "homeTeam": {"name": "Atletico Madrid", "shortName": "ATM"},
     "awayTeam": {"name": "Liverpool",       "shortName": "LIV"},
     "score": {"fullTime": {"home": 1, "away": 2}, "halfTime": {"home": 0, "away": 0}},
     "utcDate": "2026-05-17T19:00:00Z",
     "goals": [
         {"minute": 55, "team": {"name": "Atletico Madrid"}, "scorer": {"name": "Griezmann"}, "type": "REGULAR", "assist": None},
         {"minute": 74, "team": {"name": "Liverpool"},       "scorer": {"name": "Salah"},      "type": "REGULAR", "assist": None},
         {"minute": 89, "team": {"name": "Liverpool"},       "scorer": {"name": "Diaz"},       "type": "REGULAR", "assist": None},
     ]},
    {"id": 108, "status": "TIMED",     "minute": None, "competition": {"code": "PL"},
     "homeTeam": {"name": "Man United", "shortName": "MNU"},
     "awayTeam": {"name": "Newcastle",  "shortName": "NEW"},
     "score": {"fullTime": {"home": None, "away": None}, "halfTime": {"home": None, "away": None}},
     "utcDate": "2026-05-17T17:30:00Z",
     "goals": []},
]

DEMO_STATS = {
    101: {
        "possession":    {"home": 48,  "away": 52},
        "shots":         {"home": 9,   "away": 14},
        "shotsOnTarget": {"home": 5,   "away": 6},
        "corners":       {"home": 4,   "away": 7},
        "fouls":         {"home": 11,  "away": 9},
        "yellowCards":   {"home": 1,   "away": 2},
        "redCards":      {"home": 0,   "away": 0},
        "offsides":      {"home": 2,   "away": 3},
        "passes":        {"home": 312, "away": 398},
        "passAccuracy":  {"home": 81,  "away": 88},
        "saves":         {"home": 5,   "away": 3},
        "lineup": {
            "home": ["Raya (GK)", "White", "Saliba", "Gabriel", "Timber",
                     "Rice", "Partey", "Odegaard", "Saka", "Trossard", "Havertz"],
            "away": ["Ederson (GK)", "Walker", "Dias", "Akanji", "Gvardiol",
                     "Rodri", "De Bruyne", "Bernardo", "Doku", "Foden", "Haaland"],
        },
    },
}

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

class FootballAPI:
    BASE = "https://api.football-data.org/v4"

    def __init__(self, api_key, demo=False):
        self.api_key = api_key
        self.demo    = demo
        self.session = requests.Session()
        self.session.headers["X-Auth-Token"] = api_key
        self._cache    = {}
        self._cache_ts = {}
        self._lock     = threading.Lock()

    def _get(self, path, ttl=60):
        now = time.time()
        with self._lock:
            if path in self._cache and now - self._cache_ts.get(path, 0) < ttl:
                return self._cache[path]
        try:
            r = self.session.get(f"{self.BASE}{path}", timeout=8)
            r.raise_for_status()
            data = r.json()
            with self._lock:
                self._cache[path] = data
                self._cache_ts[path] = now
            return data
        except Exception:
            return None

    def get_matches(self):
        if self.demo:
            return list(DEMO_MATCHES)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        all_matches = []
        for code, info in LEAGUES.items():
            data = self._get(f"/competitions/{info['id']}/matches?dateFrom={today}&dateTo={today}", ttl=30)
            if data and "matches" in data:
                for m in data["matches"]:
                    m["competition"] = {"code": code}
                all_matches.extend(data["matches"])
        return all_matches

    def get_match_detail(self, match_id):
        if self.demo:
            for m in DEMO_MATCHES:
                if m["id"] == match_id:
                    return m
            return None
        return self._get(f"/matches/{match_id}", ttl=20)

    def get_match_stats(self, match_id):
        if self.demo:
            return DEMO_STATS.get(match_id)
        return None

    def get_standings(self, league_code):
        if self.demo:
            return None
        lid = LEAGUES[league_code]["id"]
        return self._get(f"/competitions/{lid}/standings", ttl=300)

# ---------------------------------------------------------------------------
# Curses helpers
# ---------------------------------------------------------------------------

COL_DEFAULT  = 0
COL_HEADER   = 1
COL_LIVE     = 2
COL_DIM      = 3
COL_SELECTED = 4
COL_WIN      = 5
COL_SOON     = 6
COL_TITLE    = 7

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COL_HEADER,   curses.COLOR_BLACK,  curses.COLOR_WHITE)
    curses.init_pair(COL_LIVE,     curses.COLOR_GREEN,  -1)
    curses.init_pair(COL_DIM,      curses.COLOR_WHITE,  -1)
    curses.init_pair(COL_SELECTED, curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(COL_WIN,      curses.COLOR_GREEN,  -1)
    curses.init_pair(COL_SOON,     curses.COLOR_YELLOW, -1)
    curses.init_pair(COL_TITLE,    curses.COLOR_CYAN,   -1)

def safestr(win, y, x, text, attr=0):
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w - 1:
        return
    avail = w - x - 1
    try:
        win.addstr(y, x, text[:avail], attr)
    except curses.error:
        pass

def safehline(win, y, x, n):
    h, w = win.getmaxyx()
    if y < 0 or y >= h:
        return
    n = min(n, w - x - 1)
    if n > 0:
        try:
            win.hline(y, x, ord("-"), n)
        except curses.error:
            pass

def fmt_time(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%H:%M")
    except Exception:
        return "  -  "

def fmt_score(match):
    s  = match.get("score", {}).get("fullTime", {})
    hg = s.get("home")
    ag = s.get("away")
    if hg is None or ag is None:
        return " - "
    return f"{hg}-{ag}"

def get_sorted(matches, league_filter=None):
    out = matches
    if league_filter:
        out = [m for m in out if m.get("competition", {}).get("code") == league_filter]
    return sorted(out, key=lambda m: (
        STATUS_ORDER.get(m.get("status", ""), 9),
        m.get("utcDate", "")
    ))

# ---------------------------------------------------------------------------
# Draw functions — each takes its own window and draws fresh
# ---------------------------------------------------------------------------

def draw_topbar(win, matches, next_refresh, filter_league):
    h, w = win.getmaxyx()
    win.bkgd(ord(" "), curses.color_pair(COL_HEADER) | curses.A_BOLD)
    win.erase()
    now_str  = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    live_n   = sum(1 for m in matches if m.get("status") in ("IN_PLAY", "HALF_TIME", "PAUSED"))
    title    = "FOOTY - Live Football"
    right    = f"LIVE:{live_n}  next refresh:{next_refresh}s"
    if filter_league:
        right = f"[{filter_league}]  " + right
    safestr(win, 0, 1,                      title,   curses.color_pair(COL_HEADER) | curses.A_BOLD)
    safestr(win, 0, w // 2 - len(now_str) // 2, now_str, curses.color_pair(COL_HEADER))
    safestr(win, 0, max(1, w - len(right) - 2), right,   curses.color_pair(COL_HEADER))


def draw_leaguebar(win, filter_league):
    win.erase()
    h, w = win.getmaxyx()
    x = 1
    parts = [("0", "ALL", None)] + [(str(i), code, code) for i, code in enumerate(LEAGUE_KEYS, 1)]
    for key, label, code in parts:
        tag  = f"[{key}]{label}"
        attr = curses.A_BOLD | curses.color_pair(COL_TITLE) if filter_league == code else curses.color_pair(COL_DIM) | curses.A_DIM
        if x + len(tag) + 2 >= w:
            break
        safestr(win, 0, x, tag, attr)
        x += len(tag) + 3


def draw_controls(win, view):
    h, w = win.getmaxyx()
    win.erase()
    safehline(win, 0, 0, w - 1)
    if view == "main":
        ctrl = "UP/DOWN:navigate  ENTER:detail  0-6:filter  s:standings  r:refresh  q:quit"
    elif view == "detail":
        ctrl = "b/ESC:back  r:refresh  q:quit"
    else:
        ctrl = "b/ESC:back  q:quit"
    safestr(win, 1, 1, ctrl, curses.color_pair(COL_DIM))


def draw_ticker(win, matches):
    win.erase()
    h, w = win.getmaxyx()
    goals = []
    for m in matches:
        home = m.get("homeTeam", {}).get("shortName") or "?"
        away = m.get("awayTeam", {}).get("shortName") or "?"
        for g in m.get("goals", []):
            scorer = g.get("scorer", {}).get("name", "?")
            minute = g.get("minute", "?")
            gtype  = g.get("type", "")
            suffix = "(pen)" if gtype == "PENALTY" else "(og)" if gtype == "OWN_GOAL" else ""
            goals.append(f"{minute}' {scorer}{' ' + suffix if suffix else ''}  [{home} v {away}]")
    if not goals:
        text = "GOALS: none yet"
    else:
        text = "GOALS: " + "   |   ".join(goals)
    safestr(win, 0, 0, text, curses.color_pair(COL_DIM))


def draw_matches(win, matches, selected_idx, filter_league):
    win.erase()
    h, w = win.getmaxyx()
    ms = get_sorted(matches, filter_league)

    # Fixed column widths; team columns fill the rest
    C_SEL    = 1
    C_LEA    = 4
    C_STAT   = 4
    C_MIN    = 4
    C_SCORE  = 5
    C_KO     = 5
    GAPS     = 7 * 2   # spaces between cols
    remaining = w - C_SEL - C_LEA - C_STAT - C_MIN - C_SCORE - C_KO - GAPS
    C_TEAM   = max(8, remaining // 2)

    hdr = (f"{'':>{C_SEL}} "
           f"{'LEA':<{C_LEA}} "
           f"{'HOME':<{C_TEAM}} "
           f"{'SCR':^{C_SCORE}} "
           f"{'AWAY':<{C_TEAM}} "
           f"{'ST':^{C_STAT}} "
           f"{'MIN':^{C_MIN}} "
           f"{'KO':^{C_KO}}")
    safestr(win, 0, 0, hdr, curses.color_pair(COL_HEADER) | curses.A_BOLD)
    safehline(win, 1, 0, w - 1)

    for i, m in enumerate(ms):
        row = i + 2
        if row >= h:
            break

        status = m.get("status", "")
        code   = m.get("competition", {}).get("code", "")
        home   = (m.get("homeTeam", {}).get("shortName") or m.get("homeTeam", {}).get("name", "?"))[:C_TEAM]
        away   = (m.get("awayTeam", {}).get("shortName") or m.get("awayTeam", {}).get("name", "?"))[:C_TEAM]
        score  = fmt_score(m)
        st     = STATUS_SHORT.get(status, status[:4]).strip()
        minute = str(m.get("minute", "")) if m.get("minute") else ""
        ko     = fmt_time(m.get("utcDate", ""))
        sel    = ">" if i == selected_idx else " "

        is_live = status in ("IN_PLAY", "PAUSED", "HALF_TIME")
        is_sel  = (i == selected_idx)

        if is_sel:
            attr = curses.color_pair(COL_SELECTED) | curses.A_BOLD
        elif is_live:
            attr = curses.color_pair(COL_LIVE) | curses.A_BOLD
        elif status == "FINISHED":
            attr = curses.color_pair(COL_DEFAULT)
        else:
            attr = curses.color_pair(COL_DIM) | curses.A_DIM

        line = (f"{sel:>{C_SEL}} "
                f"{code:<{C_LEA}} "
                f"{home:<{C_TEAM}} "
                f"{score:^{C_SCORE}} "
                f"{away:<{C_TEAM}} "
                f"{st:^{C_STAT}} "
                f"{minute:^{C_MIN}} "
                f"{ko:^{C_KO}}")
        safestr(win, row, 0, line, attr)

    if not ms:
        safestr(win, 3, 2, "No matches found for today.", curses.color_pair(COL_DIM))


def draw_detail(win, match, stats):
    win.erase()
    h, w = win.getmaxyx()

    if not match:
        safestr(win, 1, 1, "Could not load match. Check connection or rate limit.", curses.A_BOLD)
        return

    home   = match.get("homeTeam", {}).get("name", "?")
    away   = match.get("awayTeam", {}).get("name", "?")
    status = match.get("status", "")
    code   = match.get("competition", {}).get("code", "")
    comp   = LEAGUES.get(code, {}).get("name", code)
    sc     = match.get("score", {}).get("fullTime", {})
    hg, ag = sc.get("home", "-"), sc.get("away", "-")
    ht     = match.get("score", {}).get("halfTime", {})
    ht_h, ht_a = ht.get("home"), ht.get("away")
    st     = STATUS_SHORT.get(status, status).strip()
    minute = match.get("minute")

    row = 0
    banner = f"{home}  {hg} - {ag}  {away}"
    safestr(win, row, max(0, w // 2 - len(banner) // 2), banner, curses.A_BOLD | curses.color_pair(COL_TITLE))
    row += 1

    sub = comp + "   " + st
    if minute:
        sub += f"  {minute}'"
    if ht_h is not None:
        sub += f"   (half-time: {ht_h}-{ht_a})"
    safestr(win, row, max(0, w // 2 - len(sub) // 2), sub, curses.color_pair(COL_DIM))
    row += 1
    safehline(win, row, 0, w - 1); row += 1

    # Goals
    safestr(win, row, 1, "GOALS", curses.A_BOLD); row += 1
    goals = sorted(match.get("goals", []), key=lambda g: g.get("minute", 0))
    if not goals:
        safestr(win, row, 3, "no goals", curses.color_pair(COL_DIM)); row += 1
    else:
        for g in goals:
            if row >= h - 2:
                break
            gmin   = g.get("minute", "?")
            scorer = g.get("scorer", {}).get("name", "?")
            team   = g.get("team", {}).get("name", "?")
            gtype  = g.get("type", "REGULAR")
            assist = (g.get("assist") or {}).get("name", "")
            suffix = " [pen]" if gtype == "PENALTY" else " [og]" if gtype == "OWN_GOAL" else ""
            astr   = f"  assist: {assist}" if assist else ""
            line   = f"  {gmin:>3}'  {scorer}{suffix}  ({team}){astr}"
            attr   = curses.color_pair(COL_LIVE) if team == home else curses.color_pair(COL_SOON)
            safestr(win, row, 0, line, attr); row += 1

    safehline(win, row, 0, w - 1); row += 1

    # Stats
    safestr(win, row, 1, "MATCH STATS", curses.A_BOLD); row += 1
    if stats:
        LW = 20
        hdr = f"  {'Stat':<{LW}}  {home:<20}  {away:<20}"
        safestr(win, row, 0, hdr, curses.A_BOLD); row += 1
        stat_defs = [
            ("Possession %",    "possession"),
            ("Shots",           "shots"),
            ("Shots on Target", "shotsOnTarget"),
            ("Corners",         "corners"),
            ("Fouls",           "fouls"),
            ("Yellow Cards",    "yellowCards"),
            ("Red Cards",       "redCards"),
            ("Offsides",        "offsides"),
            ("Passes",          "passes"),
            ("Pass Accuracy %", "passAccuracy"),
            ("Saves",           "saves"),
        ]
        for label, key in stat_defs:
            if row >= h - 2:
                break
            sv = stats.get(key, {})
            hv = sv.get("home", "-")
            av = sv.get("away", "-")
            try:
                h_win = int(hv) > int(av)
                a_win = int(av) > int(hv)
            except Exception:
                h_win = a_win = False
            line = f"  {label:<{LW}}  {str(hv):<20}  {str(av):<20}"
            safestr(win, row, 0, line, curses.color_pair(COL_DEFAULT))
            hx = 2 + LW + 2
            ax = hx + 22
            if h_win:
                safestr(win, row, hx, f"{str(hv):<20}", curses.color_pair(COL_WIN) | curses.A_BOLD)
            if a_win:
                safestr(win, row, ax, f"{str(av):<20}", curses.color_pair(COL_WIN) | curses.A_BOLD)
            row += 1
    else:
        safestr(win, row, 3, "Stats not available for this match.", curses.color_pair(COL_DIM))
        row += 1

    # Lineups
    if stats and "lineup" in stats and row < h - 3:
        safehline(win, row, 0, w - 1); row += 1
        safestr(win, row, 1, "LINEUPS", curses.A_BOLD); row += 1
        lu     = stats["lineup"]
        home_l = lu.get("home", [])
        away_l = lu.get("away", [])
        CL2    = max(18, w // 2 - 4)
        safestr(win, row, 0, f"  {home:<{CL2}}  {away:<{CL2}}", curses.A_BOLD); row += 1
        for i in range(max(len(home_l), len(away_l))):
            if row >= h - 1:
                break
            hp = home_l[i] if i < len(home_l) else ""
            ap = away_l[i] if i < len(away_l) else ""
            safestr(win, row, 0, f"  {hp:<{CL2}}  {ap:<{CL2}}", curses.color_pair(COL_DEFAULT))
            row += 1


def draw_standings(win, data, league_code):
    win.erase()
    h, w = win.getmaxyx()
    info  = LEAGUES.get(league_code, {})
    title = f"STANDINGS: {info.get('name', league_code)}"
    safestr(win, 0, w // 2 - len(title) // 2, title, curses.A_BOLD | curses.color_pair(COL_TITLE))
    safehline(win, 1, 0, w - 1)

    if not data:
        safestr(win, 3, 2, "Standings not available (demo mode or rate limit).", curses.color_pair(COL_DIM))
        return

    standings = data.get("standings", [])
    total     = next((s for s in standings if s.get("type") == "TOTAL"), None)
    if not total:
        safestr(win, 3, 2, "No standings data.", curses.color_pair(COL_DIM)); return

    hdr = f"{'#':>3}  {'Team':<24}  {'MP':>3}  {'W':>3}  {'D':>3}  {'L':>3}  {'GF':>4}  {'GA':>4}  {'GD':>4}  {'Pts':>4}  Form"
    safestr(win, 2, 0, hdr, curses.A_BOLD)
    safehline(win, 3, 0, w - 1)

    table       = total.get("table", [])
    total_teams = len(table)
    for idx, entry in enumerate(table):
        row = 4 + idx
        if row >= h - 1:
            break
        pos  = entry.get("position", "?")
        team = (entry.get("team", {}).get("shortName") or entry.get("team", {}).get("name", "?"))[:24]
        mp   = entry.get("playedGames", 0)
        w_   = entry.get("won", 0)
        d    = entry.get("draw", 0)
        l_   = entry.get("lost", 0)
        gf   = entry.get("goalsFor", 0)
        ga   = entry.get("goalsAgainst", 0)
        gd   = entry.get("goalDifference", 0)
        pts  = entry.get("points", 0)
        form = (entry.get("form") or "").replace(",", "")[-5:]
        gd_s = f"+{gd}" if gd > 0 else str(gd)
        line = f"{pos:>3}  {team:<24}  {mp:>3}  {w_:>3}  {d:>3}  {l_:>3}  {gf:>4}  {ga:>4}  {gd_s:>4}  {pts:>4}  {form}"
        if pos <= 4:
            attr = curses.color_pair(COL_WIN) | curses.A_BOLD
        elif pos >= total_teams - 2:
            attr = curses.color_pair(COL_SOON)
        else:
            attr = curses.color_pair(COL_DEFAULT)
        safestr(win, row, 0, line, attr)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main(stdscr, api, refresh_interval):
    curses.curs_set(0)
    stdscr.timeout(200)
    init_colors()

    # State
    matches        = []
    view           = "main"
    selected_idx   = 0
    filter_league  = None
    detail_id      = None
    detail_match   = None
    detail_stats   = None
    standings_data = None
    standings_lc   = None
    last_refresh   = 0.0

    def do_refresh():
        nonlocal matches, last_refresh
        matches      = api.get_matches()
        last_refresh = time.time()

    do_refresh()

    while True:
        h, w = stdscr.getmaxyx()
        now  = time.time()
        nr   = max(0, int(refresh_interval - (now - last_refresh)))

        TB = 1   # topbar
        LB = 1   # league bar
        TK = 1   # ticker
        CT = 2   # controls
        BH = max(4, h - TB - LB - TK - CT)

        # Create windows fresh each frame — curses is fast enough, this avoids stale state
        topbar_w  = curses.newwin(TB, w, 0, 0)
        league_w  = curses.newwin(LB, w, TB, 0)
        body_w    = curses.newwin(BH, w, TB + LB, 0)
        ticker_w  = curses.newwin(TK, w, TB + LB + BH, 0)
        ctrl_w    = curses.newwin(CT, w, TB + LB + BH + TK, 0)

        draw_topbar(topbar_w,  matches, nr, filter_league)
        draw_leaguebar(league_w, filter_league)
        draw_controls(ctrl_w,  view)
        draw_ticker(ticker_w,  matches)

        if view == "main":
            draw_matches(body_w, matches, selected_idx, filter_league)
        elif view == "detail":
            draw_detail(body_w, detail_match, detail_stats)
        elif view == "standings":
            draw_standings(body_w, standings_data, standings_lc or "PL")

        topbar_w.noutrefresh()
        league_w.noutrefresh()
        body_w.noutrefresh()
        ticker_w.noutrefresh()
        ctrl_w.noutrefresh()
        curses.doupdate()

        if now - last_refresh >= refresh_interval:
            do_refresh()

        key = stdscr.getch()
        if key == -1:
            continue

        fm = get_sorted(matches, filter_league)

        if key in (ord("q"), ord("Q")):
            break
        elif key in (ord("r"), ord("R")):
            do_refresh()
            if view == "detail" and detail_id is not None:
                detail_match = api.get_match_detail(detail_id)
                detail_stats = api.get_match_stats(detail_id)
        elif key in (ord("b"), 27):
            if view != "main":
                view = "main"
        elif view == "main":
            if key == curses.KEY_UP:
                if fm:
                    selected_idx = (selected_idx - 1) % len(fm)
            elif key == curses.KEY_DOWN:
                if fm:
                    selected_idx = (selected_idx + 1) % len(fm)
            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                if fm and selected_idx < len(fm):
                    detail_id    = fm[selected_idx]["id"]
                    detail_match = api.get_match_detail(detail_id)
                    detail_stats = api.get_match_stats(detail_id)
                    view         = "detail"
            elif key == ord("0"):
                filter_league = None
                selected_idx  = 0
            elif key in (ord("s"), ord("S")):
                standings_lc   = filter_league or "PL"
                standings_data = api.get_standings(standings_lc)
                view           = "standings"
            else:
                for i, code in enumerate(LEAGUE_KEYS, 1):
                    if key == ord(str(i)):
                        filter_league = code
                        selected_idx  = 0
                        break

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    parser = argparse.ArgumentParser(description="FOOTY - Live Football Score Ticker")
    parser.add_argument("--key", "-k",  help="football-data.org API key (or set FOOTY_API_KEY)")
    parser.add_argument("--demo", "-d", action="store_true", help="Run with demo data, no key needed")
    parser.add_argument("--refresh",    type=int, default=30, help="Auto-refresh interval in seconds (default: 30)")
    args = parser.parse_args()

    demo    = args.demo
    api_key = args.key or os.environ.get("FOOTY_API_KEY", "")

    if not demo and not api_key:
        print("No API key found.\n")
        print("Get a FREE key (no credit card) at:")
        print("  https://www.football-data.org/client/register\n")
        print("Then run:")
        print("  export FOOTY_API_KEY=your_key")
        print("  python3 footy.py\n")
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