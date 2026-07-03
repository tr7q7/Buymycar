"""
Gestionnaire de jobs asynchrones en mémoire.

Motivation : une recherche Piloterr peut prendre 1 à 3 minutes (pagination,
~30 s/page). Une requête HTTP bloquante aussi longue est incompatible avec les
timeouts serverless (Vercel) et offre une mauvaise UX. On applique donc le
pattern job + polling :

    POST /search        → soumet un job, renvoie un job_id immédiatement
    GET  /search/{id}   → renvoie l'état (pending/running/done/error) + résultat

Implémentation MVP : registre en mémoire + ThreadPoolExecutor. Suffisant pour un
déploiement mono-instance (Render). À remplacer par Redis/RQ ou une file dédiée
le jour où l'API tourne sur plusieurs instances.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    id: str
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: Optional[str] = None


class JobManager:
    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """Enregistre un job et lance son exécution en arrière-plan."""
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = Job(id=job_id, status=JobStatus.PENDING)
        self._executor.submit(self._run, job_id, fn, *args, **kwargs)
        return job_id

    def _run(self, job_id: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self._set(job_id, status=JobStatus.RUNNING)
        try:
            result = fn(*args, **kwargs)
            self._set(job_id, status=JobStatus.DONE, result=result)
        except Exception as e:  # noqa: BLE001 — on capture pour exposer l'erreur au client
            self._set(job_id, status=JobStatus.ERROR, error=str(e))

    def _set(self, job_id: str, **changes: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for k, v in changes.items():
                setattr(job, k, v)

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)


# Singleton partagé par l'application
job_manager = JobManager()
