import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re


def parse_time(value):
    """Convert 12-hour time such as '06:14 AM' to HH:MM."""
    return datetime.strptime(
        value.strip(),
        "%I:%M %p"
    ).strftime("%H:%M")


def get_namcc():
    url = "https://namcc.org/monthly-prayer-times/"

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    today = datetime.now().strftime("%d %b")

    tables = soup.find_all("table")

    for table in tables:

        rows = table.find_all("tr")

        for row in rows:

            cells = [
                c.get_text(" ", strip=True)
                for c in row.find_all(["th", "td"])
            ]

            if not cells:
                continue

            if cells[0] == today and len(cells) >= 13:

                return {
                    "fajr": {
                        "athan": parse_time(cells[2]),
                        "iqamah": parse_time(cells[3]),
                    },
                    "dhuhr": {
                        "athan": parse_time(cells[5]),
                        "iqamah": parse_time(cells[6]),
                    },
                    "asr": {
                        "athan": parse_time(cells[7]),
                        "iqamah": parse_time(cells[8]),
                    },
                    "maghrib": {
                        "athan": parse_time(cells[9]),
                        "iqamah": parse_time(cells[10]),
                    },
                    "isha": {
                        "athan": parse_time(cells[11]),
                        "iqamah": parse_time(cells[12]),
                    },
                }

    raise RuntimeError(
        f"NAMCC: could not find today's row ({today})"
    )


def get_icrr():
    """
    ICRR schedule is published through Our Masajid.
    """

    url = "https://ourmasajid.com/m/icrr/prayer-times"

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    now = datetime.now()

    date_formats = [
        now.strftime("%b %-d"),
        now.strftime("%B %-d"),
        now.strftime("%m/%d/%Y"),
        now.strftime("%Y-%m-%d"),
    ]

    for table in soup.find_all("table"):

        for row in table.find_all("tr"):

            cells = [
                c.get_text(" ", strip=True)
                for c in row.find_all(["th", "td"])
            ]

            if not cells:
                continue

            text = " ".join(cells)

            date_found = any(
                date_format in text
                for date_format in date_formats
            )

            if not date_found:
                continue

            times = re.findall(
                r"\d{1,2}:\d{2}\s*(?:AM|PM)",
                text,
                re.IGNORECASE
            )

            if len(times) >= 10:

                return {
                    "fajr": {
                        "athan": parse_time(times[0]),
                        "iqamah": parse_time(times[1]),
                    },
                    "dhuhr": {
                        "athan": parse_time(times[2]),
                        "iqamah": parse_time(times[3]),
                    },
                    "asr": {
                        "athan": parse_time(times[4]),
                        "iqamah": parse_time(times[5]),
                    },
                    "maghrib": {
                        "athan": parse_time(times[6]),
                        "iqamah": parse_time(times[7]),
                    },
                    "isha": {
                        "athan": parse_time(times[8]),
                        "iqamah": parse_time(times[9]),
                    },
                }

    raise RuntimeError(
        "ICRR: could not find today's prayer times"
    )


def main():

    print("========================================")
    print("       MOSQUE PRAYER TIMES")
    print("========================================")

    today = datetime.now()

    print(
        "Date:",
        today.strftime("%Y-%m-%d")
    )

    print()

    results = {}

    # -----------------------------------------
    # NAMCC
    # -----------------------------------------

    try:

        results["NAMCC"] = get_namcc()

        print("NAMCC: SUCCESS")

    except Exception as e:

        print(
            "NAMCC ERROR:",
            e
        )

    # -----------------------------------------
    # ICRR
    # -----------------------------------------

    try:

        results["ICRR"] = get_icrr()

        print("ICRR: SUCCESS")

    except Exception as e:

        print(
            "ICRR ERROR:",
            e
        )

    # -----------------------------------------
    # FINAL OUTPUT
    # -----------------------------------------

    print()

    print("========================================")
    print("FINAL JSON")
    print("========================================")

    result = {
        "date": today.strftime("%Y-%m-%d"),
        "NAMCC": results.get("NAMCC"),
        "ICRR": results.get("ICRR"),
    }

    print(
        json.dumps(
            result,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
