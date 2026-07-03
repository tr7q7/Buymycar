"""
Recherche — pattern job asynchrone + polling.

POST /search       → soumet la recherche, renvoie un job_id (202 Accepted)
GET  /search/{id}  → état du job ; quand status=done, contient le résultat

La recherche elle-même (run_search) est le cœur métier extrait à l'Étape 1 :
l'API ne fait qu'orchestrer l'asynchrone et sérialiser le résultat.
"""

from fastapi import APIRouter, HTTPException, status

from app.services.search_service import run_search
from apps.api.jobs import job_manager, JobStatus
from apps.api.schemas import (
    SearchRequest, JobCreatedOut, JobStatusOut, to_search_result_out,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=JobCreatedOut, status_code=status.HTTP_202_ACCEPTED)
def create_search(req: SearchRequest) -> JobCreatedOut:
    """Soumet une recherche en arrière-plan. Renvoie un identifiant à interroger."""
    job_id = job_manager.submit(
        run_search,
        req.brand, req.model, req.fuel, req.year_min, req.year_max,
    )
    return JobCreatedOut(job_id=job_id, status=JobStatus.PENDING.value)


@router.get("/{job_id}", response_model=JobStatusOut)
def get_search(job_id: str) -> JobStatusOut:
    """État d'une recherche. Le résultat n'est présent que si status=done."""
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job introuvable")

    result_out = None
    if job.status == JobStatus.DONE and job.result is not None:
        result_out = to_search_result_out(job.result)

    return JobStatusOut(
        job_id=job.id,
        status=job.status.value,
        result=result_out,
        error=job.error,
    )
