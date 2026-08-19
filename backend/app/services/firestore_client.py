"""The only module allowed to import google.cloud.firestore directly.

Everything else — department code, ADK tools, API routes — goes through the
org-scoped helpers here. See /docs/system_prompt.md and
.cursor/rules/firestore-access.mdc.
"""

from functools import lru_cache

from google.cloud import firestore

from app.config import settings


@lru_cache
def get_client() -> firestore.Client:
    return firestore.Client(project=settings.google_cloud_project)


def org_collection(org_id: str, collection: str) -> firestore.CollectionReference:
    """orgs/{org_id}/{collection}"""
    return get_client().collection("orgs").document(org_id).collection(collection)


def org_doc(org_id: str, collection: str, doc_id: str) -> firestore.DocumentReference:
    return org_collection(org_id, collection).document(doc_id)
