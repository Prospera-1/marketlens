"""
Simple deterministic checks for the competitor discovery module.

Run:
  python -m backend.competitor_discovery.example_test_cases
"""

from backend.competitor_discovery.competitor_engine import CompanyNotFoundError, get_competitors


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run() -> None:
    # Case-insensitive industry detection + exclusion of the target.
    res_hyundai = get_competitors("Hyundai")
    _assert(res_hyundai["industry"] == "automobile", "Expected automobile industry for Hyundai")
    _assert(
        all(c["name"].lower() != "hyundai" for c in res_hyundai["competitors"]),
        "Hyundai must not be included in its own competitor list",
    )
    _assert(len(res_hyundai["competitors"]) >= 4, "Expected at least 4 automobile competitors")

    # Another industry.
    res_teams = get_competitors("teams")
    _assert(res_teams["industry"] == "saas", "Expected saas industry for Teams")
    _assert(
        all(c["name"].lower() != "teams" for c in res_teams["competitors"]),
        "Teams must not be included in its own competitor list",
    )

    # Unknown company should raise with suggestions (fuzzy matching).
    try:
        get_competitors("Slak")  # misspelling
        raise AssertionError("Expected CompanyNotFoundError for unknown company")
    except CompanyNotFoundError as e:
        _assert(len(e.suggestions) > 0, "Expected fuzzy suggestions for misspelled company")

    print("All example test cases passed.")


if __name__ == "__main__":
    run()

