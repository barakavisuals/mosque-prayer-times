import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import sys

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

TODAY = datetime.now().strftime("%Y-%m-%d")

URLS = {
    "ICRR": "https://roundrockmasjid.org/prayer-times",
    "NAMCC": "https://namcc.org/monthly-prayer-times/",
}

PRAYERS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def clean(text):
    return " ".join(text.split())


def time_to_24h(time_string):
    """Convert 5:45 AM / 05:45 AM / 5:45AM -> 05:45"""

    if not time_string:
        return None

    time_string = clean(time_string).upper()

    for fmt in ("%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(time_string, fmt).strftime("%H:%M")
        except ValueError:
            pass

    return None


def get_page(url):
    print(f"Fetching: {url}")

    response = requests.get(
        url,
        timeout=30,
        headers=HEADERS,
    )

    print(f"HTTP status: {response.status_code}")

    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def find_time_strings(text):
    """
    Find all normal AM/PM times in a piece of text.
    """

    pattern = r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b"

    return re.findall(
        pattern,
        text,
        flags=re.IGNORECASE
    )


def normalize_prayer_name(name):
    name = clean(name).lower()

    aliases = {
        "fajr": "fajr",
        "zuhr": "dhuhr",
        "dhuhr": "dhuhr",
        "zuhur": "dhuhr",
        "asr": "asr",
        "maghrib": "maghrib",
        "isha": "isha",
        "eshaa": "isha",
    }

    return aliases.get(name)


# --------------------------------------------------
# ICRR
# --------------------------------------------------

def get_icrr():

    soup = get_page(URLS["ICRR"])

    prayers = {}

    # Look through table rows first
    for table in soup.find_all("table"):

        for row in table.find_all("tr"):

            cells = [
                clean(cell.get_text(" ", strip=True))
                for cell in row.find_all(["td", "th"])
            ]

            if not cells:
                continue

            row_text = " ".join(cells)

            prayer = None

            for possible_prayer in PRAYERS:

                if re.search(
                    rf"\b{possible_prayer}\b",
                    row_text,
                    re.IGNORECASE
                ):
                    prayer = possible_prayer
                    break

            # Handle Zuhr/Dhuhr
            if re.search(r"\b(?:zuhr|dhuhr)\b", row_text, re.IGNORECASE):
                prayer = "dhuhr"

            if not prayer:
                continue

            times = find_time_strings(row_text)

            if len(times) >= 2:

                prayers[prayer] = {
                    "athan": time_to_24h(times[0]),
                    "iqamah": time_to_24h(times[1]),
                }

    # Fallback: inspect page text
    if len(prayers) < 5:

        text = clean(soup.get_text(" ", strip=True))

        patterns = {
            "fajr": r"Fajr.*?(\d{1,2}:\d{2}\s*[AP]M).*?(\d{1,2}:\d{2}\s*[AP]M)",
            "dhuhr": r"(?:Dhuhr|Zuhr).*?(\d{1,2}:\d{2}\s*[AP]M).*?(\d{1,2}:\d{2}\s*[AP]M)",
            "asr": r"Asr.*?(\d{1,2}:\d{2}\s*[AP]M).*?(\d{1,2}:\d{2}\s*[AP]M)",
            "maghrib": r"Maghrib.*?(\d{1,2}:\d{2}\s*[AP]M).*?(\d{1,2}:\d{2}\s*[AP]M)",
            "isha": r"Isha.*?(\d{1,2}:\d{2}\s*[AP]M).*?(\d{1,2}:\d{2}\s*[AP]M)",
        }

        for prayer, pattern in patterns.items():

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                athan = time_to_24h(match.group(1))
                iqamah = time_to_24h(match.group(2))

                if athan and iqamah:

                    prayers[prayer] = {
                        "athan": athan,
                        "iqamah": iqamah,
                    }

    return prayers


# --------------------------------------------------
# NAMCC
# --------------------------------------------------

def get_namcc():

    soup = get_page(URLS["NAMCC"])

    prayers = {}

    # --------------------------------------------------
    # Find tables
    # --------------------------------------------------

    for table in soup.find_all("table"):

        rows = table.find_all("tr")

        for row in rows:

            cells = [
                clean(cell.get_text(" ", strip=True))
                for cell in row.find_all(["td", "th"])
            ]

            if len(cells) < 2:
                continue

            row_text = " ".join(cells)

            prayer = None

            # Identify prayer
            if re.search(r"\bFajr\b", row_text, re.IGNORECASE):
                prayer = "fajr"

            elif re.search(
                r"\b(?:Dhuhr|Zuhr|Zuhur)\b",
                row_text,
                re.IGNORECASE
            ):
                prayer = "dhuhr"

            elif re.search(r"\bAsr\b", row_text, re.IGNORECASE):
                prayer = "asr"

            elif re.search(r"\bMaghrib\b", row_text, re.IGNORECASE):
                prayer = "maghrib"

            elif re.search(r"\bIsha\b", row_text, re.IGNORECASE):
                prayer = "isha"

            if not prayer:
                continue

            times = find_time_strings(row_text)

            if len(times) >= 2:

                prayers[prayer] = {
                    "athan": time_to_24h(times[0]),
                    "iqamah": time_to_24h(times[1]),
                }

    return prayers


# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

def validate_prayers(name, prayers):

    print(f"\n{name} prayer count: {len(prayers)}")

    print(json.dumps(prayers, indent=2))

    missing = [
        prayer
        for prayer in PRAYERS
        if prayer not in prayers
    ]

    if missing:

        print(
            f"\n{name} is missing: "
            + ", ".join(missing)
        )

        return False

    return True


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 60)
    print("MOSQUE PRAYER TIME TEST")
    print("Date:", TODAY)
    print("=" * 60)

    results = {
        "date": TODAY,
        "mosques": {}
    }

    success = True

    # --------------------------------------------------
    # ICRR
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("ICRR")
    print("=" * 60)

    try:

        icrr = get_icrr()

        results["mosques"]["ICRR"] = icrr

        if not validate_prayers("ICRR", icrr):
            success = False

    except Exception as e:

        print("ICRR ERROR:", repr(e))

        results["mosques"]["ICRR"] = {
            "error": str(e)
        }

        success = False

    # --------------------------------------------------
    # NAMCC
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("NAMCC")
    print("=" * 60)

    try:

        namcc = get_namcc()

        results["mosques"]["NAMCC"] = namcc

        if not validate_prayers("NAMCC", namcc):
            success = False

    except Exception as e:

        print("NAMCC ERROR:", repr(e))

        results["mosques"]["NAMCC"] = {
            "error": str(e)
        }

        success = False

    # --------------------------------------------------
    # RAW RESULT
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("RAW RESULT")
    print("=" * 60)

    print(json.dumps(results, indent=2))

    # --------------------------------------------------
    # FAIL WORKFLOW IF DATA IS MISSING
    # --------------------------------------------------

    if not success:

        print("\n❌ Prayer-time retrieval was incomplete.")

        sys.exit(1)

    print("\n✅ Prayer-time retrieval successful.")


if __name__ == "__main__":
    main()