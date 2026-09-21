import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import sys


TODAY = datetime.now()
TODAY_MONTH_DAY = TODAY.strftime("%b %d")
TODAY_DAY = TODAY.strftime("%d")
TODAY_MONTH = TODAY.strftime("%b")


ICRR_URL = "https://roundrockmasjid.org/prayer-times"
NAMCC_URL = "https://namcc.org/monthly-prayer-times/"


def get_soup(url):
    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (Prayer Times Automation)"
        }
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def normalize_time(value):
    """Convert source time to HH:MM 24-hour format."""
    value = value.strip()

    formats = [
        "%I:%M %p",
        "%I:%M%p",
        "%H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            pass

    raise ValueError(f"Could not understand time: {value}")


def normalize_date(value):
    """Normalize dates such as 'Sep 21', 'September 21', '21', etc."""
    value = " ".join(value.strip().split())

    formats = [
        "%b %d",
        "%B %d",
        "%m/%d",
        "%m/%d/%Y",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%b %d")
        except ValueError:
            pass

    return value


def get_icrr():
    print("\n=== ICRR ===")
    print(f"Looking for today's date: {TODAY_MONTH_DAY}")

    soup = get_soup(ICRR_URL)

    tables = soup.find_all("table")

    print(f"Found {len(tables)} table(s)")

    for table in tables:
        rows = table.find_all("tr")

        if not rows:
            continue

        header_cells = rows[0].find_all(["th", "td"])
        headers = [
            cell.get_text(" ", strip=True)
            for cell in header_cells
        ]

        expected = ["Date", "Fajr", "Zuhr", "Asr", "Maghrib", "Isha"]

        if not all(item in headers for item in expected):
            continue

        print(f"Using ICRR table headers: {headers}")

        header_map = {
            header.lower(): index
            for index, header in enumerate(headers)
        }

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            values = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            if len(values) < len(headers):
                continue

            row_date = normalize_date(values[header_map["date"]])

            if row_date != TODAY_MONTH_DAY:
                continue

            print(f"Found ICRR date row: {values}")

            return {
                "fajr": {
                    "athan": normalize_time(values[header_map["fajr"]]),
                    "iqamah": None
                },
                "dhuhr": {
                    "athan": normalize_time(values[header_map["zuhr"]]),
                    "iqamah": None
                },
                "asr": {
                    "athan": normalize_time(values[header_map["asr"]]),
                    "iqamah": None
                },
                "maghrib": {
                    "athan": normalize_time(values[header_map["maghrib"]]),
                    "iqamah": None
                },
                "isha": {
                    "athan": normalize_time(values[header_map["isha"]]),
                    "iqamah": None
                }
            }

    raise RuntimeError(
        f"ICRR does not have a prayer-time row for {TODAY_MONTH_DAY}"
    )


def get_namcc():
    print("\n=== NAMCC ===")
    print(f"Looking for today's date: {TODAY_DAY}")

    soup = get_soup(NAMCC_URL)

    tables = soup.find_all("table")

    print(f"Found {len(tables)} table(s)")

    required_columns = [
        "Date",
        "Fajr Adhaan",
        "Fajr Iqamah",
        "Dhuhr Adhaan",
        "Dhuhr Iqamah",
        "Asr Adhaan",
        "Asr Iqamah",
        "Maghrib Adhaan",
        "Maghrib Iqamah",
        "Isha Adhaan",
        "Isha Iqamah",
    ]

    for table_number, table in enumerate(tables, start=1):

        rows = table.find_all("tr")

        if not rows:
            continue

        header_cells = rows[0].find_all(["th", "td"])

        headers = [
            cell.get_text(" ", strip=True)
            for cell in header_cells
        ]

        if not all(column in headers for column in required_columns):
            continue

        print(f"Using NAMCC table #{table_number}")
        print(f"Headers: {headers}")

        header_map = {
            header: index
            for index, header in enumerate(headers)
        }

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])

            values = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            if len(values) < len(headers):
                continue

            row_date = values[header_map["Date"]].strip()

            # NAMCC dates are numeric day values such as "21".
            if row_date != TODAY_DAY:
                continue

            print(f"Found NAMCC date row: {values}")

            return {
                "fajr": {
                    "athan": normalize_time(
                        values[header_map["Fajr Adhaan"]]
                    ),
                    "iqamah": normalize_time(
                        values[header_map["Fajr Iqamah"]]
                    )
                },
                "dhuhr": {
                    "athan": normalize_time(
                        values[header_map["Dhuhr Adhaan"]]
                    ),
                    "iqamah": normalize_time(
                        values[header_map["Dhuhr Iqamah"]]
                    )
                },
                "asr": {
                    "athan": normalize_time(
                        values[header_map["Asr Adhaan"]]
                    ),
                    "iqamah": normalize_time(
                        values[header_map["Asr Iqamah"]]
                    )
                },
                "maghrib": {
                    "athan": normalize_time(
                        values[header_map["Maghrib Adhaan"]]
                    ),
                    "iqamah": normalize_time(
                        values[header_map["Maghrib Iqamah"]]
                    )
                },
                "isha": {
                    "athan": normalize_time(
                        values[header_map["Isha Adhaan"]]
                    ),
                    "iqamah": normalize_time(
                        values[header_map["Isha Iqamah"]]
                    )
                }
            }

    raise RuntimeError(
        f"NAMCC does not have a prayer-time row for day {TODAY_DAY}"
    )


def main():
    print("========================================")
    print("       MOSQUE PRAYER TIMES")
    print("========================================")
    print(f"Today: {TODAY.strftime('%Y-%m-%d')}")
    print(f"Date being searched: {TODAY_MONTH_DAY}")
    print()

    results = {}

    errors = []

    try:
        results["ICRR"] = get_icrr()
    except Exception as e:
        print(f"ICRR ERROR: {e}")
        errors.append(f"ICRR: {e}")

    try:
        results["NAMCC"] = get_namcc()
    except Exception as e:
        print(f"NAMCC ERROR: {e}")
        errors.append(f"NAMCC: {e}")

    print("\n========================================")
    print("FINAL JSON")
    print("========================================")

    print(json.dumps(results, indent=2))

    if errors:
        print("\n========================================")
        print("ERRORS")
        print("========================================")

        for error in errors:
            print(error)

        sys.exit(1)

    print("\n========================================")
    print("SUCCESS")
    print("========================================")


if __name__ == "__main__":
    main()
