import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from zoneinfo import ZoneInfo
import json
import re


CENTRAL = ZoneInfo("America/Chicago")


# ============================================================
# GENERAL HELPERS
# ============================================================

def get_today():
    return datetime.now(CENTRAL)


def parse_time(value):
    """Convert a time such as 5:58 AM to 24-hour HH:MM."""
    if value is None:
        raise ValueError("Missing time value")

    value = str(value).strip().upper()

    # Remove seconds if present
    value = re.sub(r"(\d{1,2}:\d{2}):\d{2}", r"\1", value)

    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            pass

    raise ValueError(f"Could not parse time: {value}")


def extract_times(text):
    """Return all times found in a text string."""
    if not text:
        return []

    return re.findall(
        r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b",
        text.upper()
    )


def normalize_key(value):
    """Normalize JSON/table field names for easier matching."""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def parse_date_value(value, default_year=None, default_month=None):
    """
    Try to convert many possible date formats into a Python date.
    Used primarily for the ICP API.
    """

    if value is None:
        return None

    if isinstance(value, dict):
        # Common API structure:
        # {"date": "..."}
        for key in ("date", "value", "datetime"):
            if key in value:
                result = parse_date_value(
                    value[key],
                    default_year,
                    default_month
                )
                if result:
                    return result

        return None

    text = str(value).strip()

    # YYYY-MM-DD
    match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    if match:
        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3))
            )
        except ValueError:
            pass

    # MM/DD/YYYY
    match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text)
    if match:
        try:
            return date(
                int(match.group(3)),
                int(match.group(1)),
                int(match.group(2))
            )
        except ValueError:
            pass

    # YYYY/MM/DD
    match = re.search(r"\b(\d{4})/(\d{1,2})/(\d{1,2})\b", text)
    if match:
        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3))
            )
        except ValueError:
            pass

    # Formats such as:
    # September 21
    # Sep 21
    if default_year:
        for fmt in ("%B %d", "%b %d"):
            try:
                parsed = datetime.strptime(text, fmt)
                return date(
                    default_year,
                    parsed.month,
                    parsed.day
                )
            except ValueError:
                pass

    return None


def find_date_in_entry(entry, year, month):
    """
    Search a JSON object for a field containing its date.
    """
    if not isinstance(entry, dict):
        return None

    # Prefer fields that are obviously date fields.
    preferred_keys = [
        "date",
        "day",
        "datetime",
        "date_time",
        "prayer_date",
        "gregorian_date",
    ]

    for preferred in preferred_keys:
        for key, value in entry.items():
            if normalize_key(key) == normalize_key(preferred):
                parsed = parse_date_value(
                    value,
                    default_year=year,
                    default_month=month
                )
                if parsed:
                    return parsed

    # Fallback: inspect all values.
    for value in entry.values():
        parsed = parse_date_value(
            value,
            default_year=year,
            default_month=month
        )
        if parsed:
            return parsed

    return None


def find_prayer_time(entry, aliases):
    """
    Find a prayer's Athan/start time in a JSON entry.

    We deliberately ignore fields containing:
      - iqama
      - sunrise
      - sunset

    This allows this function to work with slightly different
    versions of the Masjidi API field names.
    """

    if not isinstance(entry, dict):
        return None

    candidates = []

    for key, value in entry.items():
        normalized = normalize_key(key)

        if not any(alias in normalized for alias in aliases):
            continue

        if "iqama" in normalized:
            continue

        if "sunrise" in normalized:
            continue

        if "sunset" in normalized:
            continue

        try:
            parsed = parse_time(value)
            candidates.append((key, parsed))
        except (ValueError, TypeError):
            continue

    if candidates:
        return candidates[0][1]

    return None


def find_iqama_time(entry, aliases):
    """
    Find an Iqamah time in an ICP iqama schedule entry.
    """

    if not isinstance(entry, dict):
        return None

    for key, value in entry.items():
        normalized = normalize_key(key)

        if "iqama" not in normalized:
            continue

        if not any(alias in normalized for alias in aliases):
            continue

        try:
            return parse_time(value)
        except (ValueError, TypeError):
            continue

    return None


# ============================================================
# NAMCC
# ============================================================

