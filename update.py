#!/usr/bin/env python3
"""Daily updater for the Red Velvet stream tracker. 

Reads Spotify totals and daily streams from Kworb, YouTube views from Kworb, then writes data.json.
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
from html import unescape
from html.parser import HTMLParser

SPOTIFY_URL = "https://kworb.net/spotify/artist/1z4g3DjTBBZKhvAroFlhOM_songs.html"
YOUTUBE_URL = "https://kworb.net/youtube/artist/redvelvet.html"
UA = "RedVelvetStreamTracker/1.0 (fan project; one request per page per day)"

# kworb spotify
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

# youtube videos
VIDEOS = {
    "Surfin' Boy": "NZP153MUpHY",
    "Run Devil Run": "MP7w6N5Jlow",  # a stage clip, not a music video
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

# bsides
BSIDES = [
    "Hot Girls Cold Vibe",
    "Hula Hoop",
    "Orchestra",
    "Hawaii",
    "Sweet Dreams",
    "Night Drive",
    "Bubble",
    "Sunflower",
    "Last Drop",
    "Love Arcade",
    "Knock Knock (Who's There?)",
    "Will I Ever See You Again?",
    "Underwater",
    "Iced Coffee",
    "Nightmare",
    "One Kiss",
    "Bulldozer",
    "Scenery",
    "Wings",
    "Bye Bye",
    "Celebrate",
    "On A Ride",
    "Zoom",
    "Bamboleo",
    "Beg For Me",
    "Good, Bad, Ugly",
    "In My Dreams",
    "Rainbow Halo",
    "Better Be",
    "Hello, Sunset",
    "Knock On Wood",
    "Pose",
    "Pushin' N Pullin'",
    "In & Out",
    "La Rouge",
    "Remember Forever",
    "Carpool",
    "Eyes Locked, Hands Locked",
    "Jumpin'",
    "Ladies Night",
    "Love Is The Way",
    "Bing Bing",
    "LP",
    "Milkshake",
    "Parade",
    "Sunny Side Up!",
    "Butterflies",
    "Sassy Me",
    "So Good",
    "Taste",
    "Blue Lemonade",
    "Hit That Drum",
    "Mosquito",
    "Mr. E",
    "With You",
    "All Right",
    "Time To Love",
    "About Love",
    "Attaboy",
    "I Just",
    "Kingdom Come",
    "Look",
    "Moonlight Melody",
    "My Second Date",
    "Perfect 10",
    "Hear The Sea",
    "Mojito",
    "You Better Know",
    "Zoo",
    "Body Talk",
    "Happily Ever After",
    "Last Love",
    "Little Little",
    "Talk To Me",
    "Bad Dracula",
    "Fool",
    "Lucky Girl",
    "My Dear",
    "Some Love",
    "Sunny Afternoon",
    "Cool Hot Sweet Love",
    "First Time",
    "Light Me Up",
    "Rose Scent Breeze",
    "Campfire",
    "Cool World",
    "Day 1",
    "Don't U Wait No More",
    "Huff n Puff",
    "Lady's Room",
    "Oh Boy",
    "Red Dress",
    "Time Slip",
    "Candy",
    "Somethin' Kinda Crazy",
    "Stupid Cupid",
    "Take It Slow"
]

# japanese
JAPANESE = [
    "Sappy",
    "#Cookie Jar",
    "Wildside",
    "Sayonara",
    "Aitai-tai",
    "Color of Love",
    "Marionette",
    "Swimming Pool",
    "Snap Snap",
    "'Cause it's you",
    "Jackpot"
]


ALIASES = {
    "First Time": "처음인가요 First Time",
    "Rose Scent Breeze": "장미꽃 향기는 바람에 날리고 Rose Scent Breeze",
    "La Rouge": "La Rouge - Special Track",
}


# solo and aseul
EXTRA = {
    "Irene & Seulgi": {
        "url": "https://kworb.net/spotify/artist/6bwp9ObI8FWvMPCIWVBmhl_songs.html",
        "songs": [
            "Monster",
            "Naughty",
            "TILT",
            "Feel Good",
            "Jelly",
            "Diamond",
            "Uncover (Sung by SEULGI)",
            "Girl Next Door",
            "Heaven",
            "Irresistible",
            "Trampoline",
            "What's Your Problem?",
            "Cheetah",
            "Fall 4 U",
            "Love Anxiety",
            "Wave",
            "Free",
        ],
    },
    "Seulgi": {
        "url": "https://kworb.net/spotify/artist/2QM5S4yO6xHgnNvF0nbZZq_songs.html",
        "songs": [
            "28 Reasons",
            "Wow Thing",
            "Anywhere But Home",
            "Baby, Not Baby",
            "Dead Man Runnin'",
            "Bad Boy, Sad Girl",
            "Los Angeles",
            "Crown",
            "Praying",
            "In my memory",
            "Better Dayz",
            "Weakness",
            "Whatever",
            "Rollin' (With My Homies)",
            "Always",
        ],
    },
    "Irene": {
        "url": "https://kworb.net/spotify/artist/1FCug8HMxqearaZB5qwWQj_songs.html",
        "songs": [
            "Like A Flower",
            "Summer Rain",
            "Strawberry Silhouette",
            "Calling Me Back",
            "Ka-Ching",
            "Start Line",
            "Winter Wish",
            "I Feel Pretty",
            "Biggest Fan",
            "Best Believe",
            "Don't Wanna Get Up",
            "Face To Face",
            "Million Miles Away",
            "Love Can Make A Way",
            "Black Halo",
            "SPIT IT OUT",
            "MTV (My Timeless Video)",
            "Wasteland",
        ],
    },
    "Wendy": {
        "url": "https://kworb.net/spotify/artist/0FRUZvZNPzM3YJMABJxf2K_songs.html",
        "songs": [
            "Written In The Stars",
            "Like Water",
            "What If Love",
            "Goodbye",
            "When This Rain Stops",
            "Wish You Hell",
            "Spring Love",
            "His Car Isn't Yours",
            "Daydream",
            "Two Words",
            "I Can Only See You",
            "Best Friend (with SEULGI)",
            "Why Can't You Love Me?",
            "Airport Goodbyes",
            "The Road",
            "Sunkiss",
            "Queen Of The Party",
            "Doll",
            "Vermilion",
            "Better Judgement",
            "If I Could Read Your Mind",
            "Best Ever",
            "Miracle",
            "Say You Love Me",
            "Chapter You",
            "Hate²",
            "EXISTENTIAL CRISIS",
            "The Little Match Girl",
            "Let You Know",
            "EMOTIONS",
            "Fireproof",
            "Believe",
            "Girls",
            "FLY",
        ],
    },
    "Joy": {
        "url": "https://kworb.net/spotify/artist/0sYpJ0nCC8AlDrZFeAA7ub_songs.html",
        "songs": [
            "Hello",
            "Introduce me a good person",
            "Je T'aime",
            "Yeowooya",
            "Dream Me",
            "Day By Day",
            "I'm OK (feat. Lee Hyun Woo)",
            "Always In My Heart",
            "Your Days",
            "Shiny Boy",
            "Happy Birthday To You",
            "If Only",
            "Why isn't love always easy?",
            "Waiting for You",
            "Love Splash!",
            "Be There For You",
            "The Way To Me",
            "OMG!",
            "Your Name",
            "Blue night song",
            "My Lips Like Warm Coffee",
            "La Vie En Bleu",
            "Scent Of Green",
            "Get Up And Dance",
            "Unwritten Page",
            "Cuddle",
            "Love Condition",
        ],
    },
}
# solo aliases
EXTRA_ALIASES = {
    "Uncover (Sung by SEULGI)": "Uncover (Sung by SEULGI) - Bonus Track",
    "Always In My Heart": "이별을 배웠어 Always In My Heart",
    "Spring Love": "봄인가 봐 Spring Love",
    "Let You Know": "아나요 Let You Know",
    "Ka-Ching": "Ka-Ching - Special Track",
    "I Feel Pretty": "I Feel Pretty - Special Track",
    "Why isn't love always easy?": "Why isn't love always easy? (Romance 101 X JOY)",
    "Airport Goodbyes": "Airport Goodbyes (Prod. The Black Skirts)",
}


def norm(text):
    return re.sub(r"[^0-9a-z\uac00-\ud7a3]", "", (text or "").lower())


def lookup(found, name):
    wanted = norm(name)
    for key, value in found.items():
        if norm(key) == wanted:
            return value
    return None


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


def read_spotify(url=SPOTIFY_URL):
    html = fetch(url)
    if not html:
        return None, None
    found = {}
    for row in parse_rows(html):
        cells = row["cells"]
        if len(cells) >= 2 and num(cells[1]) is not None:
            found.setdefault(cells[0], (num(cells[1]), num(cells[2]) if len(cells) > 2 else None))
    m = re.search(r"Last updated:\s*(\d{4}/\d{2}/\d{2})", html)
    return found, (m.group(1) if m else None)


def read_peaks(url):
    """Kworb's "Peaks" page for an artist: every song's best chart position (Global and by country).

    Returns a list like [{"t": "Psycho", "d": "2019/12/27", "s": 136095619, "p": {"Global": 54, "KR": 29}}], in
    Kworb's order (most chart streams first), or None if the page could not be read.
    """
    html = fetch(url)
    if not html:
        return None
    rows = parse_rows(html)
    header = None
    for row in rows:
        cells = [c.strip() for c in row["cells"]]
        if cells and cells[0].lower() == "peak date":
            header = cells
            break
    if not header:
        header = ["Peak Date", "Title", "Streams", "Global", "ID", "PH", "TH", "MY", "SG", "KR", "TW", "VN", "HK", "JP",
                  "CA", "US", "SA", "AE", "RU", "BG"]
    out = []
    for row in rows:
        cells = [c.strip() for c in row["cells"]]
        if len(cells) < 4 or not re.match(r"\d{4}/\d{2}/\d{2}$", cells[0]):
            continue
        pos = {}
        for name, val in zip(header[3:], cells[3:]):
            if re.fullmatch(r"\d{1,3}", val):
                pos[name] = int(val)
        if pos:
            out.append({"t": cells[1], "d": cells[0], "s": num(cells[2]) or 0, "p": pos})
    if not out:
        print("Chart peaks page had no readable rows:", url)
        return None
    return out[:150]


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


MSC = "https://www.mystreamcount.com"
MAIN_ARTIST_ID = "1z4g3DjTBBZKhvAroFlhOM"   # rv spotify
# mystreamcount 
# ID is 22 letters at end of mystreamcount
MSC_TRACK_IDS = {
    "Love Anxiety": "5CQ9lSfkFurZ9ftmg838ZI",
}
MSC_STALE_DAYS = 2      # use mystreamcount when kworb is dated
msc_down = False        # set to true after one failed request so the rest are skipped


def msc_fetch(url):
    """One polite attempt. After the first failure we stop asking, so a block never slows the run."""
    global msc_down
    if msc_down:
        return None
    time.sleep(1)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as err:
        print("MyStreamCount unavailable (", err, ") - skipping it for this run.")
        msc_down = True
        return None


def msc_artist_tracks(artist_id):
    """{song title: Spotify track id} from a MyStreamCount artist page."""
    html = msc_fetch(MSC + "/artist/" + artist_id)
    tracks = {}
    if not html:
        return tracks
    parts = re.split(r"/track/([A-Za-z0-9]{22})", html)
    for i in range(1, len(parts) - 1, 2):
        tid, after = parts[i], parts[i + 1]
        after = after.split(">", 1)[1] if ">" in after else after
        text = re.sub(r"<[^>]*(>|$)", "\n", after[:1200])
        for line in text.split("\n"):
            line = unescape(line).strip()
            if line and re.search(r"[A-Za-z\uac00-\ud7a3]", line):
                tracks.setdefault(line, tid)
                break
    if not tracks:
        print("MyStreamCount artist page had no readable songs. Start of page:", html[:300].replace("\n", " "))
    return tracks


def msc_find(tracks, name):
    wanted = norm(name)
    for key, tid in tracks.items():
        if norm(key) == wanted:
            return tid
    close = [tid for key, tid in tracks.items() if wanted and norm(key).startswith(wanted)]
    if len(set(close)) == 1:
        return close[0]
    # for aliases
    tail = [tid for key, tid in tracks.items() if len(wanted) >= 5 and re.search(r"[\uac00-\ud7a3\u3040-\u30ff]", key) and norm(key).endswith(wanted)]
    return tail[0] if len(set(tail)) == 1 else None


def msc_total(track_id):
    html = msc_fetch(MSC + "/track/" + track_id)
    if not html:
        return None
    text = unescape(re.sub(r"<[^>]+>", " ", html))
    text = re.sub(r"\s+", " ", text)
    # so text dosent glitch
  
    for pattern in (r"accumulated\s+(\d[\d,]*)\s+streams", r"Total\s+Streams\s*:?\s*(\d[\d,]*)"):
        for m in re.finditer(pattern, text, re.I):
            n = num(m.group(1))
            if n and not (1900 <= n <= 2100):
                return n
    return None


# solo and aseul mv

EXTRA_VIDEOS = {
    "Monster": "Ujb-gvqsoi0",
    "TILT": "wlTvVgI5FEI",
    "Like A Flower": "KdOF5-h4qpw",
    "28 Reasons": "G_BYjnopO6U",
    "Hello": "lNvBbh5jDcA",
    "Naughty": "wCWoUUWwdqg",
    "Biggest Fan": "x7wLlK9MMN4",
    "Baby, Not Baby": "S-VLzICd2FE",
    "Wow Thing": "KR5CtMLuiqQ",
    "Wish You Hell": "yIQgSDpwFEo",
    "Sunkiss": "5PS2cJsSJrI",
    "Daydream": "L1rR_smhD78",
    "Like Water": "-Ih5UArd4zk",
    "Love Splash!": "-2fAmkQS854",
}

MV_SEARCH = {
    "Irene & Seulgi": ["Cheetah"],
    "Irene": ["Wasteland"],
    "Seulgi": ["Dead Man Runnin'", "Rollin' (With My Homies)", "Better Dayz"],
    "Wendy": ["Goodbye", "Girls"],
    "Joy": ["Je T'aime", "Introduce me a good person", "Yeowooya"],
}
MV_SKIP = ("teaser", "dance practice", "performance", "live", "reaction", "lyric", "audio", "behind", "making",
           "highlight", "stage", "reacts", "shorts", "cover", "preview", "spoiler", "snippet", "visualizer", "clip")
MV_RETRY_DAYS = 30


def squash(text):
    return re.sub(r"[^a-z0-9\uac00-\ud7a3]", "", (text or "").lower())


def find_mv(who, title, key):
    """Search YouTube for a song's official music video. Returns a video ID only when the result looks right."""
    name = "Red Velvet" if who == "Irene & Seulgi" else who
    query = urllib.parse.urlencode({"part": "snippet", "q": name + " " + title + " MV", "type": "video",
                                    "maxResults": 8, "key": key})
    body = fetch("https://www.googleapis.com/youtube/v3/search?" + query)
    if not body:
        return None
    try:
        items = json.loads(body).get("items", [])
    except Exception:
        return None
    want = squash(title)
    for item in items:
        vid = (item.get("id") or {}).get("videoId")
        text = (item.get("snippet") or {}).get("title", "")
        low = text.lower()
        if not vid or want not in squash(text):
            continue
        if not re.search(r"\bm/?v\b|music video", low):
            continue
        if any(w in low for w in MV_SKIP):
            continue
        if squash(name.split(" ")[0]) not in squash(text):
            continue
        return vid
    return None


