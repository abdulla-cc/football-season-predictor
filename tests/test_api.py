import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import src.api as api
from src.api import health
from fastapi import HTTPException
import pytest


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


def test_admin_key_is_required(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")

    with pytest.raises(HTTPException) as missing:
        api.require_admin_key(None)
    assert missing.value.status_code == 401

    with pytest.raises(HTTPException) as incorrect:
        api.require_admin_key("wrong-key")
    assert incorrect.value.status_code == 401

    assert api.require_admin_key("test-admin-key") is None


def test_admin_operations_fail_closed_without_configuration(monkeypatch):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)

    with pytest.raises(HTTPException) as error:
        api.require_admin_key("any-key")
    assert error.value.status_code == 503


def test_expensive_mutations_are_only_exposed_as_protected_admin_routes():
    routes = {route.path: route for route in api.app.routes if hasattr(route, "methods")}

    assert "/api/update-data" not in routes
    assert "/api/admin/update-data" in routes
    assert "/api/admin/simulation/refresh" in routes
    assert routes["/api/admin/update-data"].dependant.dependencies
    assert routes["/api/admin/simulation/refresh"].dependant.dependencies


def test_render_allows_only_the_production_frontend_origin():
    render_config = Path("render.yaml").read_text(encoding="utf-8")

    assert 'value: "https://football-season-predictor.vercel.app"' in render_config
    assert 'value: "*"' not in render_config