def get_namcc():
    now = get_today()

    url = "https://namcc.org/monthly-prayer-times/"

    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    target_date = now.date()

    for table in soup.find_all("table"):

        rows = table.find_all("tr")

        if not rows:
            continue

        headers = [
            cell.get_text(" ", strip=True).lower()
            for cell in rows[0].find_all(["th", "td"])
        ]

        # We need the NAMCC monthly prayer table.
        if not any("fajr" in header for header in headers):
            continue

        if not any("maghrib" in header for header in headers):
            continue

        header_map = {}

        for index, header in enumerate(headers):
            header_map[header] = index

        for row in rows[1:]:
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["th", "td"])
            ]

            if len(cells) < len(headers):
                continue

            row_date_text = cells[0]

            # Example:
            # 21 Sep
            # 21 Sep 2026
            if not re.search(
                rf"\b{target_date.day:02d}\b|\b{target_date.day}\b",
                row_date_text
            ):
                continue

            if target_date.strftime("%b").lower() not in row_date_text.lower():
                continue

            def get_column(*possible_names):
                for name in possible_names:
                    for header, index in header_map.items():
                        if name in header:
                            return cells[index]
                return None

            return {
                "fajr": {
                    "athan": parse_time(
                        get_column("fajr adhaan", "fajr athan")
                    ),
                    "iqamah": parse_time(
                        get_column("fajr iqamah")
                    ),
                },
                "dhuhr": {
                    "athan": parse_time(
                        get_column("dhuhr adhaan", "dhuhr athan")
                    ),
                    "iqamah": parse_time(
                        get_column("dhuhr iqamah")
                    ),
                },
                "asr": {
                    "athan": parse_time(
                        get_column("asr adhaan", "asr athan")
                    ),
                    "iqamah": parse_time(
                        get_column("asr iqamah")
                    ),
                },
                "maghrib": {
                    "athan": parse_time(
                        get_column("maghrib adhaan", "maghrib athan")
                    ),
                    "iqamah": parse_time(
                        get_column("maghrib iqamah")
                    ),
                },
                "isha": {
                    "athan": parse_time(
                        get_column("isha adhaan", "isha athan")
                    ),
                    "iqamah": parse_time(
                        get_column("isha iqamah")
                    ),
                },
            }

    raise RuntimeError(
        f"NAMCC: could not find today's row ({target_date})"
    )


# ============================================================
# ICRR
# ============================================================

def get_icrr():
    now = get_today()

    url = "https://ourmasajid.com/m/icrr/prayer-times"

    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    target_date = now.date()

    for table in soup.find_all("table"):

        rows = table.find_all("tr")

        if len(rows) < 2:
            continue

        headers = [
            cell.get_text(" ", strip=True).lower()
            for cell in rows[0].find_all(["th", "td"])
        ]

        required_headers = [
            "date",
            "fajr",
            "dhuhr",
            "asr",
            "maghrib",
            "isha",
        ]

        if not all(
            any(required in header for header in headers)
            for required in required_headers
        ):
            continue

        for row in rows[1:]:
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["th", "td"])
            ]

            if len(cells) < 7:
                continue

            date_text = cells[0]

            # Match month and day.
            month_match = target_date.strftime("%b").lower()
            if month_match not in date_text.lower():
                continue

            if not re.search(
                rf"\b{target_date.day}\b",
                date_text
            ):
                continue

            # Columns:
            # Date | Fajr | Sunrise | Dhuhr | Asr | Maghrib | Isha

            fajr_times = extract_times(cells[1])
            dhuhr_times = extract_times(cells[3])
            asr_times = extract_times(cells[4])
            maghrib_times = extract_times(cells[5])
            isha_times = extract_times(cells[6])

            if not all([
                len(fajr_times) >= 2,
                len(dhuhr_times) >= 2,
                len(asr_times) >= 2,
                len(maghrib_times) >= 2,
                len(isha_times) >= 2,
            ]):
                raise RuntimeError(
                    "ICRR: found today's row but could not parse "
                    "all Athan/Iqamah times"
                )

            return {
                "fajr": {
                    "athan": parse_time(fajr_times[0]),
                    "iqamah": parse_time(fajr_times[1]),
                },
                "dhuhr": {
                    "athan": parse_time(dhuhr_times[0]),
                    "iqamah": parse_time(dhuhr_times[1]),
                },
                "asr": {
                    "athan": parse_time(asr_times[0]),
                    "iqamah": parse_time(asr_times[1]),
                },
                "maghrib": {
                    "athan": parse_time(maghrib_times[0]),
                    "iqamah": parse_time(maghrib_times[1]),
                },
                "isha": {
                    "athan": parse_time(isha_times[0]),
                    "iqamah": parse_time(isha_times[1]),
                },
            }

    raise RuntimeError(
        f"ICRR: could not find today's row ({target_date})"
    )


