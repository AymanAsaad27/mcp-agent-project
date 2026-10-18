
from pathlib import Path
import uuid

import pytest

from servers.sqlite_server import (
    describe_table,
    list_tables,
    query_database,
    validate_select,
)
from servers.files_server import (
    WORKSPACE,
    list_files,
    read_file,
    resolve_workspace_path,
    write_file,
)
from servers.weather_server import get_weather


# -------------------------
# SQLite server tests
# -------------------------

def test_list_tables():
    result = list_tables()

    assert set(result["tables"]) >= {
        "customers",
        "products",
        "orders",
    }


def test_describe_products_table():
    result = describe_table("products")

    assert result["table"] == "products"
    column_names = {column["name"] for column in result["columns"]}
    assert {"id", "name", "category", "price"} <= column_names


def test_query_order_count():
    result = query_database(
        "SELECT COUNT(*) AS total FROM orders"
    )

    assert result["row_count"] == 1
    assert result["rows"][0]["total"] == 60


def test_query_products_in_price_order():
    result = query_database(
        "SELECT name, price FROM products ORDER BY price DESC"
    )

    prices = [row["price"] for row in result["rows"]]

    assert prices == sorted(prices, reverse=True)
    assert result["rows"][0]["name"] == "Mechanical Keyboard"


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "DELETE FROM products",
        "UPDATE products SET price = 0",
        "DROP TABLE products",
        "SELECT * FROM products; DROP TABLE products",
    ],
)
def test_reject_unsafe_sql(sql):
    with pytest.raises(ValueError):
        validate_select(sql)


def test_unknown_table_is_rejected():
    with pytest.raises(ValueError):
        describe_table("table_that_does_not_exist")


# -------------------------
# Filesystem server tests
# -------------------------

def test_list_workspace():
    result = list_files(".")

    names = {item["name"] for item in result["items"]}
    assert "products.txt" in names
    assert "company_handbook.md" in names


def test_read_handbook():
    result = read_file("company_handbook.md")

    assert "Working Hours" in result["content"]
    assert "Refunds are processed within 7 business days." in result["content"]


def test_write_and_read_file():
    relative_path = f"notes/pytest_{uuid.uuid4().hex}.txt"
    expected = "Automated filesystem test."

    try:
        result = write_file(relative_path, expected)
        assert result["success"] is True

        read_result = read_file(relative_path)
        assert read_result["content"] == expected
    finally:
        path = resolve_workspace_path(relative_path)
        if path.exists():
            path.unlink()


@pytest.mark.parametrize(
    "path",
    [
        "../outside.txt",
        "..\\outside.txt",
        "C:\\Windows\\win.ini",
        "D:\\outside.txt",
    ],
)
def test_reject_paths_outside_workspace(path):
    with pytest.raises(ValueError):
        resolve_workspace_path(path)


def test_reject_oversized_file_content():
    relative_path = f"notes/pytest_oversized_{uuid.uuid4().hex}.txt"

    with pytest.raises(ValueError):
        write_file(relative_path, "x" * 100_001)

    assert not resolve_workspace_path(relative_path).exists()


def test_read_file_must_exist():
    relative_path = f"notes/missing_{uuid.uuid4().hex}.txt"

    with pytest.raises(FileNotFoundError):
        read_file(relative_path)


# -------------------------
# Weather server tests
# -------------------------

def test_weather_rejects_empty_city():
    with pytest.raises(ValueError, match="City name cannot be empty"):
        get_weather("   ")


def test_weather_rejects_overlong_city():
    with pytest.raises(ValueError, match="City name is too long"):
        get_weather("A" * 101)
