"""API v1 Aggregated Router."""

from fastapi import APIRouter

from app.api.v1.citizen_applications import router as citizen_applications_router
from app.api.v1.citizen_auth import router as citizen_auth_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.journeys import router as journeys_router
from app.api.v1.officer import router as officer_router
from app.api.v1.policies import router as policies_router
from app.api.v1.policy_authoring import router as policy_authoring_router
from app.api.v1.policy_discovery import router as policy_discovery_router
from app.api.v1.provenance import router as provenance_router
from app.api.v1.schemes import router as schemes_router

api_v1_router = APIRouter()

api_v1_router.include_router(schemes_router)
api_v1_router.include_router(policies_router)
api_v1_router.include_router(evaluations_router)
api_v1_router.include_router(journeys_router)
api_v1_router.include_router(officer_router)
api_v1_router.include_router(citizen_auth_router)
api_v1_router.include_router(citizen_applications_router)
api_v1_router.include_router(policy_discovery_router)
api_v1_router.include_router(policy_authoring_router)
api_v1_router.include_router(provenance_router)
