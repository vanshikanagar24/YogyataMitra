"""Provider-neutral AI policy discovery and candidate extraction abstraction.

Establishes standard interfaces for discovering official government policy texts,
extracting candidate eligibility/exclusion statements, identifying provenance,
detecting conflicts, and generating structured advisory intelligence for human review.

CRITICAL ARCHITECTURAL BOUNDARY:
- AI outputs are strictly non-executable data objects.
- AI never generates AST, never activates policy, and never determines citizen eligibility.
- Prompts and extracted texts are treated as untrusted text data.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.policy_discovery import (
    CandidateType,
    EffectiveDateStatus,
    ProvenanceStatus,
)

import re

logger = logging.getLogger(__name__)


class PolicyDiscoveryProviderError(Exception):
    """Raised when an external AI discovery provider encounters an error, timeout, or malformed data.
    
    Security Invariant: Never contains API keys, tokens, or credentials in message or representation.
    """

    def __init__(self, message: str, provider_name: str, code: str = "PROVIDER_ERROR") -> None:
        sanitized = str(message)
        # 1. Redact configured API key if present
        api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
        if api_key and len(api_key) > 4:
            sanitized = sanitized.replace(api_key, "[REDACTED_API_KEY]")
        # 2. Redact generic key/token/secret patterns
        sanitized = re.sub(
            r'(?i)(?:key|token|secret|password|api_key)[=:\s]+["\']?([a-zA-Z0-9_\-\.]{6,})["\']?',
            r'key=[REDACTED_API_KEY]',
            sanitized,
        )
        super().__init__(sanitized)
        self.provider_name = provider_name
        self.code = code


# ------------------------------------------------------------------------------
# Data Transfer Models for AI Discovery
# ------------------------------------------------------------------------------

class DiscoveredSource(BaseModel):
    """Represents a discovered official government source document."""
    url: str
    title: str
    publisher: str
    document_identifier: Optional[str] = None
    publication_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    raw_content: str
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNKNOWN
    effective_date_status: EffectiveDateStatus = EffectiveDateStatus.UNKNOWN


class ExtractedCandidatePayload(BaseModel):
    """Structured candidate policy statement extracted by AI."""
    title: str
    candidate_type: CandidateType
    candidate_text_en: str
    candidate_text_hi: str
    normalized_concept: str
    source_url: str
    source_title: str
    source_publisher: str
    source_document_identifier: Optional[str] = None
    source_publication_date: Optional[datetime] = None
    source_effective_date: Optional[datetime] = None
    source_excerpt: str
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    confidence_explanation: Optional[str] = None
    uncertainty_notes: Optional[str] = None
    questions_for_reviewer: List[str] = Field(default_factory=list)
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNKNOWN
    effective_date_status: EffectiveDateStatus = EffectiveDateStatus.UNKNOWN
    conflict_detected: bool = False
    conflict_details_json: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------------------------
# Base Provider Abstract Interface
# ------------------------------------------------------------------------------

class BasePolicyDiscoveryProvider(ABC):
    """Abstract base class for policy discovery and extraction providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the AI provider."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the specific model."""
        ...

    @abstractmethod
    async def discover_sources(self, scheme_code: str) -> List[DiscoveredSource]:
        """Discover relevant official government sources for the given scheme."""
        ...

    @abstractmethod
    async def extract_candidates(
        self, scheme_code: str, sources: List[DiscoveredSource]
    ) -> List[ExtractedCandidatePayload]:
        """Extract candidate policy statements from discovered official sources."""
        ...


# ------------------------------------------------------------------------------
# Mock / Controlled Development Provider
# ------------------------------------------------------------------------------

