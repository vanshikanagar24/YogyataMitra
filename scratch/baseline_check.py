import asyncio
import os
import sys
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.scheme import Scheme, PolicyVersion, RuleSet


async def main():
    async with AsyncSessionLocal() as s:
        schemes = (await s.execute(select(Scheme).order_by(Scheme.scheme_code))).scalars().all()
        pvs = (await s.execute(select(PolicyVersion).order_by(PolicyVersion.version_code))).scalars().all()
        rss = (await s.execute(select(RuleSet))).scalars().all()

        print(f"SCHEME COUNT: {len(schemes)}")
        for sc in schemes:
            print(f"  - {sc.scheme_code}: {sc.name_en}")

        print(f"POLICY VERSION COUNT: {len(pvs)}")
        for pv in pvs:
            print(f"  - {pv.version_code} | id={pv.id} | hash={pv.rule_definition_hash}")

        print(f"RULESET COUNT: {len(rss)}")
        for rs in rss:
            print(f"  - RuleSet id={rs.id} for policy_version_id={rs.policy_version_id}")


if __name__ == "__main__":
    asyncio.run(main())
