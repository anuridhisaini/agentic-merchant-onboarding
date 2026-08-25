"""
Web dashboard backend. Wraps the existing agent pipeline over HTTP so you can
submit applications and watch them move through agents in a browser instead
of reading terminal output.

Nothing about orchestrator.py, the agents, or state.py changes - this is a
thin layer on top of code that's already tested and working.

Run with:
    uvicorn api:app --reload

Then open http://localhost:8000 in your browser.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

import orchestrator
from state import MerchantApplication
from mock_data import load_mock_applications, MOCK_APPLICATIONS

app = FastAPI(title="Merchant Onboarding Agent Pipeline")

# Allow the frontend (served from the same origin, but being permissive
# here avoids CORS headaches if you ever split frontend/backend hosting)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApplicationInput(BaseModel):
    """What a user submits through the dashboard form."""
    application_id: str = "CUSTOM-001"
    business_name: str
    industry: str
    country: str
    monthly_volume_usd: float
    documents: dict = {}
    questions: list[str] = []


@app.get("/api/mock-applications")
def list_mock_applications():
    """Returns the 15 pre-built mock applications for quick demo selection."""
    return [
        {
            "application_id": app_data["application_id"],
            "business_name": app_data["business_name"],
            "scenario_tag": app_data["scenario_tag"],
            "industry": app_data["industry"],
        }
        for app_data in MOCK_APPLICATIONS
    ]


@app.post("/api/run/{application_id}")
def run_mock_application(application_id: str):
    """Runs the pipeline on one specific mock application by ID."""
    applications = load_mock_applications()
    match = next((a for a in applications if a.application_id == application_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"No mock application with id {application_id}")

    result = orchestrator.run(match)
    return result.full_dict()


@app.post("/api/submit")
def submit_custom_application(input_data: ApplicationInput):
    """Runs the pipeline on a custom application submitted via the dashboard form."""
    app_obj = MerchantApplication(
        application_id=input_data.application_id,
        business_name=input_data.business_name,
        industry=input_data.industry,
        country=input_data.country,
        monthly_volume_usd=input_data.monthly_volume_usd,
        documents=input_data.documents,
        questions=input_data.questions,
        scenario_tag="custom_submission",
    )
    result = orchestrator.run(app_obj)
    return result.full_dict()


@app.get("/api/metrics")
def get_aggregate_metrics():
    """Runs all 15 mock applications and returns aggregate metrics -
    same numbers run.py prints to the terminal, but as JSON for the dashboard."""
    applications = load_mock_applications()
    results = [orchestrator.run(a) for a in applications]

    decisions: dict[str, int] = {}
    total_handoffs = 0
    total_retries = 0
    for r in results:
        decisions[r.final_decision] = decisions.get(r.final_decision, 0) + 1
        total_handoffs += len(r.handoff_log)
        total_retries += sum(r.retry_counts.values())

    return {
        "total_applications": len(results),
        "decisions": decisions,
        "average_handoffs": round(total_handoffs / len(results), 2),
        "total_retries": total_retries,
        "results": [r.summary() for r in results],
    }


# Serve the frontend (index.html + assets) from /static, and make it the root page
app.mount("/", StaticFiles(directory="static", html=True), name="static")