def discover_videos(data, today):
    """Returns {title: video ID} for the solo and sub-unit songs, finding new ones when it can."""
    vids = dict(data.get("vids", {}))
    vids.update(EXTRA_VIDEOS)
    tried = dict(data.get("vids_tried", {}))
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        return vids, tried
    found = 0
    for who, titles in MV_SEARCH.items():
        for title in titles:
            if title in vids:
                continue
            last = tried.get(title)
            try:
                recent = last and (today - date.fromisoformat(last)).days < MV_RETRY_DAYS
            except Exception:
                recent = False
            if recent:
                continue
            vid = find_mv(who, title, key)
            tried[title] = today.isoformat()
            if vid:
                vids[title] = vid
                found += 1
                print(who + ": found a music video for", title, "->", vid)
    if found == 0:
        print("No new solo or sub-unit music videos found today.")
    return vids, tried



APPLE_COUNTRIES = ["kr", "jp", "th", "id", "ph", "my", "sg", "tw", "hk", "vn", "us", "uk", "ar", "au", "br", "ca",
                   "co", "fr", "de", "in", "it", "mx", "nl", "pe", "pl", "ru", "es", "tr", "dz", "ao", "ai", "ag",
                   "am", "at", "az", "bh", "bb", "by", "be", "bz", "bj", "bm", "bt", "bo", "bw", "vg", "bn", "bg",
                   "bf", "kh", "cm", "cv", "ky", "td", "cl", "cn", "cr", "hr", "cy", "cz", "ci", "dk", "dm", "do",
                   "ec", "eg", "sv", "ee", "fj", "fi", "gm", "gh", "gr", "gd", "gt", "gw", "gy", "hn", "hu", "is",
                   "ie", "il", "jm", "jo", "kz", "ke", "kw", "kg", "la", "lv", "lb", "lr", "ly", "lt", "lu", "mo",
                   "mg", "mw", "mv", "ml", "mt", "mr", "mu", "fm", "md", "mn", "ms", "ma", "mz", "mm", "na", "np",
                   "nz", "ni", "ne", "ng", "mk", "no", "om", "pa", "pg", "py", "pt", "qa", "cg", "ro", "kn", "sa",
                   "sn", "rs", "sc", "sl", "sk", "si", "sb", "za", "lk", "lc", "vc", "sr", "sz", "se", "ch", "tj",
                   "tz", "bs", "tt", "tn", "tm", "tc", "ug", "ua", "ae", "uy", "uz", "ve", "ye", "zw"]


