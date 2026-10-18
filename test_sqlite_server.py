
from servers.sqlite_server import (
    describe_table,
    list_tables,
    query_database,
    validate_select,
)


def main():
    print("\n1. LIST TABLES")
    print(list_tables())

    print("\n2. DESCRIBE PRODUCTS")
    print(describe_table("products"))

    print("\n3. QUERY PRODUCTS")
    result = query_database(
        "SELECT name, category, price FROM products ORDER BY price DESC"
    )
    print(result)

    print("\n4. TEST WRITE-QUERY REJECTION")
    try:
        validate_select("DELETE FROM products")
    except ValueError as exc:
        print("Correctly rejected:", exc)
    else:
        raise AssertionError("DELETE query was not rejected")

    print("\n5. TEST MULTIPLE-STATEMENT REJECTION")
    try:
        validate_select("SELECT * FROM products; DROP TABLE products")
    except ValueError as exc:
        print("Correctly rejected:", exc)
    else:
        raise AssertionError("Multiple SQL statements were not rejected")

    print("\nAll direct tests passed.")


if __name__ == "__main__":
    main()