# ============================================================
# ICP
# ============================================================

def get_icp():
    now = get_today()
    today = now.date()

    url = (
        "https://ummahsoft.org/salahtime/api/masjidi/v1/index.php/"
        f"masjids/50001/iqamahandprayertimes/"
        f"{now.year}/{now.month}"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.5 Safari/605.1.15"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.masjidiapp.com/",
        "Origin": "https://www.masjidiapp.com",
    }

    params = {
        "XDEBUG_SESSION_START": "PHPSTORM"
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    # --------------------------------------------------------
    # STEP 1:
    # Find today's DAILY prayer row.
    #
    # This contains the changing Athan times.
    # --------------------------------------------------------

    prayer_times = data.get("prayerTimes", [])

    if not isinstance(prayer_times, list):
        raise RuntimeError(
            "ICP: prayerTimes was not returned as a list"
        )

    daily_entry = None

    print(
        "ICP API prayerTimes entries:",
        len(prayer_times)
    )

    for entry in prayer_times:

        if not isinstance(entry, dict):
            continue

        entry_date = find_date_in_entry(
            entry,
            now.year,
            now.month
        )

        if entry_date == today:
            daily_entry = entry
            break

    if daily_entry is None:

        print(
            "ICP: Could not find today's prayerTimes row."
        )

        if prayer_times:
            print(
                "ICP first prayerTimes entry:",
                json.dumps(
                    prayer_times[0],
                    indent=2,
                    default=str
                )
            )

        raise RuntimeError(
            f"ICP: could not find today's daily prayer row ({today})"
        )

    print(
        "ICP matched daily prayer row for:",
        today
    )

    # Extract Athan times from the daily row.
    fajr_athan = find_prayer_time(
        daily_entry,
        ["fajr"]
    )

    dhuhr_athan = find_prayer_time(
        daily_entry,
        ["dhuhr", "zuhr"]
    )

    asr_athan = find_prayer_time(
        daily_entry,
        ["asr"]
    )

    maghrib_athan = find_prayer_time(
        daily_entry,
        ["maghrib", "magrib"]
    )

    isha_athan = find_prayer_time(
        daily_entry,
        ["isha"]
    )

    athan_times = {
        "fajr": fajr_athan,
        "dhuhr": dhuhr_athan,
        "asr": asr_athan,
        "maghrib": maghrib_athan,
        "isha": isha_athan,
    }

    missing_athan = [
        prayer
        for prayer, value in athan_times.items()
        if value is None
    ]

    if missing_athan:
        print(
            "ICP daily row:",
            json.dumps(
                daily_entry,
                indent=2,
                default=str
            )
        )

        raise RuntimeError(
            "ICP: could not extract Athan time(s): "
            + ", ".join(missing_athan)
        )

    # --------------------------------------------------------
    # STEP 2:
    # Find the MOST RECENT Iqamah schedule whose effective
    # date is <= today.
    #
    # Example:
    #
    # Sept 1 schedule -> applies Sept 1-5
    # Sept 6 schedule -> applies Sept 6-12
    # Sept 13 schedule -> applies Sept 13-19
    # Sept 20 schedule -> applies Sept 20-26
    # Sept 27 schedule -> applies Sept 27 onward
    # --------------------------------------------------------

    iqama_times = data.get("iqamaTimes", [])

    if not isinstance(iqama_times, list):
        raise RuntimeError(
            "ICP: iqamaTimes was not returned as a list"
        )

    print(
        "ICP API iqamaTimes entries:",
        len(iqama_times)
    )

    selected_iqama_entry = None
    selected_iqama_date = None

    for entry in iqama_times:

        if not isinstance(entry, dict):
            continue

        raw_date = entry.get("date")

        if isinstance(raw_date, dict):
            raw_date = raw_date.get(
                "date",
                raw_date.get("value", "")
            )

        entry_date = parse_date_value(
            raw_date,
            default_year=now.year,
            default_month=now.month
        )

        print(
            "ICP API iqama schedule date:",
            repr(raw_date),
            "=>",
            entry_date
        )

        if entry_date is None:
            continue

        # We want the latest schedule that has already started.
        if entry_date <= today:

            if (
                selected_iqama_date is None
                or entry_date > selected_iqama_date
            ):
                selected_iqama_date = entry_date
                selected_iqama_entry = entry

    if selected_iqama_entry is None:
        raise RuntimeError(
            f"ICP: could not find an Iqamah schedule effective "
            f"on or before {today}"
        )

    print(
        "ICP selected Iqamah schedule:",
        selected_iqama_date
    )

    # --------------------------------------------------------
    # STEP 3:
    # Extract Iqamah times from the selected schedule.
    # --------------------------------------------------------

    fajr_iqamah = find_iqama_time(
        selected_iqama_entry,
        ["fajr"]
    )

    dhuhr_iqamah = find_iqama_time(
        selected_iqama_entry,
        ["dhuhr", "zuhr"]
    )

    asr_iqamah = find_iqama_time(
        selected_iqama_entry,
        ["asr"]
    )

    maghrib_iqamah = find_iqama_time(
        selected_iqama_entry,
        ["maghrib", "magrib"]
    )

    isha_iqamah = find_iqama_time(
        selected_iqama_entry,
        ["isha"]
    )

    iqamah_times_result = {
        "fajr": fajr_iqamah,
        "dhuhr": dhuhr_iqamah,
        "asr": asr_iqamah,
        "maghrib": maghrib_iqamah,
        "isha": isha_iqamah,
    }

    missing_iqamah = [
        prayer
        for prayer, value in iqamah_times_result.items()
        if value is None
    ]

    if missing_iqamah:

        print(
            "ICP selected Iqamah entry:",
            json.dumps(
                selected_iqama_entry,
                indent=2,
                default=str
            )
        )

        raise RuntimeError(
            "ICP: could not extract Iqamah time(s): "
            + ", ".join(missing_iqamah)
        )

    # --------------------------------------------------------
    # STEP 4:
    # Combine the DAILY Athan times with the EFFECTIVE
    # Iqamah schedule.
    # --------------------------------------------------------

    result = {
        "fajr": {
            "athan": fajr_athan,
            "iqamah": fajr_iqamah,
        },
        "dhuhr": {
            "athan": dhuhr_athan,
            "iqamah": dhuhr_iqamah,
        },
        "asr": {
            "athan": asr_athan,
            "iqamah": asr_iqamah,
        },
        "maghrib": {
            "athan": maghrib_athan,
            "iqamah": maghrib_iqamah,
        },
        "isha": {
            "athan": isha_athan,
            "iqamah": isha_iqamah,
        },
    }

    print(
        "ICP combined prayer times:",
        json.dumps(result, indent=2)
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    now = get_today()

    print("Date:", now.strftime("%Y-%m-%d"))
    print(
        "Timezone:",
        now.tzname()
    )

    results = {}

    # --------------------------------------------------------
    # NAMCC
    # --------------------------------------------------------

    try:
        results["NAMCC"] = get_namcc()
        print("\nNAMCC: SUCCESS")
    except Exception as e:
        results["NAMCC"] = None
        print("\nNAMCC ERROR:", e)

    # --------------------------------------------------------
    # ICRR
    # --------------------------------------------------------

    try:
        results["ICRR"] = get_icrr()
        print("ICRR: SUCCESS")
    except Exception as e:
        results["ICRR"] = None
        print("ICRR ERROR:", e)

    # --------------------------------------------------------
    # ICP
    # --------------------------------------------------------

    try:
        results["ICP"] = get_icp()
        print("ICP: SUCCESS")
    except Exception as e:
        results["ICP"] = None
        print("ICP ERROR:", e)

    # --------------------------------------------------------
    # FINAL JSON
    # --------------------------------------------------------

    output = {
        "date": now.strftime("%Y-%m-%d"),
        "NAMCC": results.get("NAMCC"),
        "ICRR": results.get("ICRR"),
        "ICP": results.get("ICP"),
    }

    with open(
        "prayer_times.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("\nFinal prayer_times.json:")
    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
