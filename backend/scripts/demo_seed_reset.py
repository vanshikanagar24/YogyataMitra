# ========================================================================
# SYNTHETIC DEMONSTRATION DATA ONLY
# NOT VALID FOR GOVERNMENT USE
# Zero real PII — all identities are fabricated for demonstration purposes
# ========================================================================

import sys
import asyncio
import argparse
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.citizen import Citizen, Claim, Evidence
from app.models.evaluation import EvaluationTrace
from app.models.enums import JourneyState, ClaimStatus
from app.models.journey import EvaluationJourney, JourneyTransitionRecord
from app.models.scheme import Scheme, PolicyVersion
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

async def reset_demo_data(session):
    """Delete only synthetic demo data."""
    # Find SYN-CIT-DEMO* citizens
    stmt = select(Citizen).where(Citizen.synthetic_reference.like("SYN-CIT-DEMO%"))
    result = await session.execute(stmt)
    citizens = result.scalars().all()
    
    citizen_ids = [c.id for c in citizens]
    
    if citizen_ids:
        # Delete evaluation traces before deleting their synthetic citizens.
        # This is restricted to the synthetic citizen IDs selected above.
        stmt = delete(EvaluationTrace).where(
            EvaluationTrace.citizen_id.in_(citizen_ids)
        )
        await session.execute(stmt)

        # Delete journeys for synthetic citizens
        stmt = delete(EvaluationJourney).where(EvaluationJourney.citizen_id.in_(citizen_ids))
        result = await session.execute(stmt)
        journeys_deleted = result.rowcount
        
        # Delete claims for synthetic citizens (cascades to evidence)
        stmt = delete(Claim).where(Claim.citizen_id.in_(citizen_ids))
        await session.execute(stmt)

        # Delete synthetic citizens
        stmt = delete(Citizen).where(Citizen.id.in_(citizen_ids))
        result = await session.execute(stmt)
        citizens_deleted = result.rowcount
        
        print(f"[DEMO RESET] Deleted {journeys_deleted} synthetic journeys for SYN-CIT-DEMO* citizens")
        print(f"[DEMO RESET] Deleted {citizens_deleted} synthetic citizen profiles")
    else:
        print("[DEMO RESET] No synthetic demo data found to delete")

async def seed_demo_data(session):
    """Create synthetic demo citizens and sample journeys."""
    citizens_data = [
        {"ref": "SYN-CIT-DEMO0001", "name": "Ramesh Kumar (Demo)", "dob": date(1985, 6, 15), "gender": "Male", "state": "Uttar Pradesh", "district": "Varanasi", "target_scheme": "PM_KISAN"},
        {"ref": "SYN-CIT-DEMO0002", "name": "Sunita Devi (Demo)", "dob": date(1990, 3, 22), "gender": "Female", "state": "Maharashtra", "district": "Pune", "target_scheme": "SSY"},
        {"ref": "SYN-CIT-DEMO0003", "name": "Priya Sharma (Demo)", "dob": date(2020, 1, 10), "gender": "Female", "state": "Rajasthan", "district": "Jaipur", "target_scheme": "PMMVY"},
    ]
    
    for c_data in citizens_data:
        # Create citizen if not exist
        stmt = select(Citizen).where(Citizen.synthetic_reference == c_data["ref"])
        result = await session.execute(stmt)
        citizen = result.scalar_one_or_none()
        
        if not citizen:
            citizen = Citizen(
                synthetic_reference=c_data["ref"],
                display_name=c_data["name"],
                date_of_birth=c_data["dob"],
                gender=c_data["gender"],
                state=c_data["state"],
                district=c_data["district"]
            )
            session.add(citizen)
            await session.flush()
            print(f"[DEMO SEED] Created citizen {c_data['ref']} ({c_data['name'].replace(' (Demo)', '')})")
        
        # Find active scheme
        stmt = select(Scheme).where(Scheme.scheme_code == c_data["target_scheme"])
        result = await session.execute(stmt)
        scheme = result.scalar_one_or_none()
        
        if scheme:
            stmt = select(EvaluationJourney).where(
                EvaluationJourney.citizen_id == citizen.id,
                EvaluationJourney.scheme_id == scheme.id
            )
            result = await session.execute(stmt)
            existing_journey = result.scalar_one_or_none()
            
            if not existing_journey:
                stmt = select(PolicyVersion).where(PolicyVersion.scheme_id == scheme.id)
                result = await session.execute(stmt)
                policy_version = result.scalars().first()
                
                journey = EvaluationJourney(
                    citizen_id=citizen.id,
                    scheme_id=scheme.id,
                    policy_version_id=policy_version.id if policy_version else None,
                    state=JourneyState.DRAFT
                )
                session.add(journey)
                print(f"[DEMO SEED] Created {c_data['target_scheme']} DRAFT journey for {c_data['ref']}")
        else:
            print(f"[DEMO SEED] Scheme {c_data['target_scheme']} not found for journey creation")

async def main():
    parser = argparse.ArgumentParser(description="YogyataMitra Demo Seed/Reset")
    parser.add_argument("--reset", action="store_true", help="Reset synthetic demo data before seeding")
    parser.add_argument("--seed-only", action="store_true", help="Only seed, skip reset")
    args = parser.parse_args()
    
    async with AsyncSessionLocal() as session:
        if args.reset or not args.seed_only:
            await reset_demo_data(session)
        await seed_demo_data(session)
        await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
