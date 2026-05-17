# footy - Live Football Score Ticker

a terminal based football widget. idk why it should exist but it does now smh.

Leagues: Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Champions League


## Setup

    pip install requests

Get a free BSD key at:
    https://sports.bzzoiro.com/register/

    python3 footy.py --key YOUR_KEY
    # or
    export BSD_API_KEY=your_key && python3 footy.py
    # or demo mode (no key)
    python3 footy.py --demo


## Controls

    UP / DOWN    navigate matches
    ENTER        match detail
    0            all leagues
    1-6          filter by league (PL / La Liga / Bundesliga / Serie A / Ligue 1 / UCL)
    s            standings
    r            force refresh
    b / ESC      back
    q            quit


## Detail view gives you (all free)

    Goals       minute, scorer, assist, description, running score
    Cards       yellow / red / yellow-red, minute, player, team
    Subs        player on/off, minute, team
    Stats       possession, shots, SoT, corners, fouls, cards, offsides,
                pass accuracy, attacks, dangerous attacks, xG
    Lineups     shirt number, position, name for all 11 starters per side
