import asyncio
import hashlib
import json
import sys
sys.path.insert(0, ".")
from app.core.database import AsyncSessionLocal
from app.models.scheme import PolicyVersion, RuleSet, Scheme
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Scheme))
        schemes = res.scalars().all()
        scheme_map = {s.id: s.scheme_code for s in schemes}

        res = await session.execute(
            select(PolicyVersion)
            .options(selectinload(PolicyVersion.rule_set))
            .order_by(PolicyVersion.scheme_id, PolicyVersion.effective_from)
        )
        pvs = res.scalars().all()

        print(f"{'scheme_code':<12} | {'version_code':<20} | {'effective_from':<14} | {'effective_to':<14} | {'ruleset_id':<38} | {'actual_rule_hash'}")
        print("-" * 170)

        for pv in pvs:
            code = scheme_map.get(pv.scheme_id, 'UNKNOWN')
            rs = pv.rule_set
            rs_id = str(rs.id) if rs else "NONE"
            
            # Compute hash of definition_json
            computed_hash = "NONE"
            if rs and rs.definition_json:
                canonical_str = json.dumps(rs.definition_json, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                computed_hash = hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

            # Also check pv.rule_definition_hash
            db_hash = pv.rule_definition_hash or "NONE"
            
            print(f"{code:<12} | {pv.version_code:<20} | {str(pv.effective_from):<14} | {str(pv.effective_to):<14} | {rs_id:<38} | {computed_hash}")
            if db_hash != "NONE" and db_hash != computed_hash:
                print(f"   [db rule_definition_hash]: {db_hash}")

if __name__ == "__main__":
    asyncio.run(main())
