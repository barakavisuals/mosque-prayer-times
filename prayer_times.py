import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import re


# Use Central Time for all prayer-time dates.
CENTRAL = ZoneInfo("America/Chicago")


def get_today():
    """Return the current date/time in Central Time."""
    return datetime.now(CENTRAL)


def parse_time(value):
    """Convert 12-hour time such as '06:14 AM' to HH:MM."""
    return datetime.strptime(
        value.strip().upper(),
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

    today = get_today().strftime("%d %b")

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
    ICRR prayer times are published through Our Masajid.

    Table structure:
    Fajr Adhan, Fajr Iqamah,
    Sunrise,
    Dhuhr Adhan, Dhuhr Iqamah,
    Asr Adhan, Asr Iqamah,
    Maghrib Adhan, Maghrib Iqamah,
    Isha Adhan, Isha Iqamah
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

    now = get_today()

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

            # ICRR has 11 times:
            # 0 = Fajr Adhan
            # 1 = Fajr Iqamah
            # 2 = Sunrise
            # 3 = Dhuhr Adhan
            # 4 = Dhuhr Iqamah
            # 5 = Asr Adhan
            # 6 = Asr Iqamah
            # 7 = Maghrib Adhan
            # 8 = Maghrib Iqamah
            # 9 = Isha Adhan
            # 10 = Isha Iqamah

            if len(times) >= 11:

                return {
                    "fajr": {
                        "athan": parse_time(times[0]),
                        "iqamah": parse_time(times[1]),
                    },
                    "dhuhr": {
                        "athan": parse_time(times[3]),
                        "iqamah": parse_time(times[4]),
                    },
                    "asr": {
                        "athan": parse_time(times[5]),
                        "iqamah": parse_time(times[6]),
                    },
                    "maghrib": {
                        "athan": parse_time(times[7]),
                        "iqamah": parse_time(times[8]),
                    },
                    "isha": {
                        "athan": parse_time(times[9]),
                        "iqamah": parse_time(times[10]),
                    },
                }

    raise RuntimeError(
        "ICRR: could not find today's prayer times"
    )


def get_icp():
    """
    ICP prayer times from the MasjidiApp / UmmahSoft API.

    Masjid ID 50001 = Islamic Center of Pflugerville.
    """

    now = get_today()

    url = (
        "https://ummahsoft.org/salahtime/api/masjidi/v1/index.php/"
        f"masjids/50001/iqamahandprayertimes/"
        f"{now.year}/{now.month}"
    )

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    today = now.strftime("%Y-%m-%d")

    for entry in data.get("iqamaTimes", []):

        entry_date = entry["date"]["date"][:10]

        if entry_date != today:
            continue

        return {
            "fajr": {
                "athan": parse_time(entry["fajr_start_time"]),
                "iqamah": parse_time(entry["fajr_iqama_time"]),
            },
            "dhuhr": {
                "athan": parse_time(entry["zuhr_start_time"]),
                "iqamah": parse_time(entry["zuhr_iqama_time"]),
            },
            "asr": {
                "athan": parse_time(entry["asr_start_time"]),
                "iqamah": parse_time(entry["asr_iqama_time"]),
            },
            "maghrib": {
                "athan": parse_time(entry["magrib_start_time"]),
                "iqamah": parse_time(entry["magrib_iqama_time"]),
            },
            "isha": {
                "athan": parse_time(entry["isha_start_time"]),
                "iqamah": parse_time(entry["isha_iqama_time"]),
            },
        }

    raise RuntimeError(
        f"ICP: could not find today's row ({today})"
    )


def main():

    print("========================================")
    print("       MOSQUE PRAYER TIMES")
    print("========================================")

    today = get_today()

    print(
        "Date:",
        today.strftime("%Y-%m-%d")
    )

    print(
        "Timezone:",
        today.strftime("%Z")
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
    # ICP
    # -----------------------------------------

    try:

        results["ICP"] = get_icp()

        print("ICP: SUCCESS")

    except Exception as e:

        print(
            "ICP ERROR:",
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
        "ICP": results.get("ICP"),
    }

    json_output = json.dumps(
        result,
        indent=2
    )

    print(json_output)

    with open("prayer_times.json", "w") as file:
        file.write(json_output)

    print()
    print("Saved prayer times to prayer_times.json")


if __name__ == "__main__":
    main()
