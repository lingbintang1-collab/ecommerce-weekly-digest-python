import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from digest_service import digest_lines


def test_digest_lines_makes_order_state_visible():
    orders = [{"order_id": "A-17", "status": "shipped", "total": 42.5}]
    assert digest_lines(orders) == ["A-17: shipped ($42.50)"]