ITUNES_COUNTRIES = ["th", "id", "ph", "my", "sg", "tw", "hk", "vn", "jp", "us", "uk", "mn", "ar", "au", "br", "ca",
                    "co", "fr", "de", "in", "it", "mx", "nl", "pe", "pl", "ru", "es", "tr", "ai", "ag", "am", "at",
                    "az", "bh", "bb", "by", "be", "bz", "bm", "bo", "bw", "vg", "bn", "bg", "bf", "kh", "cv", "ky",
                    "cl", "cr", "cy", "cz", "dk", "dm", "do", "ec", "eg", "sv", "ee", "fj", "fi", "gm", "gh", "gr",
                    "gd", "gt", "gw", "hn", "hu", "ie", "il", "jo", "kz", "ke", "kg", "la", "lv", "lb", "lt", "lu",
                    "mo", "mt", "mu", "fm", "md", "mz", "na", "np", "nz", "ni", "ne", "ng", "no", "om", "pa", "pg",
                    "py", "pt", "qa", "ro", "kn", "sa", "sk", "si", "za", "lk", "sz", "se", "ch", "tj", "bs", "tt",
                    "tm", "ug", "ua", "ae", "uz", "ve", "zw"]
APPLE_NAMES = {
    "Red Velvet": ("red velvet", "레드벨벳", "レッドベルベット"),
    "Irene": ("irene", "아이린", "アイリーン"),
    "Seulgi": ("seulgi", "슬기", "スルギ"),
    "Wendy": ("wendy", "웬디", "ウェンディ"),
    "Joy": ("joy", "조이", "ジョイ"),
}


