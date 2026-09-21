import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

TODAY = datetime.now().strftime("%Y-%m-%d")

URLS = {
    "ICRR": "https://roundrockmasjid.org/prayer-times",
    "NAMCC": "https://namcc.org/monthly-prayer-times/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


def get_page(name, url):
    print("\n" + "=" * 80)
    print(f"{name} - FETCH")
    print("=" * 80)

    response = requests.get(
        url,
        timeout=30,
        headers=HEADERS
    )

    print("URL:", url)
    print("HTTP STATUS:", response.status_code)
    print("CONTENT TYPE:", response.headers.get("content-type"))
    print("CONTENT LENGTH:", len(response.text))

    response.raise_for_status()

    return response.text


def inspect_page(name, html):
    print("\n" + "=" * 80)
    print(f"{name} - PAGE INSPECTION")
    print("=" * 80)

    soup = BeautifulSoup(html, "html.parser")

    # --------------------------------------------------
    # TITLE
    # --------------------------------------------------

    print("\nPAGE TITLE:")
    print(soup.title.get_text(" ", strip=True) if soup.title else "NO TITLE")

    # --------------------------------------------------
    # TABLES
    # --------------------------------------------------

    tables = soup.find_all("table")

    print("\nTABLE COUNT:", len(tables))

    for i, table in enumerate(tables, 1):

        print("\n--- TABLE", i, "---")

        rows = table.find_all("tr")

        print("ROW COUNT:", len(rows))

        for row in rows[:15]:

            cells = [
                " ".join(cell.get_text(" ", strip=True).split())
                for cell in row.find_all(["td", "th"])
            ]

            print(cells)

    # --------------------------------------------------
    # PRAYER WORDS
    # --------------------------------------------------

    text = " ".join(soup.stripped_strings)

    print("\nPRAYER WORD SEARCH:")

    for word in [
        "Fajr",
        "Dhuhr",
        "Zuhr",
        "Asr",
        "Maghrib",
        "Isha",
        "Iqamah",
        "Adhaan",
        "Adhan",
        "Athan",
    ]:

        matches = len(
            re.findall(
                re.escape(word),
                text,
                re.IGNORECASE
            )
        )

        print(f"{word}: {matches}")

    # --------------------------------------------------
    # TIME STRINGS
    # --------------------------------------------------

    times = re.findall(
        r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b",
        text,
        re.IGNORECASE
    )

    print("\nTIME STRINGS FOUND:", len(times))

    print(times[:100])

    # --------------------------------------------------
    # SCRIPT TAGS
    # --------------------------------------------------

    scripts = soup.find_all("script")

    print("\nSCRIPT TAG COUNT:", len(scripts))

    for i, script in enumerate(scripts):

        script_text = script.string or script.get_text()

        if not script_text:
            continue

        interesting = any(
            word.lower() in script_text.lower()
            for word in [
                "fajr",
                "dhuhr",
                "zuhr",
                "asr",
                "maghrib",
                "isha",
                "iqamah",
                "athan",
                "prayer",
                "api",
            ]
        )

        if interesting:

            print("\n--- INTERESTING SCRIPT", i, "---")

            print(script_text[:5000])

    # --------------------------------------------------
    # LINKS
    # --------------------------------------------------

    print("\nLINKS CONTAINING PRAYER/TIME/MONTH:")

    for link in soup.find_all("a", href=True):

        href = link.get("href", "")
        label = " ".join(link.stripped_strings)

        combined = f"{label} {href}".lower()

        if any(
            word in combined
            for word in [
                "prayer",
                "times",
                "monthly",
                "calendar",
                "api",
            ]
        ):

            print(
                "LABEL:",
                label,
                "| HREF:",
                href
            )


def main():

    print("=" * 80)
    print("MOSQUE PRAYER TIME DIAGNOSTIC")
    print("DATE:", TODAY)
    print("=" * 80)

    for name, url in URLS.items():

        try:

            html = get_page(name, url)

            inspect_page(name, html)

        except Exception as e:

            print("\nERROR:", repr(e))

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
