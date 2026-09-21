import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import sys
import re


TODAY = datetime.now()

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


def get_icrr():
    print("\n=== ICRR ===")
    print("Looking for today's prayer times on ICRR homepage")

    soup = get_soup(ICRR_URL)

    text = soup.get_text(" ", strip=True)

    print(f"Page title: {soup.title.get_text(strip=True) if soup.title else 'Unknown'}")

    # Look for the prayer names in the page text.
    prayer_names = [
        "Fajr",
        "Sunrise",
        "Zuhr",
        "Asr",
        "Maghrib",
        "Isha",
    ]

    # Search tables first.
    tables = soup.find_all("table")

    print(f"Tables found: {len(tables)}")

    for table_number, table in enumerate(tables, start=1):

        rows = table.find_all("tr")

        if not rows:
            continue

        print(f"Inspecting ICRR table #{table_number}")

        for row in rows:

            cells = row.find_all(["td", "th"])

            values = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            if not values:
                continue

            row_text = " ".join(values)

            # We are looking for a row containing all five prayer names.
            if (
                "Fajr" in row_text
                and "Zuhr" in row_text
                and "Asr" in row_text
                and "Maghrib" in row_text
                and "Isha" in row_text
            ):
                print(f"Potential ICRR prayer row: {values}")

    # ------------------------------------------------------------------
    # ICRR's homepage currently renders today's prayer information as
    # individual text elements rather than the stale 7-day table.
    # Extract the prayer labels and nearby time strings from the DOM.
    # ------------------------------------------------------------------

    prayer_data = {}

    # Find all text-bearing elements.
    elements = soup.find_all(["div", "span", "p", "td", "li"])

    for element in elements:

        label = element.get_text(" ", strip=True)

        if label not in prayer_names:
            continue

        # Look at the immediate parent for the prayer's times.
        parent = element.parent

        if parent is None:
            continue

        parent_text = parent.get_text(" ", strip=True)

        # Extract times such as:
        # 5:17 AM
        # 5:50 AM
        times = re.findall(
            r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b",
            parent_text,
            flags=re.IGNORECASE
        )

        if times:
            print(
                f"ICRR {label}: "
                f"parent text={parent_text!r}, "
                f"times={times}"
            )

            prayer_data[label.lower()] = times

    required = ["fajr", "zuhr", "asr", "maghrib", "isha"]

    missing = [
        prayer
        for prayer in required
        if prayer not in prayer_data
    ]

    if missing:
        raise RuntimeError(
            "ICRR homepage did not provide today's times for: "
            + ", ".join(missing)
        )

    result = {}

    for prayer in required:

        times = prayer_data[prayer]

        if len(times) < 2:
            raise RuntimeError(
                f"ICRR {prayer} did not provide both Adhan and Iqamah: "
                f"{times}"
            )

        result_name = "dhuhr" if prayer == "zuhr" else prayer

        result[result_name] = {
            "athan": normalize_time(times[0]),
            "iqamah": normalize_time(times[1])
        }

    return result


def get_namcc():
    print("\n=== NAMCC ===")
    print(f"Looking for today's date: {TODAY.strftime('%d %b')}")

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

    target_date = TODAY.strftime("%d %b")

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
        f"NAMCC does not have a prayer-time row for {target_date}"
    )


def main():

    print("========================================")
    print("       MOSQUE PRAYER TIMES")
    print("========================================")

    print(f"Today: {TODAY.strftime('%Y-%m-%d')}")

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
    main()                    f"Row {row_number}: "
                    f"date=[{values[date_index]!r}] "
                    f"full_row={values}"
                )


def inspect_namcc():
    print("\n")
    print("========================================")
    print("NAMCC DATE DIAGNOSTIC")
    print("========================================")

    soup = get_soup(NAMCC_URL)
    tables = soup.find_all("table")

    print(f"Tables found: {len(tables)}")

    for table_number, table in enumerate(tables, start=1):
        rows = table.find_all("tr")

        if not rows:
            continue

        headers = [
            cell.get_text(" ", strip=True)
            for cell in rows[0].find_all(["th", "td"])
        ]

        print(f"\nTable #{table_number}")
        print(f"Headers: {headers}")

        if "Date" not in headers:
            continue

        date_index = headers.index("Date")

        print("\nDATE VALUES FOUND:")

        for row_number, row in enumerate(rows[1:], start=1):
            cells = row.find_all(["td", "th"])

            values = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            if len(values) > date_index:
                print(
                    f"Row {row_number}: "
                    f"date=[{values[date_index]!r}] "
                    f"full_row={values}"
                )


def main():
    print("========================================")
    print("       MOSQUE PRAYER TIMES")
    print("       DATE DIAGNOSTIC")
    print("========================================")

    print(f"Python date: {TODAY}")
    print(f"Month: {TODAY.month}")
    print(f"Day: {TODAY.day}")
    print(f"Formatted: {TODAY.strftime('%b %d')}")

    inspect_icrr()
    inspect_namcc()

    print("\n")
    print("========================================")
    print("DIAGNOSTIC COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()