def apple_artist(text):
    """Works out which of our artists a Kworb 'Artist - Title' cell belongs to. Returns (artist, title) or None."""
    parts = [p.strip() for p in re.split(r"\s[-\u2013]\s", text or "")]
    if len(parts) < 2:
        return None
    head = " ".join(parts[:-1]).lower()
    title = parts[-1]
    if ("irene" in head and "seulgi" in head) or ("아이린" in head and "슬기" in head):
        return "Irene & Seulgi", title
    names = [n.strip() for n in re.split(r"\s*(?:,|&|/|\bfeat\.?|\bft\.?|\sx\s)\s*", parts[0].lower()) if n.strip()]
    for who in ("Irene", "Seulgi", "Wendy", "Joy", "Red Velvet"):
        if any(n in APPLE_NAMES[who] for n in names):
            return who, " - ".join(parts[1:])
    return None


def read_chart(old, today, folder, label, codes):
    """Updates the saved peaks for one Kworb country-chart service (Apple Music or iTunes).
    Returns the new {"updated", "best"} block, or the old one on failure."""
    best = {w: dict(t) for w, t in (old or {}).get("best", {}).items()}
    seen_pages, hits = 0, 0
    stamp = today.strftime("%Y/%m/%d")
    for cc in codes:
        time.sleep(1)
        try:
            req = urllib.request.Request("https://kworb.net/charts/" + folder + "/" + cc + ".html", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", "replace")
        except Exception as err:
            print(label, cc.upper(), "not read -", err)
            continue
        rows = parse_rows(html)
        seen_pages += 1
        for row in rows:
            cells = [c.strip() for c in row["cells"]]
            if len(cells) < 2 or not re.fullmatch(r"\d{1,3}", cells[0]):
                continue
            hit = apple_artist(cells[-1])   # the last cell is "Artist - Title" (some countries have no P+ column)
            if not hit:
                continue
            who, title = hit
            pos = int(cells[0])
            entry = best.setdefault(who, {}).setdefault(title, {}).setdefault(cc.upper(), {"p": pos, "d": stamp})
            if pos < entry["p"]:
                entry["p"], entry["d"] = pos, stamp
            entry["l"] = stamp
            entry["n"] = pos
            hits += 1
    if not seen_pages:
        print(label + ": no country pages could be read, keeping the old data.")
        return old
    print(label + ": read", seen_pages, "country charts,", hits, "entries for our artists")
    return {"updated": stamp, "best": best}


def read_apple(old, today):
    return read_chart(old, today, "apple_s", "Apple Music", APPLE_COUNTRIES)


def gain(hist, today, title, field, now):
    """Average daily change since the most recent earlier snapshot, or None if there is none yet."""
    if now is None:
        return None
    for day in sorted((d for d in hist if d < today.isoformat()), reverse=True):
        before = hist[day].get(title, {}).get(field)
        if before is not None and not (1900 <= before <= 2100):   # ignore a release year that was once saved by mistake
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
    xvids, vids_tried = discover_videos(data, today)
    api.update(read_api([v for v in xvids.values() if v not in api]))
    if not os.environ.get("YOUTUBE_API_KEY", "").strip():
        print("No YOUTUBE_API_KEY set: likes will stay empty.")

    songs, snap, missing = {}, {}, []
    rv_msc, from_msc_main = None, 0
    for title in list(SPOTIFY) + BSIDES + JAPANESE:
        old = data.get("songs", {}).get(title) or {}
        sp, yt = old.get("spotify"), old.get("youtube")
        snap[title] = {}

        fresh = False
        if spotify is not None:
            hit = lookup(spotify, SPOTIFY.get(title) or ALIASES.get(title, title))
            if hit:
                sp = {"total": hit[0], "yday": hit[1]}
                snap[title]["s"] = hit[0]
                fresh = True
        if not fresh:
            # Not on Kworb (or Kworb is down): try MyStreamCount's Red Velvet page.
            if rv_msc is None:
                rv_msc = msc_artist_tracks(MAIN_ARTIST_ID)
            tid = None
            for name in (SPOTIFY.get(title), ALIASES.get(title), title):
                tid = msc_find(rv_msc, name) if name else None
                if tid:
                    break
            tid = tid or MSC_TRACK_IDS.get(title)
            total = msc_total(tid) if tid else None
            if total:
                sp = {"total": total, "yday": gain(hist, today, title, "s", total)}
                snap[title]["s"] = total
                from_msc_main += 1
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
        elif title in VIDEOS:
            missing.append(title + " (YouTube: no video ID yet)")
        songs[title] = {"spotify": sp, "youtube": yt}

    if from_msc_main:
        print("Red Velvet:", from_msc_main, "song(s) updated from MyStreamCount")
    xdates = dict(data.get("xdates", {}))
    for who, info in EXTRA.items():
        found, kdate = read_spotify(info["url"])
        if found is None:
            continue
        if kdate:
            xdates[who] = kdate
        try:
            age = (today - date(*map(int, kdate.split("/")))).days if kdate else 999
        except Exception:
            age = 999
        stale = age > MSC_STALE_DAYS
        print(who + ": Kworb page date", kdate, "-", ("STALE, trying MyStreamCount" if stale else "fresh, using Kworb"))
        msc, from_msc = None, 0
        why = {"no match": [], "no total": [], "lower": []}
        for title in info["songs"]:
            old = (data.get("songs", {}).get(title) or {}).get("spotify")
            hit = lookup(found, EXTRA_ALIASES.get(title, title))
            if hit and not stale:
                old = {"total": hit[0], "yday": hit[1]}
                snap[title] = {"s": hit[0]}
            else:
                if hit:
                    old = {"total": hit[0], "yday": None}   
                    
                if msc is None:
                    mid = re.search(r"/artist/([A-Za-z0-9]{22})", info["url"])
                    msc = msc_artist_tracks(mid.group(1)) if mid else {}
                tid = msc_find(msc, EXTRA_ALIASES.get(title, title)) or msc_find(msc, title) or MSC_TRACK_IDS.get(title)
                total = msc_total(tid) if tid else None
                if not tid:
                    why["no match"].append(title)
                elif not total:
                    why["no total"].append(title)
                elif hit and total < hit[0]:
                    why["lower"].append(title + " (MSC " + format(total, ",") + " < Kworb " + format(hit[0], ",") + ")")
                if total and (not hit or total >= hit[0]):
                    old = {"total": total, "yday": gain(hist, today, title, "s", total)}
                    snap[title] = {"s": total}
                    from_msc += 1
                elif not hit:
                    missing.append(title + " (" + who + ")")
            yt = (data.get("songs", {}).get(title) or {}).get("youtube")
            vid = xvids.get(title)
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
                    snap.setdefault(title, {})["y"] = views
                    prev = yt or {}
                    yt = {"total": views, "yday": yday, "likes": prev.get("likes"), "ylikes": prev.get("ylikes")}
                    if likes is not None:
                        snap[title]["l"] = likes
                        yt["likes"] = likes
                        yt["ylikes"] = gain(hist, today, title, "l", likes)
            songs[title] = {"spotify": old, "youtube": yt}
        for k, v in why.items():
            if v:
                print(who + ": MyStreamCount " + k + " for", "; ".join(v[:8]) + (" ..." if len(v) > 8 else ""))
        if msc is not None:
            print(who + ": MyStreamCount page had", len(msc), "songs")
        if from_msc:
            print(who + ":", from_msc, "song(s) updated from MyStreamCount")
            if from_msc * 2 >= len(info["songs"]):
                xdates[who] = today.strftime("%Y/%m/%d")

    hist[ds] = snap
    for day in [d for d in hist if (today - date.fromisoformat(d)).days > 60]:
        del hist[day]

    charts = dict(data.get("charts", {}))
    peak_pages = {"Red Velvet": "https://kworb.net/spotify/artist/" + MAIN_ARTIST_ID + ".html"}
    for who, info in EXTRA.items():
        peak_pages[who] = info["url"].replace("_songs.html", ".html")
    for who, url in peak_pages.items():
        peaks = read_peaks(url)
        if peaks:
            charts[who] = peaks
            print(who + ": read", len(peaks), "chart peaks")
        else:
            print(who + ": chart peaks not updated, keeping the old ones")

    try:
        apple = read_apple(data.get("apple"), today)
    except Exception as err:
        print("Apple Music: skipped -", err)
        apple = data.get("apple")
    try:
        itunes = read_chart(data.get("itunes"), today, "itunes", "iTunes", ITUNES_COUNTRIES)
    except Exception as err:
        print("iTunes: skipped -", err)
        itunes = data.get("itunes")
    out = {"updated": kworb_date or ds, "xdates": xdates, "songs": songs, "charts": charts, "vids": xvids, "vids_tried": vids_tried}
    if apple:
        out["apple"] = apple
    if itunes:
        out["itunes"] = itunes
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=1)
    print("Updated", len(songs), "songs. Data date:", out["updated"])
    if missing:
        print("No fresh numbers for:", ", ".join(missing))


if __name__ == "__main__":
    main()