class MockPolicyDiscoveryProvider(BasePolicyDiscoveryProvider):
    """High-fidelity development provider with official GoI source intelligence.
    
    Provides deterministic, reproducible, and verifiable discovery scenarios for
    PM-KISAN and Sukanya Samriddhi Yojana (SSY), including:
    - Official domain match provenance (.gov.in / .nic.in)
    - Procedural clarifications & e-KYC updates
    - Apparent multi-source conflict scenarios
    - Effective date vs publication date distinction
    """

    @property
    def provider_name(self) -> str:
        return "MOCK_GOV_DISCOVERY_AGENT"

    @property
    def model_name(self) -> str:
        return "mock-statutory-agent-v1"

    async def discover_sources(self, scheme_code: str) -> List[DiscoveredSource]:
        code = scheme_code.upper().strip()
        now = datetime.now(timezone.utc)

        if code == "PM_KISAN":
            return [
                DiscoveredSource(
                    url="https://pmkisan.gov.in/Documents/OperationalGuidelines_2024_Update.pdf",
                    title="PM-KISAN Operational Guidelines - Mandatory Aadhaar Seeding and e-KYC Protocol",
                    publisher="Department of Agriculture & Farmers Welfare, Ministry of Agriculture",
                    document_identifier="DOA/PMK/2024/CIR-08",
                    publication_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
                    effective_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
                    raw_content=(
                        "All eligible landholder farmer families must complete biometric or OTP-based e-KYC. "
                        "Bank accounts receiving the financial benefit of Rs. 6000 per annum must be strictly "
                        "Aadhaar-seeded with active Direct Benefit Transfer (DBT) enablement. Non-seeded accounts "
                        "shall not receive subsequent tranches until verification is completed."
                    ),
                    provenance_status=ProvenanceStatus.OFFICIAL_DOMAIN_MATCH,
                    effective_date_status=EffectiveDateStatus.CONFIRMED,
                ),
                DiscoveredSource(
                    url="https://agricoop.nic.in/gazette/pmkisan_exclusion_amendment_2023.pdf",
                    title="Gazette Notification on Exclusion Criteria for Institutional Landholders & Trusts",
                    publisher="Ministry of Agriculture and Farmers Welfare",
                    document_identifier="GSR-412(E)-2023",
                    publication_date=datetime(2023, 11, 20, tzinfo=timezone.utc),
                    effective_date=datetime(2023, 12, 1, tzinfo=timezone.utc),
                    raw_content=(
                        "It is clarified that agricultural land held under religious or charitable trusts "
                        "does not qualify as farmer family holding for PM-KISAN, irrespective of tenancy "
                        "arrangements, unless the individual tenant holds independent revenue ownership rights."
                    ),
                    provenance_status=ProvenanceStatus.OFFICIAL_DOMAIN_MATCH,
                    effective_date_status=EffectiveDateStatus.CONFIRMED,
                ),
                DiscoveredSource(
                    url="https://upbhulekh.gov.in/circulars/land_seeding_timeline_conflict.pdf",
                    title="State Revenue Council Advisory on Land Mutation Records Integration for PM-KISAN",
                    publisher="State Revenue Department / PM-KISAN State Nodal Cell",
                    document_identifier="REV/PMK-MUT/2024/03",
                    publication_date=datetime(2024, 3, 5, tzinfo=timezone.utc),
                    effective_date=None,  # Effective date is pending state gazette concurrence
                    raw_content=(
                        "Joint family landholdings where mutation is pending before the Tehsildar Court "
                        "may be temporarily registered for verification with provisional Khatauni extract. "
                        "[NOTE: This appears to conflict with Central Guideline Clause 4.2 requiring final registered mutation]."
                    ),
                    provenance_status=ProvenanceStatus.OFFICIAL_DOMAIN_MATCH,
                    effective_date_status=EffectiveDateStatus.UNKNOWN,
                ),
            ]

        elif code in ("SSY", "SUKANYA_SAMRIDDHI"):
            return [
                DiscoveredSource(
                    url="https://dea.gov.in/sites/default/files/SSY_Scheme_Amendment_Notification_2024.pdf",
                    title="Sukanya Samriddhi Account (Amendment) Scheme, 2024 - Clarification on Adopted Children & Medical Grounds",
                    publisher="Department of Economic Affairs, Ministry of Finance",
                    document_identifier="G.S.R. 118(E)",
                    publication_date=datetime(2024, 2, 12, tzinfo=timezone.utc),
                    effective_date=datetime(2024, 4, 1, tzinfo=timezone.utc),
                    raw_content=(
                        "Where an account is opened for an adopted girl child, the valid adoption deed "
                        "executed under the Hindu Adoptions and Maintenance Act, 1956 or court order under "
                        "the Juvenile Justice (Care and Protection of Children) Act, 2015 shall serve as conclusive "
                        "proof of legal guardianship. Premature closure shall be permitted on medical grounds "
                        "of life-threatening illnesses upon certification by an authorized Government Medical Officer."
                    ),
                    provenance_status=ProvenanceStatus.OFFICIAL_DOMAIN_MATCH,
                    effective_date_status=EffectiveDateStatus.CONFIRMED,
                ),
                DiscoveredSource(
                    url="https://indiapost.gov.in/financial/ssy_q4_interest_rate_circular.pdf",
                    title="National Savings Schemes Interest Rate Declaration for Q4 FY 2023-24",
                    publisher="Department of Economic Affairs, Budget Division, Ministry of Finance",
                    document_identifier="F.No.1/4/2019-NS",
                    publication_date=datetime(2023, 12, 29, tzinfo=timezone.utc),
                    effective_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    raw_content=(
                        "The rate of interest on deposits made under the Sukanya Samriddhi Account Scheme "
                        "shall be 8.2% (eight point two percent) per annum for the fourth quarter of Financial Year 2023-24 "
                        "commencing on 1st January, 2024 and ending on 31st March, 2024."
                    ),
                    provenance_status=ProvenanceStatus.OFFICIAL_DOMAIN_MATCH,
                    effective_date_status=EffectiveDateStatus.CONFIRMED,
                ),
            ]

        return []

    async def extract_candidates(
        self, scheme_code: str, sources: List[DiscoveredSource]
    ) -> List[ExtractedCandidatePayload]:
        code = scheme_code.upper().strip()
        candidates: List[ExtractedCandidatePayload] = []

        if code == "PM_KISAN":
            candidates.append(
                ExtractedCandidatePayload(
                    title="Mandatory Biometric/OTP e-KYC and Direct Benefit Transfer (DBT) Account Seeding",
                    candidate_type=CandidateType.PROCEDURAL_REQUIREMENT,
                    candidate_text_en=(
                        "All applicant farmers must complete mandatory e-KYC authentication and maintain "
                        "an active Aadhaar-seeded bank account enabled for Direct Benefit Transfer."
                    ),
                    candidate_text_hi=(
                        "सभी पात्र किसान परिवारों के लिए अनिवार्य बायोमेट्रिक या ओटीपी आधारित ई-केवाईसी पूरा करना "
                        "और डायरेक्ट बेनिफिट ट्रांसफर (डीबीटी) सक्षम आधार से जुड़ा बैंक खाता होना आवश्यक है।"
                    ),
                    normalized_concept="farmer.procedural.ekyc_and_dbt_seeding",
                    source_url="https://pmkisan.gov.in/Documents/OperationalGuidelines_2024_Update.pdf",
                    source_title="PM-KISAN Operational Guidelines - Mandatory Aadhaar Seeding and e-KYC Protocol",
                    source_publisher="Department of Agriculture & Farmers Welfare, Ministry of Agriculture",
                    source_document_identifier="DOA/PMK/2024/CIR-08",
                    source_publication_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
                    source_effective_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
                    source_excerpt=(
                        "All eligible landholder farmer families must complete biometric or OTP-based e-KYC. "
                        "Bank accounts receiving the financial benefit must be strictly Aadhaar-seeded with active DBT enablement."
                    ),
                    extraction_confidence=0.94,
                    confidence_explanation="High confidence: Explicit statutory circular from central nodal ministry with specific circular reference.",
                    uncertainty_notes="Requires state-level bank integration verification.",
                    questions_for_reviewer=[
                        "Does this constitute an eligibility condition or a pre-disbursement verification gate?",
                        "Should failure of e-KYC result in temporary hold rather than total disqualification?",
                    ],
                    provenance_status=ProvenanceStatus.OFFICIAL_DOMAIN_MATCH,
                    effective_date_status=EffectiveDateStatus.CONFIRMED,
                    conflict_detected=False,
                )
            )

            candidates.append(
                ExtractedCandidatePayload(
                    title="Exclusion of Religious and Charitable Trusts from Agricultural Family Landholdings",
                    candidate_type=CandidateType.EXCLUSION,
                    candidate_text_en=(
                        "Agricultural land registered in the name of religious, charitable, or educational trusts "
                        "is excluded from PM-KISAN family entitlement calculations, unless the cultivator possesses "
                        "separate, personal statutory revenue title."
                    ),
                    candidate_text_hi=(
                        "धार्मिक, धर्मार्थ या शैक्षणिक ट्रस्टों के नाम पर दर्ज कृषि भूमि को पीएम-किसान परिवार पात्रता "
                        "गणना से बाहर रखा गया है, जब तक कि काश्तकार के पास व्यक्तिगत वैधानिक राजस्व स्वामित्व न हो।"
                    ),
                    normalized_concept="family.exclusion.trust_institutional_land",
                    source_url="https://agricoop.nic.in/gazette/pmkisan_exclusion_amendment_2023.pdf",
                    source_title="Gazette Notification on Exclusion Criteria for Institutional Landholders & Trusts",
                    source_publisher="Ministry of Agriculture and Farmers Welfare",
                    source_document_identifier="GSR-412(E)-2023",
                    source_publication_date=datetime(2023, 11, 20, tzinfo=timezone.utc),
                    source_effective_date=datetime(2023, 12, 1, tzinfo=timezone.utc),
                    source_excerpt=(
                        "It is clarified that agricultural land held under religious or charitable trusts "
                        "does not qualify as farmer family holding for PM-KISAN."
                    ),
                    extraction_confidence=0.91,
                    confidence_explanation="Official gazette publication explicitly resolving an exclusion ambiguity.",
                    uncertainty_notes="Distinguishes institutional ownership from individual cultivator tenancies.",
                    questions_for_reviewer=[
                        "Confirm whether this applies retrospectively to existing registered applicants or only forward.",
                    ],
                    provenance_status=ProvenanceStatus.OFFICIAL_DOMAIN_MATCH,
                    effective_date_status=EffectiveDateStatus.CONFIRMED,
                    conflict_detected=False,
                )
            )

            candidates.append(
                ExtractedCandidatePayload(
                    title="Provisional Registration for Pending Mutation Landholdings (Potential State Conflict)",
                    candidate_type=CandidateType.ELIGIBILITY_CONDITION,
                    candidate_text_en=(
                        "Provisional registration permitted for heirs with pending mutation cases in revenue courts, "
                        "subject to conditional certification by Tehsildar."
                    ),
                    candidate_text_hi=(
                        "तहसीलदार द्वारा सशर्त प्रमाणीकरण के अधीन, राजस्व न्यायालयों में लंबित दाखिल-खारिज मामलों वाले वारिसों "
                        "के लिए अनंतिम पंजीकरण की अनुमति दी जा सकती है।"
                    ),
                    normalized_concept="farmer.land.provisional_mutation_allowance",
                    source_url="https://upbhulekh.gov.in/circulars/land_seeding_timeline_conflict.pdf",
                    source_title="State Revenue Council Advisory on Land Mutation Records Integration for PM-KISAN",
                    source_publisher="State Revenue Department / PM-KISAN State Nodal Cell",
                    source_document_identifier="REV/PMK-MUT/2024/03",
                    source_publication_date=datetime(2024, 3, 5, tzinfo=timezone.utc),
                    source_effective_date=None,
                    source_excerpt=(
                        "Joint family landholdings where mutation is pending before the Tehsildar Court "
                        "may be temporarily registered for verification with provisional Khatauni extract."
                    ),
                    extraction_confidence=0.68,
                    confidence_explanation="Moderate confidence: State advisory appears to conflict with Central Operational Guidelines Clause 4.2.",
                    uncertainty_notes="Potential federal-state regulatory conflict regarding final title requirement.",
                    questions_for_reviewer=[
                        "Does central PM-KISAN guidelines recognize state-level provisional mutation for benefit disbursement?",
                        "Should this candidate be rejected or held under NEEDS_CLARIFICATION until central Ministry concurrence?",
                    ],
                    provenance_status=ProvenanceStatus.OFFICIAL_DOMAIN_MATCH,
                    effective_date_status=EffectiveDateStatus.UNKNOWN,
                    conflict_detected=True,
                    conflict_details_json={
                        "conflicting_sources": [
                            {
                                "source": "Central Operational Guidelines Clause 4.2",
                                "rule": "Requires fully updated and mutated land title in state revenue ledger.",
                            },
                            {
                                "source": "State Revenue Advisory REV/PMK-MUT/2024/03",
                                "rule": "Allows provisional registration on pending mutation.",
                            },
                        ],
                        "apparent_conflict": "Provisional vs Final mutation title requirement.",
                    },
                )
            )

        elif code in ("SSY", "SUKANYA_SAMRIDDHI"):
            candidates.append(
                ExtractedCandidatePayload(
                    title="Adoption Deed and Court Order Verification for Legal Guardianship in SSY Accounts",
                    candidate_type=CandidateType.DOCUMENTATION_REQUIREMENT,
                    candidate_text_en=(
                        "For an adopted girl child, a registered adoption deed under the Hindu Adoptions and Maintenance Act, "
                        "1956 or a valid court order under the Juvenile Justice Act, 2015 serves as statutory proof of legal guardianship."
                    ),
                    candidate_text_hi=(
                        "गोद ली गई बालिका के लिए, हिंदू दत्तक ग्रहण और भरण-पोषण अधिनियम, 1956 के तहत पंजीकृत गोदनामा "
                        "या किशोर न्याय अधिनियम, 2015 के तहत वैध अदालती आदेश कानूनी अभिभावकता का वैधानिक प्रमाण होगा।"
                    ),
                    normalized_concept="girl_child.guardian.adoption_deed_requirement",
                    source_url="https://dea.gov.in/sites/default/files/SSY_Scheme_Amendment_Notification_2024.pdf",
                    source_title="Sukanya Samriddhi Account (Amendment) Scheme, 2024",
                    source_publisher="Department of Economic Affairs, Ministry of Finance",
                    source_document_identifier="G.S.R. 118(E)",
                    source_publication_date=datetime(2024, 2, 12, tzinfo=timezone.utc),
                    source_effective_date=datetime(2024, 4, 1, tzinfo=timezone.utc),
                    source_excerpt=(
                        "Where an account is opened for an adopted girl child, the valid adoption deed executed under "
                        "the Hindu Adoptions and Maintenance Act, 1956 or court order under the Juvenile Justice Act, 2015 "
                        "shall serve as conclusive proof of legal guardianship."
                    ),
                    extraction_confidence=0.96,
                    confidence_explanation="High confidence: Formal Ministry of Finance statutory amendment notification.",
                    uncertainty_notes="Requires legal document upload verification by authorized post office / bank officer.",
                    questions_for_reviewer=[
                        "Does the current verification document list include adoption deed under JJ Act?",
                    ],
                    provenance_status=ProvenanceStatus.OFFICIAL_DOMAIN_MATCH,
                    effective_date_status=EffectiveDateStatus.CONFIRMED,
                    conflict_detected=False,
                )
            )

            candidates.append(
                ExtractedCandidatePayload(
                    title="Premature Closure Provision on Medical Grounds of Life-Threatening Diseases",
                    candidate_type=CandidateType.BENEFIT_PARAMETER,
                    candidate_text_en=(
                        "Premature closure of the Sukanya Samriddhi Account is permissible on medical grounds "
                        "for treatment of life-threatening diseases of the account holder, subject to certification "
                        "by an authorized Government Medical Officer."
                    ),
                    candidate_text_hi=(
                        "खाताधारक बालिका की जानलेवा बीमारियों के इलाज के लिए चिकित्सा आधार पर सुकन्या समृद्धि खाते को "
                        "समय से पहले बंद करने की अनुमति है, जो अधिकृत सरकारी चिकित्सा अधिकारी के प्रमाणन के अधीन है।"
                    ),
                    normalized_concept="account.closure.medical_grounds_exception",
                    source_url="https://dea.gov.in/sites/default/files/SSY_Scheme_Amendment_Notification_2024.pdf",
                    source_title="Sukanya Samriddhi Account (Amendment) Scheme, 2024",
                    source_publisher="Department of Economic Affairs, Ministry of Finance",
                    source_document_identifier="G.S.R. 118(E)",
                    source_publication_date=datetime(2024, 2, 12, tzinfo=timezone.utc),
                    source_effective_date=datetime(2024, 4, 1, tzinfo=timezone.utc),
                    source_excerpt=(
                        "Premature closure shall be permitted on medical grounds of life-threatening illnesses upon certification "
                        "by an authorized Government Medical Officer."
                    ),
                    extraction_confidence=0.93,
                    confidence_explanation="High confidence: Direct statutory clause in 2024 amendment rules.",
                    uncertainty_notes="Procedural guideline for acceptable medical certificate formats.",
                    questions_for_reviewer=[
                        "Confirm whether medical closure rules belong to account servicing rather than initial opening eligibility.",
                    ],
                    provenance_status=ProvenanceStatus.OFFICIAL_DOMAIN_MATCH,
                    effective_date_status=EffectiveDateStatus.CONFIRMED,
                    conflict_detected=False,
                )
            )

        return candidates


