"""
PostHog côté backend — un seul événement métier : payment_completed.

No-op si POSTHOG_API_KEY absente (dev local sans clé, tests).
"""

import logging

from apps.api.core.config import settings

logger = logging.getLogger("autocote.analytics")

_client = None
_init_attempted = False


def _get_client():
    global _client, _init_attempted
    if _init_attempted:
        return _client
    _init_attempted = True
    if not settings.posthog_api_key:
        return None
    import posthog as posthog_module

    _client = posthog_module.Posthog(
        settings.posthog_api_key, host=settings.posthog_host
    )
    return _client


def track(distinct_id: str, event: str, properties: dict | None = None) -> None:
    client = _get_client()
    if not client or not distinct_id:
        return
    try:
        client.capture(distinct_id=distinct_id, event=event, properties=properties or {})
    except Exception:
        logger.warning("[posthog] échec envoi event=%s", event, exc_info=True)
