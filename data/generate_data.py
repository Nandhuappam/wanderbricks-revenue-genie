"""Generate a synthetic Wanderbricks-style travel-booking dataset (5 tables).

The schema mirrors samples.wanderbricks so that the same Gold views, Genie
instructions and benchmark questions work against either source.

A small, controlled amount of "dirty" data is injected on purpose, so the
Gold-layer cleanup rules can be demonstrated and tested:
  * mixed-case / padded status values (" Confirmed", "CONFIRMED")
  * duplicate booking rows (same booking_id, older updated_at)
  * check_out <= check_in
  * null and negative total_amount

All names, emails and phone numbers are fake (example.com domain).

Usage:  python generate_data.py            # writes CSVs next to this file
"""

import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 42
N_HOSTS, N_PROPERTIES, N_USERS, N_BOOKINGS = 200, 600, 2000, 10000
START, END = date(2025, 1, 1), date(2026, 11, 23)
OUT = Path(__file__).parent / "csv"

rng = random.Random(SEED)

DESTINATIONS = [
    # destination, country, state_or_province, code, nightly price factor
    ("Paris", "France", "Ile-de-France", "IDF", 1.5),
    ("Nice", "France", "Provence-Alpes-Cote d'Azur", "PAC", 1.3),
    ("London", "United Kingdom", "England", "ENG", 1.6),
    ("Edinburgh", "United Kingdom", "Scotland", "SCT", 1.1),
    ("Barcelona", "Spain", "Catalonia", "CT", 1.2),
    ("Madrid", "Spain", "Community of Madrid", "MD", 1.0),
    ("Rome", "Italy", "Lazio", "LAZ", 1.2),
    ("Florence", "Italy", "Tuscany", "TOS", 1.3),
    ("Lisbon", "Portugal", "Lisbon", "LIS", 0.9),
    ("Amsterdam", "Netherlands", "North Holland", "NH", 1.4),
    ("Berlin", "Germany", "Berlin", "BE", 1.0),
    ("Munich", "Germany", "Bavaria", "BY", 1.1),
    ("New York", "United States", "New York", "NY", 1.8),
    ("Miami", "United States", "Florida", "FL", 1.4),
    ("San Francisco", "United States", "California", "CA", 1.7),
    ("Austin", "United States", "Texas", "TX", 1.0),
    ("Toronto", "Canada", "Ontario", "ON", 1.1),
    ("Vancouver", "Canada", "British Columbia", "BC", 1.2),
    ("Mexico City", "Mexico", "Mexico City", "CMX", 0.7),
    ("Cancun", "Mexico", "Quintana Roo", "ROO", 1.0),
    ("Tokyo", "Japan", "Tokyo", "13", 1.4),
    ("Kyoto", "Japan", "Kyoto", "26", 1.2),
    ("Bangkok", "Thailand", "Bangkok", "10", 0.6),
    ("Phuket", "Thailand", "Phuket", "83", 0.8),
    ("Bali", "Indonesia", "Bali", "BA", 0.7),
    ("Singapore", "Singapore", "Central Region", "01", 1.5),
    ("Dubai", "United Arab Emirates", "Dubai", "DU", 1.6),
    ("Goa", "India", "Goa", "GA", 0.5),
    ("Kochi", "India", "Kerala", "KL", 0.4),
    ("Sydney", "Australia", "New South Wales", "NSW", 1.5),
]

PROPERTY_TYPES = [  # type, weight, base price, bedrooms range, max guests per bedroom
    ("apartment", 40, 110, (1, 3), 2),
    ("house", 20, 180, (2, 5), 2),
    ("villa", 8, 380, (3, 6), 2),
    ("condo", 12, 130, (1, 3), 2),
    ("cabin", 6, 140, (1, 3), 2),
    ("studio", 10, 80, (1, 1), 2),
    ("loft", 4, 160, (1, 2), 2),
]

FIRST = ["Aarav", "Maya", "Liam", "Sofia", "Noah", "Aisha", "Lucas", "Emma", "Ravi", "Chen",
         "Yuki", "Mateo", "Olivia", "Arjun", "Fatima", "Hugo", "Lea", "Diego", "Anya", "Kai",
         "Priya", "Jonas", "Zara", "Omar", "Nina", "Leo", "Isla", "Ethan", "Meera", "Sami"]
LAST = ["Sharma", "Garcia", "Muller", "Rossi", "Smith", "Tanaka", "Silva", "Martin", "Nair",
        "Kim", "Dubois", "Lopez", "Brown", "Wang", "Khan", "Novak", "Jensen", "Costa", "Ali", "Menon"]
USER_COUNTRIES = ["United States", "United Kingdom", "Germany", "France", "India", "Canada",
                  "Australia", "Japan", "Spain", "Italy", "Netherlands", "Singapore", "Brazil"]
COMPANIES = ["Acme Corp", "Globex", "Initech", "Umbrella Travel", "Stark Industries", "Wayne Enterprises",
             "Hooli", "Vandelay Imports", "Soylent", "Contoso", "Northwind", "Fabrikam"]
ADJ = ["Cozy", "Sunny", "Modern", "Charming", "Spacious", "Quiet", "Stylish", "Bright", "Rustic", "Luxury"]


def rand_date(a: date, b: date) -> date:
    return a + timedelta(days=rng.randint(0, (b - a).days))


def rand_ts(a: date, b: date) -> datetime:
    d = rand_date(a, b)
    return datetime(d.year, d.month, d.day, rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59))


def person():
    f, l = rng.choice(FIRST), rng.choice(LAST)
    return f"{f} {l}", f"{f.lower()}.{l.lower()}{rng.randint(1, 999)}@example.com"


