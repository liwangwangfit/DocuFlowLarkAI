import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from utils.system_resource import calculate_dynamic_workers


def test_dynamic_workers_never_exceeds_total_files():
    workers, detail = calculate_dynamic_workers(total_files=3)
    assert workers <= 3
    assert workers >= 1
    assert "cpu_count" in detail
    assert "available_memory_gb" in detail


def test_dynamic_workers_respects_upper_bound():
    workers, _ = calculate_dynamic_workers(total_files=999, max_workers=6)
    assert workers <= 6
