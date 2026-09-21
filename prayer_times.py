import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import sys
import re


def parse_time(value):
    """Convert 12-hour time such as '06:14 AM' to HH:MM."""
    return datetime.strptime(value.strip(), "%I:%M %p").strftime("%H:%M")


def get_namcc():
    url = "https://namcc.org/prayer-times"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    today = datetime.now().strftime("%d %b")
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")

        for row in rows:
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]

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

    raise RuntimeError(f"NAMCC: could not find today's row ({today})")


def get_icrr():
    """
    ICRR schedule is published through Our Masajid.
    """
    url = "https://ourmasajid.com/m/icrr/prayer-times"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    today = datetime.now().strftime("%Y-%m-%d")

    # Look through tables for today's row.
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [
                c.get_text(" ", strip=True)
                for c in row.find_all(["th", "td"])
            ]

            if not cells:
                continue

            text = " ".join(cells)

            # Look for today's date in several possible formats.
            if (
                datetime.now().strftime("%b %-d") in text
                or datetime.now().strftime("%B %-d") in text
                or datetime.now().strftime("%m/%d/%Y") in text
                or today in text
            ):
                times = re.findall(
                    r"\d{1,2}:\d{2}\s*(?:AM|PM)",
                    text,
                    re.IGNORECASE,
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

    # If the page structure changes, print useful diagnostic information.
    raise RuntimeError("ICRR: could not find today's prayer times")


def main():
    print("=== MOSQUE PRAYER TIMES ===")
    print("Date:", datetime.now().strftime("%Y-%m-%d"))
    print()

    namcc = get_namcc()
    icrr = get_icrr()

    print("=== NAMCC ===")
    print(json.dumps(namcc, indent=2))
    print()

    print("=== ICRR ===")
    print(json.dumps(icrr, indent=2))
    print()

    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "NAMCC": namcc,
        "ICRR": icrr,
    }

    print("=== FINAL JSON ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1)        rows = table.find_all("tr")

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
