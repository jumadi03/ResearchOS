"""
Manual test for Law Registry.
"""

from app.architecture.governance import LawRegistry


def main() -> None:
    registry = LawRegistry()

    print("Registry :", registry)
    print("All      :", registry.get_all())
    print("By ID    :", registry.get_by_id("ALA-STR-001"))
    print("Category :", registry.get_by_category("Structural"))

    print()
    print("PASS")


if __name__ == "__main__":
    main()