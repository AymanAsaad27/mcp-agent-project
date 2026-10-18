
import random
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "data" / "shop.db"
DB.parent.mkdir(parents=True, exist_ok=True)

random.seed(42)

with sqlite3.connect(DB) as con:
    con.execute("PRAGMA foreign_keys = ON")

    con.executescript("""
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS products;
    DROP TABLE IF EXISTS customers;

    CREATE TABLE customers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        country TEXT NOT NULL,
        signup_date TEXT NOT NULL
    );

    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL CHECK(price >= 0)
    );

    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        product_id INTEGER NOT NULL REFERENCES products(id),
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        order_date TEXT NOT NULL
    );
    """)

    customers = [
        (1, "Alice Chen", "China", "2025-01-10"),
        (2, "Rahim Uddin", "Bangladesh", "2025-02-14"),
        (3, "John Smith", "USA", "2025-03-02"),
        (4, "Maria Lopez", "Spain", "2025-03-20"),
        (5, "Yuki Tanaka", "Japan", "2025-04-05"),
        (6, "Omar Hassan", "Egypt", "2025-05-18"),
    ]

    products = [
        (1, "Wireless Mouse", "Electronics", 19.99),
        (2, "Mechanical Keyboard", "Electronics", 74.50),
        (3, "Notebook Pack", "Stationery", 8.25),
        (4, "Desk Lamp", "Home", 32.00),
        (5, "USB-C Hub", "Electronics", 29.90),
        (6, "Water Bottle", "Home", 12.40),
    ]

    con.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?)", customers
    )
    con.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?)", products
    )

    orders = []
    for i in range(1, 61):
        month = random.randint(1, 9)
        day = random.randint(1, 28)
        orders.append((
            i,
            random.randint(1, 6),
            random.randint(1, 6),
            random.randint(1, 5),
            f"2026-{month:02d}-{day:02d}",
        ))

    con.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders
    )

print(f"Database created at: {DB}")
