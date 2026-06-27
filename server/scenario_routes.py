"""Routes for uploaded playbook to generated scenario conversion."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from crucible.agents.base import ModelClient, ModelClientError, make_client
from crucible.config import Settings, get_settings
from crucible.scenarios.builder import build_generated_scenario
from crucible.scenarios.generated import register_generated_scenario
from crucible.scenarios.upload import extract_playbook_text

router = APIRouter()


def get_scenario_model_client(settings: Settings = Depends(get_settings)) -> ModelClient:
    return make_client(settings)


@router.post("/scenarios/generate")
async def generate_scenario(
    file: UploadFile = File(...),
    language: str = Form("en"),
    settings: Settings = Depends(get_settings),
    client: ModelClient = Depends(get_scenario_model_client),
):
    try:
        data = await file.read()
        text = extract_playbook_text(file.filename or "playbook", file.content_type, data)
        scenario = build_generated_scenario(
            client=client,
            model=settings.session_prep_model,
            raw_playbook_text=text,
            filename=file.filename or "playbook",
            language=language,
        )
        register_generated_scenario(scenario)
        return scenario.frontend_dict()
    except ModelClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
