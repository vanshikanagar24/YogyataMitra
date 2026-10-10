"""Seed demonstration citizen profile and multiple applications for Phase B.

Creates or updates demo citizen `SYN-CIT-DEMO0001` with:
1. Application 1: PM_KISAN (State: EVALUATED, ELIGIBLE under v3.0-2023)
   - Cultivable land claim (1.8 Ha)
   - Verified RoR Land Record
   - Evaluated trace record with bilingual explanations
   - Full transition history
2. Application 2: SSY (State: VERIFICATION_IN_PROGRESS)
   - Girl child age claim (6 years)
   - Biological mother guardianship claim
   - Submitted Birth Certificate evidence
   - Active transition history
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.enums import (
    ClaimStatus,
    EligibilityResult,
    EvidenceStatus,
    JourneyState,
    VerificationStatus,
)
from app.models.evaluation import EvaluationTrace
from app.models.journey import EvaluationJourney, JourneyTransitionRecord
from app.models.scheme import Scheme, PolicyVersion


async def seed_demo_citizen():
    async with AsyncSessionLocal() as session:
        # 1. Ensure Citizen SYN-CIT-DEMO0001 exists
        res = await session.execute(
            select(Citizen).where(Citizen.synthetic_reference == "SYN-CIT-DEMO0001")
        )
        citizen = res.scalar_one_or_none()
        if not citizen:
            citizen = Citizen(
                synthetic_reference="SYN-CIT-DEMO0001",
                display_name="Test Citizen (Demo)",
                date_of_birth=date(1985, 6, 15),
                gender="Male",
                state="Maharashtra",
                district="Pune",
            )
            session.add(citizen)
            await session.flush()
            print(f"Created citizen: {citizen.synthetic_reference} (id={citizen.id})")
        else:
            print(f"Found citizen: {citizen.synthetic_reference} (id={citizen.id})")

        # 2. Get PM_KISAN and SSY schemes
        pm_kisan_res = await session.execute(
            select(Scheme)
            .where(Scheme.scheme_code == "PM_KISAN")
            .options(selectinload(Scheme.policy_versions))
        )
        pm_kisan = pm_kisan_res.scalar_one_or_none()

        ssy_res = await session.execute(
            select(Scheme)
            .where(Scheme.scheme_code == "SSY")
            .options(selectinload(Scheme.policy_versions))
        )
        ssy = ssy_res.scalar_one_or_none()

        if not pm_kisan or not ssy:
            print("ERROR: Schemes PM_KISAN or SSY not found in database!")
            return

        # 3. Check existing journeys for this citizen
        j_res = await session.execute(
            select(EvaluationJourney)
            .where(EvaluationJourney.citizen_id == citizen.id)
            .options(selectinload(EvaluationJourney.scheme))
        )
        existing_journeys = {j.scheme.scheme_code: j for j in j_res.scalars().all()}

        # Seed PM-KISAN Journey if missing
        if "PM_KISAN" not in existing_journeys:
            # Active policy version
            pv_pmkisan = next(
                (pv for pv in pm_kisan.policy_versions if "2023" in pv.version_code),
                pm_kisan.policy_versions[0],
            )

            # Create EvaluationTrace
            trace_data = {
                "result": "ELIGIBLE",
                "ruleset_version": pv_pmkisan.version_code,
                "reasons_en": [
                    "Applicant holds cultivable agricultural land of 1.8 hectares.",
                    "No statutory constitutional or institutional exclusions triggered.",
                    "All required land ownership documents verified by Welfare Officer.",
                ],
                "reasons_hi": [
                    "आवेदक के पास 1.8 हेक्टेयर कृषि योग्य भूमि की पुष्टि हुई।",
                    "कोई संवैधानिक या संस्थागत बहिष्करण नियम लागू नहीं हुआ।",
                    "कल्याण अधिकारी द्वारा भू-अभिलेख दस्तावेज़ सत्यापित किए गए।",
                ],
            }
            eval_trace = EvaluationTrace(
                citizen_id=citizen.id,
                scheme_id=pm_kisan.id,
                policy_version_id=pv_pmkisan.id,
                evaluation_date=date.today(),
                input_snapshot_json={
                    "agricultural_landholding": 1.8,
                    "is_institutional_landholder": False,
                    "paid_income_tax_last_ay": False,
                },
                result_state=EligibilityResult.ELIGIBLE,
                trace_json=trace_data,
                rule_definition_hash=pv_pmkisan.rule_definition_hash,
            )
            session.add(eval_trace)
            await session.flush()

            # Create Journey
            j_pmkisan = EvaluationJourney(
                citizen_id=citizen.id,
                scheme_id=pm_kisan.id,
                state=JourneyState.EVALUATED,
                policy_version_id=pv_pmkisan.id,
                submitted_at=datetime.now(timezone.utc),
                latest_evaluation_id=eval_trace.id,
            )
            session.add(j_pmkisan)
            await session.flush()

            # Transitions
            t1 = JourneyTransitionRecord(
                journey_id=j_pmkisan.id,
                from_state=JourneyState.DRAFT,
                to_state=JourneyState.FACTS_COLLECTED,
                actor="CITIZEN",
                reason="Application self-declaration submitted by citizen",
            )
            t2 = JourneyTransitionRecord(
                journey_id=j_pmkisan.id,
                from_state=JourneyState.FACTS_COLLECTED,
                to_state=JourneyState.VERIFICATION_IN_PROGRESS,
                actor="CITIZEN",
                reason="Land record evidence attached and queued for verification",
            )
            t3 = JourneyTransitionRecord(
                journey_id=j_pmkisan.id,
                from_state=JourneyState.VERIFICATION_IN_PROGRESS,
                to_state=JourneyState.EVALUATED,
                actor="OFFICER",
                reason="Documents verified; statutory evaluation completed with outcome ELIGIBLE",
            )
            session.add_all([t1, t2, t3])

            # Claims
            c1 = Claim(
                citizen_id=citizen.id,
                journey_id=j_pmkisan.id,
                claim_type="agricultural_landholding",
                value_json={"has_cultivable_land": True, "land_area_hectares": 1.8},
                source="CITIZEN_DECLARATION",
                status=ClaimStatus.VERIFIED,
            )
            c2 = Claim(
                citizen_id=citizen.id,
                journey_id=j_pmkisan.id,
                claim_type="institutional_landholder",
                value_json={"is_institutional_landholder": False},
                source="CITIZEN_DECLARATION",
                status=ClaimStatus.VERIFIED,
            )
            c3 = Claim(
                citizen_id=citizen.id,
                journey_id=j_pmkisan.id,
                claim_type="income_tax_payee",
                value_json={"paid_income_tax_last_ay": False},
                source="CITIZEN_DECLARATION",
                status=ClaimStatus.VERIFIED,
            )
            session.add_all([c1, c2, c3])
            await session.flush()

            # Evidence on claim 1
            e1 = Evidence(
                claim_id=c1.id,
                evidence_type="land_record_7_12",
                storage_reference="uploads/pmkisan_ror_712.pdf",
                metadata_json={"survey_number": "142/3", "village": "Haveli", "district": "Pune"},
                status=EvidenceStatus.VERIFIED,
                verified_at=datetime.now(timezone.utc),
            )
            session.add(e1)
            await session.flush()

            vr1 = VerificationRecord(
                evidence_id=e1.id,
                claim_id=c1.id,
                verification_method="OFFICER_MANUAL_REVIEW",
                status=VerificationStatus.VERIFIED,
                verified_by="officer.pune@yogyatamitra.gov.in",
                verified_at=datetime.now(timezone.utc),
                details_json={"note": "Verified against Maharashtra Mahabhulekh RoR digital record."},
            )
            session.add(vr1)
            print(f"Created PM-KISAN evaluated journey: {j_pmkisan.id}")
        else:
            print("PM-KISAN journey already exists for demo citizen.")

        # Seed SSY Journey if missing
        if "SSY" not in existing_journeys:
            pv_ssy = next(
                (pv for pv in ssy.policy_versions if "2024" in pv.version_code),
                ssy.policy_versions[0],
            )
            j_ssy = EvaluationJourney(
                citizen_id=citizen.id,
                scheme_id=ssy.id,
                state=JourneyState.VERIFICATION_IN_PROGRESS,
                policy_version_id=pv_ssy.id,
                submitted_at=datetime.now(timezone.utc),
            )
            session.add(j_ssy)
            await session.flush()

            t_ssy1 = JourneyTransitionRecord(
                journey_id=j_ssy.id,
                from_state=JourneyState.DRAFT,
                to_state=JourneyState.FACTS_COLLECTED,
                actor="CITIZEN",
                reason="SSY girl child declaration submitted",
            )
            t_ssy2 = JourneyTransitionRecord(
                journey_id=j_ssy.id,
                from_state=JourneyState.FACTS_COLLECTED,
                to_state=JourneyState.VERIFICATION_IN_PROGRESS,
                actor="CITIZEN",
                reason="Uploaded municipal birth certificate; queued for officer verification",
            )
            session.add_all([t_ssy1, t_ssy2])

            c_ssy1 = Claim(
                citizen_id=citizen.id,
                journey_id=j_ssy.id,
                claim_type="girl_child_age",
                value_json={"girl_child_age": 6, "date_of_birth": "2020-04-12"},
                source="CITIZEN_DECLARATION",
                status=ClaimStatus.CLAIMED,
            )
            c_ssy2 = Claim(
                citizen_id=citizen.id,
                journey_id=j_ssy.id,
                claim_type="guardian_relationship",
                value_json={"relationship": "BIOLOGICAL_FATHER", "is_natural_guardian": True},
                source="CITIZEN_DECLARATION",
                status=ClaimStatus.CLAIMED,
            )
            c_ssy3 = Claim(
                citizen_id=citizen.id,
                journey_id=j_ssy.id,
                claim_type="number_of_daughters",
                value_json={"family_daughter_count": 1},
                source="CITIZEN_DECLARATION",
                status=ClaimStatus.CLAIMED,
            )
            session.add_all([c_ssy1, c_ssy2, c_ssy3])
            await session.flush()

            e_ssy1 = Evidence(
                claim_id=c_ssy1.id,
                evidence_type="birth_certificate",
                storage_reference="uploads/ssy_birth_cert.pdf",
                metadata_json={"issuing_authority": "Pune Municipal Corporation", "reg_number": "PMC/2020/4891"},
                status=EvidenceStatus.PENDING,
            )
            session.add(e_ssy1)
            print(f"Created SSY under-verification journey: {j_ssy.id}")
        else:
            print("SSY journey already exists for demo citizen.")

        await session.commit()
        print("Demo citizen seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_demo_citizen())
