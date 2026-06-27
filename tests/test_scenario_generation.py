import json

from starlette.testclient import TestClient

from crucible.agents.base import FakeModelClient
from crucible.runner import make_runner
from server.app import app, get_runner
from server.scenario_routes import get_scenario_model_client
from tests.conftest import test_settings


def _scenario_json() -> str:
    authority = {
        "celex": None,
        "eli": None,
        "title": "Playbook",
        "pinpoint": "Training goals",
        "source": "firm_playbook",
        "url": None,
    }
    return json.dumps(
        {
            "label": "Vendor Liability Drill",
            "description": "Practise liability cap negotiation from a firm playbook.",
            "playbook": {
                "scenario": "negotiation",
                "matter_summary": "The trainee represents the customer in a SaaS liability negotiation.",
                "objectives": ["Anchor a balanced cap", "Protect mandatory carve-outs"],
                "items": [
                    {
                        "id": "cap_anchor",
                        "label": "Cap anchor",
                        "kind": "must_have",
                        "target": "Ask for a customer-protective cap with reasons.",
                        "walk_away": "Accepting the vendor cap without value.",
                        "authorities": [authority],
                        "weight": 1.4,
                    },
                    {
                        "id": "carve_outs",
                        "label": "Carve-outs",
                        "kind": "must_have",
                        "target": "Keep fraud and gross negligence uncapped.",
                        "walk_away": None,
                        "authorities": [authority],
                        "weight": 1.4,
                    },
                    {
                        "id": "overreach",
                        "label": "Overreach trap",
                        "kind": "trap",
                        "target": "Avoid unlimited liability across every loss.",
                        "walk_away": None,
                        "authorities": [authority],
                        "weight": 1.0,
                    },
                ],
                "fallback_ladder": ["Trade cap movement for SLA value"],
                "walk_away_conditions": ["Vendor refuses serious carve-outs"],
                "authorities": [authority],
            },
            "opp_playbook": {
                "objectives": ["Keep liability predictable"],
                "batna": "Walk away from unlimited exposure.",
                "concession_ladder": [
                    {
                        "position": "Insist on one annual fee cap.",
                        "unlock_condition": "Trainee explains business-critical risk.",
                    }
                ],
            },
            "brief": {
                "authorities": [
                    {"title": "Playbook", "pinpoint": "Training goals", "note": "Source for this drill"}
                ],
                "strategy": ["Anchor early"],
                "watchOut": ["Do not concede without reciprocal value"],
            },
        }
    )


def teardown_function():
    app.dependency_overrides.clear()


def test_generate_scenario_endpoint_registers_startable_scenario():
    app.dependency_overrides[get_scenario_model_client] = lambda: FakeModelClient([_scenario_json()])
    runner = make_runner(test_settings(), FakeModelClient([]))
    app.dependency_overrides[get_runner] = lambda: runner

    with TestClient(app) as client:
        upload = ("playbook.txt", ("playbook content\n" * 80).encode(), "text/plain")
        generated = client.post("/scenarios/generate", files={"file": upload}, data={"language": "en"})
        assert generated.status_code == 200
        scenario_id = generated.json()["id"]

        started = client.post(
            "/round/generated/start",
            json={"scenario": scenario_id, "persona": "aggressor", "hardness": "standard"},
        )
        context = client.get("/round/generated/context")

    assert started.status_code == 200
    assert context.status_code == 200
    assert context.json()["hooks"][0]["id"] == "cap_anchor"


def test_generate_scenario_rejects_too_short_upload():
    app.dependency_overrides[get_scenario_model_client] = lambda: FakeModelClient([_scenario_json()])

    with TestClient(app) as client:
        response = client.post(
            "/scenarios/generate",
            files={"file": ("playbook.txt", b"too short", "text/plain")},
            data={"language": "en"},
        )

    assert response.status_code == 400
    assert "enough extractable text" in response.json()["detail"]