def season_factor(d: date) -> float:
    return {6: 1.3, 7: 1.4, 8: 1.35, 12: 1.25, 1: 0.85, 2: 0.8, 11: 0.9}.get(d.month, 1.0)


def write(name, header, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name:<13} {len(rows):>6} rows")


def main():
    print(f"Writing CSVs to {OUT}")

    # destinations
    dest_rows = []
    for i, (name, country, region, code, _) in enumerate(DESTINATIONS, start=1):
        desc = f"## {name}\nPopular {country} destination in {region}. Known for food, culture and transport links."
        dest_rows.append([i, name, country, region, code, desc])
    write("destinations", ["destination_id", "destination", "country", "state_or_province",
                           "state_or_province_code", "description"], dest_rows)

    # hosts
    host_rows = []
    for hid in range(1, N_HOSTS + 1):
        name, email = person()
        phone = f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"
        rating = round(min(5.0, max(1.0, rng.gauss(4.4, 0.45))), 1)
        host_rows.append([hid, name, email, phone, rng.random() < 0.75, rng.random() < 0.92,
                          rating, rng.choice(USER_COUNTRIES), rand_date(date(2018, 1, 1), date(2024, 12, 31))])
    write("hosts", ["host_id", "name", "email", "phone", "is_verified", "is_active",
                    "rating", "country", "joined_at"], host_rows)

    # properties
    prop_rows, prop_info = [], {}
    types, weights = [t[0] for t in PROPERTY_TYPES], [t[1] for t in PROPERTY_TYPES]
    spec = {t[0]: t for t in PROPERTY_TYPES}
    for pid in range(1, N_PROPERTIES + 1):
        ptype = rng.choices(types, weights)[0]
        _, _, base, (bmin, bmax), gpb = spec[ptype]
        did = rng.randint(1, len(DESTINATIONS))
        dname, *_, factor = DESTINATIONS[did - 1]
        bedrooms = rng.randint(bmin, bmax)
        price = round(base * factor * rng.uniform(0.8, 1.25), 2)
        max_guests = max(1, bedrooms * gpb)
        title = f"{rng.choice(ADJ)} {ptype} in {dname}"
        prop_rows.append([pid, rng.randint(1, N_HOSTS), did, title,
                          f"A {title.lower()} with {bedrooms} bedroom(s).", price, ptype, max_guests,
                          bedrooms, max(1, bedrooms - rng.randint(0, 1)),
                          round(rng.uniform(-40, 60), 6), round(rng.uniform(-120, 150), 6),
                          rand_ts(date(2022, 1, 1), date(2024, 12, 31))])
        prop_info[pid] = (price, max_guests)
    write("properties", ["property_id", "host_id", "destination_id", "title", "description", "base_price",
                         "property_type", "max_guests", "bedrooms", "bathrooms",
                         "property_latitude", "property_longitude", "created_at"], prop_rows)

    # users
    user_rows = []
    for uid in range(1, N_USERS + 1):
        name, email = person()
        is_biz = rng.random() < 0.18
        user_rows.append([uid, email, name, rng.choice(USER_COUNTRIES),
                          "business" if is_biz else "individual",
                          rand_ts(date(2022, 1, 1), date(2026, 10, 31)), is_biz,
                          rng.choice(COMPANIES) if is_biz else ""])
    write("users", ["user_id", "email", "name", "country", "user_type", "created_at",
                    "is_business", "company_name"], user_rows)

    # bookings
    status_pool = ["confirmed"] * 72 + ["pending"] * 10 + ["cancelled"] * 18
    rows = []
    for bid in range(1, N_BOOKINGS + 1):
        pid = rng.randint(1, N_PROPERTIES)
        price, max_guests = prop_info[pid]
        check_in = rand_date(START, END + timedelta(days=60))
        nights = rng.choices([1, 2, 3, 4, 5, 6, 7, 10, 14], [8, 18, 20, 15, 12, 8, 10, 5, 4])[0]
        check_out = check_in + timedelta(days=nights)
        created = rand_ts(max(START - timedelta(days=30), check_in - timedelta(days=120)),
                          min(check_in, END))
        updated = created + timedelta(hours=rng.randint(0, 72))
        amount = round(price * nights * season_factor(check_in) * rng.uniform(0.95, 1.1), 2)
        status = rng.choice(status_pool)
        if check_in > END and status == "confirmed":
            status = "pending" if rng.random() < 0.5 else "confirmed"
        rows.append([bid, rng.randint(1, N_USERS), pid, check_in, check_out,
                     rng.randint(1, max_guests), amount, status, created, updated])

    # ---- inject controlled dirty data ----
    dirty = rng.sample(range(len(rows)), 300)
    for i in dirty[:150]:                       # messy status casing / whitespace
        rows[i][7] = rng.choice([" Confirmed", "CONFIRMED", "confirmed ", "Pending", "CANCELLED"])
    for i in dirty[150:190]:                    # check_out <= check_in
        rows[i][4] = rows[i][3]
    for i in dirty[190:210]:                    # null amount
        rows[i][6] = ""
    for i in dirty[210:225]:                    # negative amount
        rows[i][6] = -abs(rows[i][6])
    for i in dirty[225:300]:                    # duplicates (older version of the row)
        dup = list(rows[i])
        dup[7] = "pending"
        dup[9] = rows[i][9] - timedelta(hours=rng.randint(1, 48))
        rows.append(dup)
    rng.shuffle(rows)

    write("bookings", ["booking_id", "user_id", "property_id", "check_in", "check_out", "guests_count",
                       "total_amount", "status", "created_at", "updated_at"], rows)
    print("Done. Injected dirty rows: 150 status, 40 bad dates, 20 null, 15 negative, 75 duplicates.")


if __name__ == "__main__":
    main()
