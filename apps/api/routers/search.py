"""
Recherche — pattern job asynchrone + polling.

POST /search       → soumet la recherche, renvoie un job_id (202 Accepted)
GET  /search/{id}  → état du job ; quand status=done, contient le résultat

La recherche elle-même (run_search) est le cœur métier extrait à l'Étape 1 :
l'API ne fait qu'orchestrer l'asynchrone et sérialiser le résultat.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.services.search_service import run_search
from apps.api.db import get_db
from apps.api.db_models import Search
from apps.api import credits_service
from apps.api.jobs import job_manager, JobStatus
from apps.api.schemas import (
    SearchRequest, JobCreatedOut, JobStatusOut, to_search_result_out,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=JobCreatedOut, status_code=status.HTTP_202_ACCEPTED)
def create_search(req: SearchRequest, db: Session = Depends(get_db)) -> JobCreatedOut:
    """
    Soumet une recherche en arrière-plan après consommation d'un crédit.

    Décrément atomique AVANT lancement : si aucun crédit, on renvoie 402 NEED_CREDITS
    sans lancer de job ni consommer de crédit. Le crédit n'est débité qu'une fois,
    au lancement accepté (pas de remboursement auto en cas d'échec technique du job).
    """
    if not credits_service.decrement(db, req.email):
        raise HTTPException(status_code=402, detail="NEED_CREDITS")

    job_id = job_manager.submit(
        run_search,
        req.brand, req.model, req.fuel, req.year_min, req.year_max, req.specification,
    )

    # Trace la recherche (email ↔ job) pour un éventuel remboursement futur.
    db.add(Search(email=credits_service.normalize_email(req.email), search_id=job_id))
    db.commit()

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
