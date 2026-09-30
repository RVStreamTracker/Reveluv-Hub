#!/usr/bin/env python3
"""Daily updater for the Red Velvet stream tracker. Uses only the Python standard library.

Reads Spotify totals and daily streams from Kworb, YouTube views from Kworb (and from the
YouTube Data API if YOUTUBE_API_KEY is set, which also gives likes), then writes data.json.
history.json keeps one snapshot per day so daily gains and daily likes can be worked out.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from html.parser import HTMLParser

SPOTIFY_URL = "https://kworb.net/spotify/artist/1z4g3DjTBBZKhvAroFlhOM_songs.html"
YOUTUBE_URL = "https://kworb.net/youtube/artist/redvelvet.html"
UA = "RedVelvetStreamTracker/1.0 (fan project; one request per page per day)"

# Song title on the site -> song name on Kworb's Spotify page
SPOTIFY = {
    "Surfin' Boy": "Surfin' Boy",
    "Run Devil Run": "Run Devil Run",
    "Cosmic": "Cosmic",
    "Chill Kill": "Chill Kill",
    "Birthday": "Birthday",
    "Feel My Rhythm": "Feel My Rhythm",
    "Queendom": "Queendom",
    "Psycho": "Psycho",
    "Umpah Umpah": "Umpah Umpah",
    "Zimzalabim": "Zimzalabim",
    "RBB (Really Bad Boy)": "RBB (Really Bad Boy)",
    "Power Up": "Power Up",
    "Bad Boy": "Bad Boy",
    "Peek-A-Boo": "Peek-A-Boo",
    "Red Flavor": "Red Flavor",
    "Rookie": "Rookie",
    "Russian Roulette": "러시안 룰렛 Russian Roulette",
    "Automatic": "Automatic",
    "Dumb Dumb": "Dumb Dumb",
    "One Of These Nights": "7월 7일 One Of These Nights",
    "Ice Cream Cake": "Ice Cream Cake",
    "Happiness": "행복 (Happiness)",
}

# Song title on the site -> YouTube video ID of the music video.
# The ID is the 11 characters after "v=" in a YouTube link. "" means not known yet.
VIDEOS = {
    "Surfin' Boy": "",
    "Run Devil Run": "",
    "Cosmic": "FyG21rXCxlY",
    "Chill Kill": "xlyrt5eAtKI",
    "Birthday": "Ut1OzEVUiM4",
    "Feel My Rhythm": "R9At2ICm4LQ",
    "Queendom": "c9RzZpV460k",
    "Psycho": "uR8Mrt1IpXg",
    "Umpah Umpah": "vHS9E6JFja8",
    "Zimzalabim": "YBnGBb1wg98",
    "RBB (Really Bad Boy)": "IWJUPY-2EIM",
    "Power Up": "aiHSVQy9xN8",
    "Bad Boy": "J_CFBjAyPWE",
    "Peek-A-Boo": "6uJf2IT2Zh8",
    "Red Flavor": "WyiIGEHQP8o",
    "Rookie": "J0h8-OTC38I",
    "Russian Roulette": "QslJYDX3o8s",
    "Automatic": "px2Q47O0_eE",
    "Dumb Dumb": "XGdbaEDVWp0",
    "One Of These Nights": "9xWiro_tS1k",
    "Ice Cream Cake": "glXgSSOKlls",
    "Happiness": "JFgv8bKfxEs",
}


class Rows(HTMLParser):
    """Collects every table row as a list of cell texts, plus any YouTube video IDs linked in it."""

    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def _end_cell(self):
        if self.cell is not None and self.row is not None:
            self.row["cells"].append("".join(self.cell).strip())
        self.cell = None

    def _end_row(self):
        self._end_cell()
        if self.row is not None and self.row["cells"]:
            self.rows.append(self.row)
        self.row = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._end_row()
            self.row = {"cells": [], "ids": []}
        elif tag in ("td", "th") and self.row is not None:
            self._end_cell()
            self.cell = []
        elif tag == "a" and self.row is not None:
            m = re.search(r"video/([\w-]{11})\.html", dict(attrs).get("href") or "")
            if m:
                self.row["ids"].append(m.group(1))

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._end_cell()
        elif tag == "tr":
            self._end_row()


def fetch(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as err:
            print("Could not fetch", url, "-", err)
            time.sleep(5 * (attempt + 1))
    return None


def num(text):
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else None


def parse_rows(html):
    parser = Rows()
    parser.feed(html)
    parser._end_row()
    return parser.rows


def read_spotify():
    html = fetch(SPOTIFY_URL)
    if not html:
        return None, None
    found = {}
    for row in parse_rows(html):
        cells = row["cells"]
        if len(cells) >= 3 and num(cells[1]) is not None and num(cells[2]) is not None:
            found.setdefault(cells[0], (num(cells[1]), num(cells[2])))
    m = re.search(r"Last updated:\s*(\d{4}/\d{2}/\d{2})", html)
    return found, (m.group(1) if m else None)


def read_kworb_youtube():
    html = fetch(YOUTUBE_URL)
    if not html:
        return None
    found = {}
    for row in parse_rows(html):
        cells = row["cells"]
        if row["ids"] and len(cells) >= 3 and num(cells[1]) is not None:
            found.setdefault(row["ids"][0], (num(cells[1]), num(cells[2])))
    return found


def read_api(ids):
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    ids = [i for i in ids if i]
    if not key or not ids:
        return {}
    found = {}
    for start in range(0, len(ids), 50):
        query = urllib.parse.urlencode({"part": "statistics", "id": ",".join(ids[start:start + 50]), "key": key})
        body = fetch("https://www.googleapis.com/youtube/v3/videos?" + query)
        if not body:
            continue
        for item in json.loads(body).get("items", []):
            stats = item.get("statistics", {})
            views = int(stats["viewCount"]) if "viewCount" in stats else None
            likes = int(stats["likeCount"]) if "likeCount" in stats else None
            found[item["id"]] = (views, likes)
    return found


def gain(hist, today, title, field, now):
    """Average daily change since the most recent earlier snapshot, or None if there is none yet."""
    if now is None:
        return None
    for day in sorted((d for d in hist if d < today.isoformat()), reverse=True):
        before = hist[day].get(title, {}).get(field)
        if before is not None:
            days = max(1, (today - date.fromisoformat(day)).days)
            return max(0, round((now - before) / days))
    return None


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def main():
    today = datetime.now(timezone.utc).date()
    ds = today.isoformat()
    data = load("data.json", {"updated": "", "songs": {}})
    hist = load("history.json", {})

    spotify, kworb_date = read_spotify()
    kworb_yt = read_kworb_youtube()
    if spotify is None and kworb_yt is None:
        print("Both sources failed, keeping the old data.")
        sys.exit(1)
    api = read_api(VIDEOS.values())
    if not os.environ.get("YOUTUBE_API_KEY", "").strip():
        print("No YOUTUBE_API_KEY set: likes will stay empty.")

    songs, snap, missing = {}, {}, []
    for title in SPOTIFY:
        old = data.get("songs", {}).get(title) or {}
        sp, yt = old.get("spotify"), old.get("youtube")
        snap[title] = {}

        if spotify is not None:
            hit = spotify.get(SPOTIFY[title])
            if hit:
                sp = {"total": hit[0], "yday": hit[1]}
                snap[title]["s"] = hit[0]
            else:
                missing.append(title + " (Spotify)")

        vid = VIDEOS.get(title, "")
        if vid:
            views = yday = likes = None
            if kworb_yt and vid in kworb_yt:
                views, yday = kworb_yt[vid]
            if vid in api:
                api_views, likes = api[vid]
                if api_views is not None and (views is None or api_views >= views):
                    views = api_views
            if views is not None:
                if yday is None:
                    yday = gain(hist, today, title, "y", views)
                snap[title]["y"] = views
                prev = yt or {}
                yt = {"total": views, "yday": yday, "likes": prev.get("likes"), "ylikes": prev.get("ylikes")}
                if likes is not None:
                    snap[title]["l"] = likes
                    yt["likes"] = likes
                    yt["ylikes"] = gain(hist, today, title, "l", likes)
            else:
                missing.append(title + " (YouTube)")
        else:
            missing.append(title + " (YouTube: no video ID yet)")
        songs[title] = {"spotify": sp, "youtube": yt}

    hist[ds] = snap
    for day in [d for d in hist if (today - date.fromisoformat(d)).days > 60]:
        del hist[day]

    out = {"updated": kworb_date or ds, "songs": songs}
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=1)
    print("Updated", len(songs), "songs. Data date:", out["updated"])
    if missing:
        print("No fresh numbers for:", ", ".join(missing))


if __name__ == "__main__":
    main()
