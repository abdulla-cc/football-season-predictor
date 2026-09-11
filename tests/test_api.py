import time
from concurrent.futures import ThreadPoolExecutor

import src.api as api
from src.api import health


def test_health_response_identifies_the_service():
    assert health() == {
        "status": "ok",
        "league": "Premier League 2026/27",
        "model": "Dixon-Coles",
    }


def test_concurrent_model_requests_train_only_once(monkeypatch):
    trained_models = []

    def fake_fit(training_data):
        time.sleep(0.05)
        model = object()
        trained_models.append(model)
        return model

    monkeypatch.setattr(api, "get_complete_training_data", lambda: "training data")
    monkeypatch.setattr(api, "fit_poisson_model", fake_fit)
    api.CACHE.clear()

    with ThreadPoolExecutor(max_workers=2) as executor:
        models = list(executor.map(lambda _: api.get_or_train_model(), range(2)))

    assert len(trained_models) == 1
    assert models[0] is models[1]
    api.CACHE.clear()
