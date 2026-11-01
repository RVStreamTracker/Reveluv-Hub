"""Refreshes the fan leaderboard once a day.

For everyone who turned on "Show me on the leaderboards", this reads their public
Last.fm history, counts their Red Velvet plays (last 7 days, last 30 days, all time)
and saves the numbers to Supabase. Run by .github/workflows/leaderboard.yml.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import update  # reuses the song lists from update.py (it does not run anything on import)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
LASTFM_KEY = os.environ.get("LASTFM_KEY", "").strip()
LASTFM = "https://ws.audioscrobbler.com/2.0/"


def track_keys():
    """Same matching the website uses: 'artist|title' in lowercase."""
    keys = set()
    for t in list(update.SPOTIFY) + list(update.BSIDES) + list(update.JAPANESE):
        keys.add(("Red Velvet|" + t).lower())
    for who, info in update.EXTRA.items():
        artist = "Red Velvet - IRENE & SEULGI" if who == "Irene & Seulgi" else who
        for t in info["songs"]:
            keys.add((artist + "|" + t).lower())
    return keys


def http(url, headers=None, data=None, method="GET"):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=40) as r:
        body = r.read()
    return json.loads(body) if body else None


def sb(path, method="GET", payload=None):
    h = {"apikey": SERVICE_KEY, "Authorization": "Bearer " + SERVICE_KEY, "Content-Type": "application/json"}
    data = json.dumps(payload).encode() if payload is not None else None
    return http(SUPABASE_URL + "/rest/v1/" + path, h, data, method)


def lastfm_total(user, period, keys, max_pages):
    """Returns the number of tracked-song plays, or None if the profile can't be read."""
    total, page = 0, 1
    while True:
        q = urllib.parse.urlencode({"method": "user.getTopTracks", "user": user, "period": period,
                                    "limit": 1000, "page": page, "api_key": LASTFM_KEY, "format": "json"})
        d = None
        for attempt in range(4):
            try:
                d = http(LASTFM + "?" + q)
            except Exception as e:
                print("  request failed:", e)
                d = None
            if d and d.get("error") == 29:        # rate limited: wait and retry
                time.sleep(1.5 * (attempt + 1))
                continue
            break
        if not d or d.get("error") or "toptracks" not in d:
            if d and d.get("error"):
                print("  Last.fm error", d.get("error"), d.get("message"))
            return None
        tt = d["toptracks"]
        tracks = tt.get("track") or []
        if isinstance(tracks, dict):
            tracks = [tracks]
        for t in tracks:
            a = t.get("artist") or {}
            artist = a.get("name") or a.get("#text") or ""
            if (artist + "|" + t.get("name", "")).lower() in keys:
                total += int(t.get("playcount") or 0)
        pages = int((tt.get("@attr") or {}).get("totalPages") or 1)
        if page >= pages or page >= max_pages:
            return total
        page += 1
        time.sleep(0.25)


def main():
    if not (SUPABASE_URL and SERVICE_KEY and LASTFM_KEY):
        print("Missing SUPABASE_URL, SUPABASE_SERVICE_KEY or LASTFM_KEY secret. Nothing to do.")
        sys.exit(1)
    keys = track_keys()
    on = {r["id"] for r in sb("profiles?select=id&show_on_leaderboard=eq.true") or []}
    links = [r for r in sb("lastfm_links?select=id,lastfm_username") or [] if r["id"] in on]
    print(len(links), "listener(s) on the leaderboard")
    ok = skipped = 0
    for r in links:
        name = r["lastfm_username"]
        week = lastfm_total(name, "7day", keys, 6)
        month = lastfm_total(name, "1month", keys, 6) if week is not None else None
        alltime = lastfm_total(name, "overall", keys, 10) if month is not None else None
        if alltime is None:
            print("Skipped", name, "(could not read their Last.fm; keeping their old numbers)")
            skipped += 1
            continue
        sb("profiles?id=eq." + r["id"], "PATCH", {
            "plays_week": week, "plays_month": month, "plays_all": alltime,
            "scores_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        print("Updated", name, "- week", week, "month", month, "all", alltime)
        ok += 1
    print("Done:", ok, "updated,", skipped, "skipped")


if __name__ == "__main__":
    main()
