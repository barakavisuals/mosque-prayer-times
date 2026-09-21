import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import sys
import re


ICRR_URL = "https://roundrockmasjid.org/"
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
    value = value.strip()

    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            pass

    raise ValueError(f"Could not understand time: {value}")


def get_namcc():
    print("\n=== NAMCC ===")

    today = datetime.now()
    target_date = today.strftime("%d %b")

    print(f"Looking for: {target_date}")

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

        headers = [
            cell.get_text(" ", strip=True)
            for cell in rows[0].find_all(["th", "td"])
        ]

        if not all(column in headers for column in required_columns):
            continue

        print(f"Using NAMCC table #{table_number}")

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

            if row_date != target_date:
                continue

            print(f"Found NAMCC row: {values}")

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
        f"NAMCC does not have a prayer-time row for {target_date}"
    )


def inspect_icrr():
    print("\n=== ICRR DIAGNOSTIC ===")

    soup = get_soup(ICRR_URL)

    print(
        "Page title:",
        soup.title.get_text(strip=True)
        if soup.title
        else "Unknown"
    )

    text = soup.get_text(" ", strip=True)

    print("\nPrayer-related text found on homepage:")

    keywords = [
        "Fajr",
        "Sunrise",
        "Zuhr",
        "Dhuhr",
        "Asr",
        "Maghrib",
        "Isha",
        "Iqamah",
        "Adhan",
        "Athan",
    ]

    for keyword in keywords:

        matches = re.findall(
            rf".{{0,100}}{keyword}.{{0,200}}",
            text,
            flags=re.IGNORECASE
        )

        if matches:
            print(f"\n--- {keyword} ---")

            for match in matches[:10]:
                print(match)

    print("\nTables on ICRR homepage:")

    tables = soup.find_all("table")

    print(f"Found {len(tables)} table(s)")

    for table_number, table in enumerate(tables, start=1):

        rows = table.find_all("tr")

        print(f"\nTable #{table_number}")

        for row in rows[:10]:

            cells = row.find_all(["td", "th"])

            values = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            if values:
                print(values)


def main():

    print("========================================")
    print("       MOSQUE PRAYER TIMES")
    print("========================================")

    today = datetime.now()

    print(f"Today: {today.strftime('%Y-%m-%d')}")
    print()

    results = {}
    errors = []

    # ---------------------------------------------------------
    # NAMCC
    # ---------------------------------------------------------

    try:
        results["NAMCC"] = get_namcc()

    except Exception as e:
        print(f"NAMCC ERROR: {e}")
        errors.append(f"NAMCC: {e}")

    # ---------------------------------------------------------
    # ICRR
    # ---------------------------------------------------------

    try:
        inspect_icrr()

    except Exception as e:
        print(f"ICRR ERROR: {e}")
        errors.append(f"ICRR: {e}")

    # ---------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------

    print("\n========================================")
    print("NAMCC RESULT")
    print("========================================")

    print(
        json.dumps(
            results.get("NAMCC", {}),
            indent=2
        )
    )

    print("\n========================================")
    print("NEXT STEP")
    print("========================================")

    print(
        "NAMCC is being parsed automatically."
    )

    print(
        "ICRR is currently diagnostic-only so we can identify "
        "the exact homepage structure before building its parser."
    )

    # Do NOT fail the workflow yet.
    # We want to see the ICRR diagnostic output.

    print("\n========================================")
    print("COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()
