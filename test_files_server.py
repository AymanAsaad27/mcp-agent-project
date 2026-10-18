
import tempfile
from pathlib import Path

from servers.files_server import (
    list_files,
    read_file,
    resolve_workspace_path,
    write_file,
)


def main():
    print("\n1. LIST WORKSPACE FILES")
    result = list_files(".")
    print(result)

    print("\n2. READ HANDBOOK")
    handbook = read_file("company_handbook.md")
    print(handbook["content"][:150])
    assert handbook["characters"] > 0

    print("\n3. WRITE AND READ A TEST FILE")
    test_path = "notes/mcp_test.txt"
    original_content = "Filesystem MCP test passed."

    write_result = write_file(test_path, original_content)
    print(write_result)

    read_result = read_file(test_path)
    assert read_result["content"] == original_content
    print("Write/read round trip passed.")

    print("\n4. TEST PATH-TRAVERSAL PROTECTION")
    malicious_paths = [
        "..\\outside.txt",
        "../outside.txt",
        "C:\\Windows\\win.ini",
        "D:\\outside.txt",
    ]

    for path in malicious_paths:
        try:
            resolve_workspace_path(path)
        except ValueError:
            print(f"Correctly rejected: {path}")
        else:
            raise AssertionError(f"Unsafe path was accepted: {path}")

    print("\n5. TEST OVERSIZED WRITE")
    try:
        write_file("notes/too_large.txt", "x" * 100_001)
    except ValueError as exc:
        print("Correctly rejected:", exc)
    else:
        raise AssertionError("Oversized write was accepted")

    print("\nAll filesystem direct tests passed.")


if __name__ == "__main__":
    main()
