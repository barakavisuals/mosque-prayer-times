import requests
from bs4 import BeautifulSoup
from datetime import datetime


TODAY = datetime.now()

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


def inspect_icrr():
    print("\n")
    print("========================================")
    print("ICRR DATE DIAGNOSTIC")
    print("========================================")

    soup = get_soup(ICRR_URL)
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
