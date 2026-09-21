import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

TODAY = datetime.now().strftime("%Y-%m-%d")

URLS = {
    "ICRR": "https://roundrockmasjid.org/prayer-times",
    "NAMCC": "https://namcc.org/",
}


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def clean(text):
    return " ".join(text.split())


def time_to_24h(time_string):
    """Convert 05:45 AM -> 05:45"""
    if not time_string:
        return None

    time_string = time_string.strip().upper()

    for fmt in ("%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(time_string, fmt).strftime("%H:%M")
        except ValueError:
            pass

    return None


def get_page(url):
    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 Safari/604.1"
            )
        },
    )

    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


# --------------------------------------------------
# ICRR
# --------------------------------------------------

def get_icrr():
    soup = get_page(URLS["ICRR"])

    text = clean(soup.get_text(" ", strip=True))

    prayers = {}

    patterns = {
        "fajr": r"Fajr\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)",
        "dhuhr": r"(?:Zuhr|Dhuhr)\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)",
        "asr": r"Asr\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)",
        "maghrib": r"Maghrib\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)",
        "isha": r"Isha\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)",
    }

    for prayer, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            prayers[prayer] = {
                "athan": time_to_24h(match.group(1)),
                "iqamah": time_to_24h(match.group(2)),
            }

    return prayers


# --------------------------------------------------
# NAMCC
# --------------------------------------------------

def get_namcc():
    soup = get_page(URLS["NAMCC"])

    table = soup.find("table")

    if not table:
        raise Exception("NAMCC prayer table not found")

    rows = table.find_all("tr")

    prayers = {}

    for row in rows:
        cells = [clean(cell.get_text(" ", strip=True))
                 for cell in row.find_all(["td", "th"])]

        if len(cells) < 3:
            continue

        prayer = cells[0].lower()

        prayer_map = {
            "fajr": "fajr",
            "dhuhr": "dhuhr",
            "asr": "asr",
            "maghrib": "maghrib",
            "isha": "isha",
        }

        if prayer not in prayer_map:
            continue

        prayers[prayer_map[prayer]] = {
            "athan": time_to_24h(cells[1]),
            "iqamah": time_to_24h(cells[2]),
        }

    return prayers


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 50)
    print("MOSQUE PRAYER TIME TEST")
    print("Date:", TODAY)
    print("=" * 50)

    results = {
        "date": TODAY,
        "mosques": {}
    }

    # ICRR
    try:
        results["mosques"]["ICRR"] = get_icrr()
        print("\nICRR:")
        print(json.dumps(results["mosques"]["ICRR"], indent=2))
    except Exception as e:
        print("\nICRR ERROR:", e)

    # NAMCC
    try:
        results["mosques"]["NAMCC"] = get_namcc()
        print("\nNAMCC:")
        print(json.dumps(results["mosques"]["NAMCC"], indent=2))
    except Exception as e:
        print("\nNAMCC ERROR:", e)

    print("\n" + "=" * 50)
    print("RAW RESULT")
    print("=" * 50)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()