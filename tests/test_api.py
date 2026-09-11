from src.api import health


def test_health_response_identifies_the_service():
    assert health() == {
        "status": "ok",
        "league": "Premier League 2026/27",
        "model": "Dixon-Coles",
    }