# ------------------------------------------------------------------------------
# Gemini Provider (Live LLM Integration - NO MOCK FALLBACK)
# ------------------------------------------------------------------------------

class GeminiPolicyDiscoveryProvider(BasePolicyDiscoveryProvider):
    """Live AI provider calling Google Gemini API without mock fallback.
    
    Security & Reliability Invariants:
    - Never falls back to mock data on error, timeout, or malformed response.
    - Never logs API keys or credentials.
    - Surfaces failure cleanly as PolicyDiscoveryProviderError.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise PolicyDiscoveryProviderError(
                message="Gemini API key is required when AI_PROVIDER=gemini",
                provider_name="GOOGLE_GEMINI_POLICY_DISCOVERY",
                code="MISSING_API_KEY",
            )
        self._api_key = api_key
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "GOOGLE_GEMINI_POLICY_DISCOVERY"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def discover_sources(self, scheme_code: str) -> List[DiscoveredSource]:
        """Discover official sources via live Gemini call.
        
        Strictly raises PolicyDiscoveryProviderError on failure or timeout.
        DOES NOT FALL BACK TO MOCK DATA.
        """
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self._api_key)
            prompt = (
                f"You are a statutory policy research assistant. "
                f"List official Government of India websites, gazettes, and circulars for scheme '{scheme_code}'. "
                f"Return JSON array of sources with url, title, publisher, raw_content."
            )
            response = await client.aio.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            if not response.text:
                raise PolicyDiscoveryProviderError(
                    message="Gemini returned empty response for source discovery",
                    provider_name=self.provider_name,
                    code="EMPTY_RESPONSE",
                )
            import json
            data = json.loads(response.text)
            if not isinstance(data, list):
                raise PolicyDiscoveryProviderError(
                    message="Gemini response is not a JSON array of sources",
                    provider_name=self.provider_name,
                    code="MALFORMED_OUTPUT",
                )
            sources: List[DiscoveredSource] = []
            for item in data:
                sources.append(
                    DiscoveredSource(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        publisher=item.get("publisher", ""),
                        document_identifier=item.get("document_identifier"),
                        raw_content=item.get("raw_content", ""),
                        provenance_status=ProvenanceStatus.SOURCE_RETRIEVED,
                        effective_date_status=EffectiveDateStatus.UNKNOWN,
                    )
                )
            return sources
        except PolicyDiscoveryProviderError:
            raise
        except Exception as exc:
            sanitized = str(exc).replace(self._api_key, "[REDACTED_API_KEY]")
            logger.error(
                "Gemini source discovery failed for scheme '%s': %s",
                scheme_code,
                sanitized,
            )
            raise PolicyDiscoveryProviderError(
                message=f"Live Gemini source discovery failed: {sanitized}",
                provider_name=self.provider_name,
                code="API_FAILURE",
            ) from None

    async def extract_candidates(
        self, scheme_code: str, sources: List[DiscoveredSource]
    ) -> List[ExtractedCandidatePayload]:
        """Extract candidate policy statements via live Gemini call.
        
        Strictly raises PolicyDiscoveryProviderError on failure or timeout.
        DOES NOT FALL BACK TO MOCK DATA.
        """
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self._api_key)
            sources_summary = "\n".join([f"- {s.title} ({s.url}): {s.raw_content[:300]}" for s in sources])
            prompt = (
                f"You are a welfare policy extraction agent. From the following official sources for {scheme_code}:\n"
                f"{sources_summary}\n\n"
                f"Extract candidate policy statements as JSON array of objects with keys: "
                f"title, candidate_type, candidate_text_en, candidate_text_hi, normalized_concept, "
                f"source_url, source_title, source_publisher, source_excerpt, extraction_confidence."
            )
            response = await client.aio.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            if not response.text:
                raise PolicyDiscoveryProviderError(
                    message="Gemini returned empty response for candidate extraction",
                    provider_name=self.provider_name,
                    code="EMPTY_RESPONSE",
                )
            import json
            data = json.loads(response.text)
            if not isinstance(data, list):
                raise PolicyDiscoveryProviderError(
                    message="Gemini candidate extraction did not return a valid list",
                    provider_name=self.provider_name,
                    code="MALFORMED_OUTPUT",
                )
            candidates: List[ExtractedCandidatePayload] = []
            for item in data:
                c_type_str = item.get("candidate_type", "ELIGIBILITY_CONDITION")
                try:
                    c_type = CandidateType(c_type_str)
                except ValueError:
                    c_type = CandidateType.ELIGIBILITY_CONDITION
                candidates.append(
                    ExtractedCandidatePayload(
                        title=item.get("title", f"Candidate for {scheme_code}"),
                        candidate_type=c_type,
                        candidate_text_en=item.get("candidate_text_en", ""),
                        candidate_text_hi=item.get("candidate_text_hi", ""),
                        normalized_concept=item.get("normalized_concept", f"{scheme_code.lower()}.extracted"),
                        source_url=item.get("source_url", ""),
                        source_title=item.get("source_title", ""),
                        source_publisher=item.get("source_publisher", ""),
                        source_excerpt=item.get("source_excerpt", ""),
                        extraction_confidence=float(item.get("extraction_confidence", 0.7)),
                        provenance_status=ProvenanceStatus.SOURCE_RETRIEVED,
                        effective_date_status=EffectiveDateStatus.UNKNOWN,
                    )
                )
            return candidates
        except PolicyDiscoveryProviderError:
            raise
        except Exception as exc:
            sanitized = str(exc).replace(self._api_key, "[REDACTED_API_KEY]")
            logger.error(
                "Gemini candidate extraction failed for scheme '%s': %s",
                scheme_code,
                sanitized,
            )
            raise PolicyDiscoveryProviderError(
                message=f"Live Gemini candidate extraction failed: {sanitized}",
                provider_name=self.provider_name,
                code="API_FAILURE",
            ) from None


# ------------------------------------------------------------------------------
# Provider Factory
# ------------------------------------------------------------------------------

def get_policy_discovery_provider() -> BasePolicyDiscoveryProvider:
    """Factory creating configured AI Policy Discovery Provider.
    
    CRITICAL ARCHITECTURAL RULE:
    - The mock provider is available ONLY when explicitly configured (e.g. AI_PROVIDER=mock).
    - When AI_PROVIDER=gemini, the real Gemini provider is used without silent mock fallback.
    """
    provider_type = (
        getattr(settings, "AI_PROVIDER", None)
        or getattr(settings, "AI_DISCOVERY_PROVIDER", "mock")
        or "mock"
    ).lower().strip()

    if provider_type == "mock":
        return MockPolicyDiscoveryProvider()

    if provider_type == "gemini":
        gemini_key = getattr(settings, "GEMINI_API_KEY", None) or ""
        model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        return GeminiPolicyDiscoveryProvider(api_key=gemini_key, model_name=model)

    raise ValueError(f"Unsupported AI discovery provider: '{provider_type}'. Must be 'mock' or 'gemini'.")
