"""Generic Policy-Driven Form Metadata Registry and Resolution Service (Phase G).

Maintains version-aware, declarative policy form metadata specifications for canonical
statutory schemes (PM_KISAN, SSY).

Every form definition:
- Is bound to a specific statutory policy version (e.g. PM_KISAN v3.0-2023, SSY v3.0-2024)
- Organizes fields into policy-driven sections with bilingual titles
- Uses generic field types (TEXT, NUMBER, INTEGER, DECIMAL, DATE, BOOLEAN, SELECT, RADIO, ADDRESS)
- Supports declarative visibility conditions without dynamic code execution
- Supports declarative cross-field validation rules
- Enforces strict validation via validate_policy_form_metadata
- Fails cleanly and safely for unsupported schemes (schemes 3-10) without fabricating rules
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import uuid

from app.schemas.form_metadata import (
    ConditionOperator,
    CrossFieldRule,
    FieldCondition,
    FormEvidenceDefinition,
    FormFieldDefinition,
    FormFieldType,
    FormSectionDefinition,
    PolicyFormMetadata,
)
from app.services.form_metadata_validator import (
    PolicyFormMetadataValidationError,
    validate_policy_form_metadata,
)


class SchemeFormNotSupportedError(Exception):
    """Raised when form metadata is requested for an unsupported or unconfigured scheme."""
    pass


# ==============================================================================
# Canonical Policy Form Metadata Builders
# ==============================================================================

def _build_pm_kisan_v3_form() -> PolicyFormMetadata:
    """Build canonical form metadata for PM-KISAN v3.0-2023 (Active)."""
    sections = [
        FormSectionDefinition(
            section_key="applicant_family",
            title_en="Farmer Family & Landholding Status",
            title_hi="किसान परिवार एवं भूमि स्वामित्व स्थिति",
            description_en="Declaration of cultivable landholding ownership by the applicant farmer family.",
            description_hi="आवेदक किसान परिवार द्वारा कृषि योग्य भूमि के स्वामित्व की घोषणा।",
            display_order=1,
        ),
        FormSectionDefinition(
            section_key="land_details",
            title_en="Land Specifications & Cut-Off Criteria",
            title_hi="भूमि विवरण एवं कट-ऑफ मानदंड",
            description_en="Total cultivable area and statutory 01.02.2019 ownership cut-off compliance.",
            description_hi="कुल कृषि योग्य क्षेत्रफल तथा वैधानिक 01.02.2019 कट-ऑफ अनुपालन।",
            display_order=2,
        ),
        FormSectionDefinition(
            section_key="statutory_exclusions",
            title_en="Statutory Exclusion Categories",
            title_hi="वैधानिक बहिष्करण श्रेणियां",
            description_en="Mandatory declarations verifying that no family member falls under statutory exclusion criteria.",
            description_hi="यह सुनिश्चित करने के लिए अनिवार्य घोषणा कि परिवार का कोई सदस्य बहिष्करण के अंतर्गत नहीं आता।",
            display_order=3,
        ),
    ]

    fields = [
        # Section 1: applicant_family
        FormFieldDefinition(
            field_key="family.owns_cultivable_land",
            claim_type="family.owns_cultivable_land",
            field_type="boolean",
            required=True,
            label_en="Family Cultivable Landholding",
            label_hi="परिवार की कृषि योग्य भूमि",
            help_text_en="Does the beneficiary family hold cultivable land according to official revenue records?",
            help_text_hi="क्या परिवार के पास आधिकारिक राजस्व अभिलेखों के अनुसार कृषि योग्य भूमि का स्वामित्व है?",
            validation_message_en="Farmer family must hold cultivable land to be eligible.",
            validation_message_hi="पात्र होने के लिए किसान परिवार के पास कृषि योग्य भूमि होना आवश्यक है।",
            section_key="applicant_family",
            display_order=1,
            default_value=True,
            associated_evidence_type="LAND_RECORD",
        ),
        # Section 2: land_details
        FormFieldDefinition(
            field_key="land.total_land_area_hectares",
            claim_type="land.total_land_area_hectares",
            field_type="decimal",
            required=True,
            label_en="Total Land Area (Hectares)",
            label_hi="कुल भूमि का क्षेत्रफल (हेक्टेयर)",
            help_text_en="Enter total cultivable area in hectares as recorded in land revenue record (e.g. 1.5)",
            help_text_hi="भू-अभिलेख के अनुसार कुल कृषि योग्य क्षेत्रफल हेक्टेयर में दर्ज करें (उदा. 1.5)",
            validation_message_en="Land area must be greater than zero.",
            validation_message_hi="भूमि का क्षेत्रफल शून्य से अधिक होना चाहिए।",
            section_key="land_details",
            display_order=2,
            min_value=0.01,
            max_value=1000.0,
            step=0.01,
            default_value=1.5,
            associated_evidence_type="LAND_RECORD",
        ),
        FormFieldDefinition(
            field_key="land.transferred_after_cutoff",
            claim_type="land.transferred_after_cutoff",
            field_type="boolean",
            required=True,
            label_en="Land Acquired After 01-Feb-2019?",
            label_hi="क्या भूमि 01-फरवरी-2019 के बाद प्राप्त हुई?",
            help_text_en="Was landholding ownership transferred to the applicant after the statutory cut-off date of 01.02.2019?",
            help_text_hi="क्या भूमि स्वामित्व 01.02.2019 की कट-ऑफ तिथि के बाद हस्तांतरित हुआ था?",
            section_key="land_details",
            display_order=3,
            default_value=False,
            associated_evidence_type="LAND_RECORD",
        ),
        FormFieldDefinition(
            field_key="land.acquired_via_succession",
            claim_type="land.acquired_via_succession",
            field_type="boolean",
            required=True,
            label_en="Acquired Strictly Via Succession / Inheritance?",
            label_hi="क्या भूमि उत्तराधिकार के माध्यम से प्राप्त हुई?",
            help_text_en="If ownership was transferred after 01.02.2019, was it acquired strictly via succession on death of landowner?",
            help_text_hi="यदि कट-ऑफ के बाद प्राप्त हुई, क्या यह पूर्व भूस्वामी की मृत्यु पर उत्तराधिकार द्वारा प्राप्त हुई?",
            section_key="land_details",
            display_order=4,
            default_value=False,
            associated_evidence_type="LAND_RECORD",
            condition=FieldCondition(
                field_key="land.transferred_after_cutoff",
                operator=ConditionOperator.EQUALS,
                value=True,
            ),
        ),
        # Section 3: statutory_exclusions
        FormFieldDefinition(
            field_key="family.is_institutional_landholder",
            claim_type="family.is_institutional_landholder",
            field_type="boolean",
            required=True,
            label_en="Institutional Landholder Exemption",
            label_hi="संस्थागत भूमि धारक स्थिति",
            help_text_en="Is the agricultural land held institutionally (by trust, society, or corporate body)?",
            help_text_hi="क्या भूमि संस्थागत रूप से (ट्रस्ट, समिति या कंपनी द्वारा) धारित है?",
            section_key="statutory_exclusions",
            display_order=5,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_constitutional_post_holder",
            claim_type="family.has_constitutional_post_holder",
            field_type="boolean",
            required=True,
            label_en="Constitutional Post Holder Exemption",
            label_hi="संवैधानिक पद धारक स्थिति",
            help_text_en="Does any member of the family hold or have held a constitutional post?",
            help_text_hi="क्या परिवार का कोई सदस्य पूर्व या वर्तमान में किसी संवैधानिक पद पर रहा है?",
            section_key="statutory_exclusions",
            display_order=6,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_public_representative",
            claim_type="family.has_public_representative",
            field_type="boolean",
            required=True,
            label_en="Elected Public Representative Exemption",
            label_hi="निर्वाचित जन प्रतिनिधि स्थिति",
            help_text_en="Is any family member a former/present MP, MLA, MLC, Mayor, or District Panchayat Chairperson?",
            help_text_hi="क्या कोई सदस्य पूर्व या वर्तमान सांसद, विधायक, महापौर या जिला पंचायत अध्यक्ष है?",
            section_key="statutory_exclusions",
            display_order=7,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_disqualified_government_employee",
            claim_type="family.has_disqualified_government_employee",
            field_type="boolean",
            required=True,
            label_en="Government Service Exemption",
            label_hi="सरकारी सेवा बहिष्करण स्थिति",
            help_text_en="Is any family member a serving/retired officer/employee of Central/State Govt or PSEs (excluding Class IV / MTS)?",
            help_text_hi="क्या परिवार का कोई सदस्य सरकारी/सार्वजनिक क्षेत्र में सेवारत या सेवानिवृत्त है (चतुर्थ श्रेणी/MTS को छोड़कर)?",
            section_key="statutory_exclusions",
            display_order=8,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_pensioner_above_ten_thousand",
            claim_type="family.has_pensioner_above_ten_thousand",
            field_type="boolean",
            required=True,
            label_en="Pension Above ₹10,000 / Month Exemption",
            label_hi="₹10,000/माह से अधिक पेंशन बहिष्करण",
            help_text_en="Does any retired family pensioner draw ₹10,000 or more per month (excluding Class IV / MTS)?",
            help_text_hi="क्या परिवार का कोई पेंशनभोगी ₹10,000 या अधिक मासिक पेंशन प्राप्त करता है (चतुर्थ श्रेणी को छोड़कर)?",
            section_key="statutory_exclusions",
            display_order=9,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_income_tax_payer",
            claim_type="family.has_income_tax_payer",
            field_type="boolean",
            required=True,
            label_en="Income Tax Assessment Exemption",
            label_hi="आयकर दाता बहिष्करण स्थिति",
            help_text_en="Has any member of the family filed or paid Income Tax in the last assessment year?",
            help_text_hi="क्या परिवार के किसी सदस्य ने पिछले निर्धारण वर्ष में आयकर का भुगतान किया है?",
            section_key="statutory_exclusions",
            display_order=10,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_registered_practicing_professional",
            claim_type="family.has_registered_practicing_professional",
            field_type="boolean",
            required=True,
            label_en="Registered Professional Exemption",
            label_hi="पंजीकृत पेशेवर बहिष्करण स्थिति",
            help_text_en="Is any member a practicing Doctor, Engineer, Lawyer, Chartered Accountant, or Architect?",
            help_text_hi="क्या कोई सदस्य पंजीकृत डॉक्टर, इंजीनियर, वकील, सीए या वास्तुकार के रूप में कार्यरत है?",
            section_key="statutory_exclusions",
            display_order=11,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.is_nri",
            claim_type="family.is_nri",
            field_type="boolean",
            required=True,
            label_en="Non-Resident Indian (NRI) Status",
            label_hi="अनिवासी भारतीय (NRI) स्थिति",
            help_text_en="Is the applicant farmer family an NRI family under the provisions of the Income Tax Act?",
            help_text_hi="क्या आवेदक परिवार आयकर अधिनियम के तहत अनिवासी भारतीय (NRI) परिवार है?",
            section_key="statutory_exclusions",
            display_order=12,
            default_value=False,
        ),
    ]

    evidence_types = [
        FormEvidenceDefinition(
            evidence_type="LAND_RECORD",
            label_en="Land Ownership Record / RoR (7/12, Khasra, Khatauni)",
            label_hi="भू-अभिलेख / खसरा-खतौनी / 7-12 नकल",
            description_en="Certified revenue record extract demonstrating applicant cultivable land ownership",
            description_hi="आवेदक के नाम कृषि योग्य भूमि स्वामित्व दर्शाने वाला प्रमाणित राजस्व अभिलेख",
            mandatory=True,
            associated_field_keys=[
                "family.owns_cultivable_land",
                "land.total_land_area_hectares",
                "land.transferred_after_cutoff",
            ],
        ),
        FormEvidenceDefinition(
            evidence_type="AADHAAR",
            label_en="Aadhaar Card (Applicant Identification)",
            label_hi="आधार कार्ड (आवेदक पहचान प्रमाण)",
            description_en="Valid Aadhaar card of the primary farmer applicant",
            description_hi="मुख्य किसान आवेदक का वैध आधार कार्ड",
            mandatory=True,
        ),
        FormEvidenceDefinition(
            evidence_type="BANK_PASSBOOK",
            label_en="Bank Account Passbook / Statement",
            label_hi="बैंक खाता पासबुक / विवरण",
            description_en="Bank passbook front page or statement showing IFSC and DBT-enabled account number",
            description_hi="डीबीटी-सक्षम बैंक खाता संख्या और आईएफएससी दर्शाने वाली पासबुक की प्रति",
            mandatory=True,
        ),
    ]

    return PolicyFormMetadata(
        scheme_code="PM_KISAN",
        policy_version_code="v3.0-2023",
        effective_from="2023-01-01",
        sections=sections,
        fields=fields,
        evidence_types=evidence_types,
        cross_field_rules=[],
    )


def _build_pm_kisan_v2_form() -> PolicyFormMetadata:
    """Build form metadata for PM-KISAN v2.0-2019."""
    meta = _build_pm_kisan_v3_form()
    meta.policy_version_code = "v2.0-2019"
    meta.effective_from = "2019-04-01"
    return meta


def _build_pm_kisan_v1_form() -> PolicyFormMetadata:
    """Build form metadata for PM-KISAN v1.0-2018 (Small and Marginal Farmers <= 2ha)."""
    meta = _build_pm_kisan_v3_form()
    meta.policy_version_code = "v1.0-2018"
    meta.effective_from = "2018-12-01"
    # In v1.0, maximum cultivable land was 2.0 hectares
    for f in meta.fields:
        if f.field_key == "land.total_land_area_hectares":
            f.max_value = 2.0
            f.help_text_en = "Under PM-KISAN 2018 rules, only Small and Marginal Farmers holding up to 2.0 hectares are eligible."
            f.help_text_hi = "पीएम-किसान 2018 नियमों के तहत, 2.0 हेक्टेयर तक की जोत वाले छोटे और सीमांत किसान ही पात्र हैं।"
    return meta


def _build_ssy_v3_form() -> PolicyFormMetadata:
    """Build canonical form metadata for Sukanya Samriddhi Account (SSY) v3.0-2024 (Active)."""
    sections = [
        FormSectionDefinition(
            section_key="beneficiary_details",
            title_en="Beneficiary Girl Child",
            title_hi="लाभार्थी बालिका का विवरण",
            description_en="Identification and demographic particulars of the girl child.",
            description_hi="बालिका के पहचान एवं जनसांख्यिकीय विवरण।",
            display_order=1,
        ),
        FormSectionDefinition(
            section_key="account_details",
            title_en="Account Opening Particulars",
            title_hi="खाता खोलने का विवरण",
            description_en="Proposed opening date and first-account statutory declaration.",
            description_hi="खाता खोलने की प्रस्तावित तिथि एवं प्रथम खाता घोषणा।",
            display_order=2,
        ),
        FormSectionDefinition(
            section_key="guardian_details",
            title_en="Guardian Legal Status",
            title_hi="अभिभावक की कानूनी स्थिति",
            description_en="Statutory guardianship details (biological parents or court-appointed guardian).",
            description_hi="अभिभावक का कानूनी अधिकार (प्राकृतिक माता-पिता या न्यायालय द्वारा नियुक्त संरक्षक)।",
            display_order=3,
        ),
        FormSectionDefinition(
            section_key="family_limits",
            title_en="Family Account Limits & Exceptions",
            title_hi="परिवार खाता सीमा एवं अपवाद",
            description_en="Statutory ceiling of 2 accounts per family and multiple birth exception declaration.",
            description_hi="प्रति परिवार अधिकतम 2 खातों की वैधानिक सीमा और जुड़वां जन्म अपवाद की स्थिति।",
            display_order=4,
        ),
    ]

    fields = [
        # Section 1: beneficiary_details
        FormFieldDefinition(
            field_key="beneficiary.gender",
            claim_type="beneficiary.gender",
            field_type="select",
            required=True,
            label_en="Beneficiary Gender",
            label_hi="बालिका का लिंग",
            help_text_en="Sukanya Samriddhi Account can strictly be opened for a girl child only",
            help_text_hi="सुकन्या समृद्धि खाता केवल बालिका के नाम से ही खोला जा सकता है",
            validation_message_en="Only female girl children are eligible for SSY.",
            validation_message_hi="सुकन्या समृद्धि योजना के लिए केवल बालिकाएं ही पात्र हैं।",
            section_key="beneficiary_details",
            display_order=1,
            options=[
                {"value": "FEMALE", "label_en": "Female", "label_hi": "बालिका / कन्या", "label": "Female / बालिका"},
                {"value": "MALE", "label_en": "Male", "label_hi": "बालक", "label": "Male / बालक"},
            ],
            default_value="FEMALE",
            associated_evidence_type="BIRTH_CERTIFICATE",
        ),
        FormFieldDefinition(
            field_key="beneficiary.is_indian_resident",
            claim_type="beneficiary.is_indian_resident",
            field_type="boolean",
            required=True,
            label_en="Indian Resident Citizen",
            label_hi="भारतीय निवासी नागरिक",
            help_text_en="Is the girl child an Indian resident citizen residing in India?",
            help_text_hi="क्या बालिका भारत में रहने वाली भारतीय नागरिक है?",
            validation_message_en="Child must be an Indian resident citizen.",
            validation_message_hi="बालिका को भारतीय निवासी नागरिक होना चाहिए।",
            section_key="beneficiary_details",
            display_order=2,
            default_value=True,
        ),
        FormFieldDefinition(
            field_key="beneficiary.date_of_birth",
            claim_type="beneficiary.date_of_birth",
            field_type="date",
            required=True,
            label_en="Girl Child Date of Birth",
            label_hi="बालिका की जन्म तिथि",
            help_text_en="Child must not have attained ten years of age as of proposed account opening date",
            help_text_hi="खाता खोलने की तिथि पर बालिका की आयु 10 वर्ष से अधिक नहीं होनी चाहिए",
            validation_message_en="Valid date of birth required.",
            validation_message_hi="मान्य जन्म तिथि आवश्यक है।",
            section_key="beneficiary_details",
            display_order=3,
            default_value="2020-05-15",
            associated_evidence_type="BIRTH_CERTIFICATE",
        ),
        # Section 2: account_details
        FormFieldDefinition(
            field_key="account.opening_date",
            claim_type="account.opening_date",
            field_type="date",
            required=True,
            label_en="Account Opening Date",
            label_hi="खाता खोलने की तिथि",
            help_text_en="Proposed date of opening the Sukanya Samriddhi Account",
            help_text_hi="सुकन्या समृद्धि खाता खोलने की प्रस्तावित तिथि",
            validation_message_en="Valid opening date required.",
            validation_message_hi="खाता खोलने की मान्य तिथि आवश्यक है।",
            section_key="account_details",
            display_order=4,
            default_value="2026-09-30",
        ),
        FormFieldDefinition(
            field_key="account.is_first_account_for_child",
            claim_type="account.is_first_account_for_child",
            field_type="boolean",
            required=True,
            label_en="First SSY Account for this Child",
            label_hi="इस बालिका का पहला सुकन्या खाता",
            help_text_en="Only one account can be operated in the name of a specific girl child",
            help_text_hi="एक बालिका के नाम पर केवल एक ही खाता संचालित किया जा सकता है",
            validation_message_en="A child cannot have more than one SSY account.",
            validation_message_hi="एक बालिका के नाम पर एक से अधिक सुकन्या खाते नहीं हो सकते।",
            section_key="account_details",
            display_order=5,
            default_value=True,
        ),
        # Section 3: guardian_details
        FormFieldDefinition(
            field_key="guardian.is_natural_guardian",
            claim_type="guardian.is_natural_guardian",
            field_type="boolean",
            required=True,
            label_en="Natural Guardian (Biological Father/Mother)",
            label_hi="प्राकृतिक अभिभावक (माता या पिता)",
            help_text_en="Is the applicant the biological or legal adoptive father/mother?",
            help_text_hi="क्या आवेदक बालिका के जैविक या कानूनी दत्तक माता/पिता हैं?",
            section_key="guardian_details",
            display_order=6,
            default_value=True,
            associated_evidence_type="AADHAAR",
        ),
        FormFieldDefinition(
            field_key="guardian.is_court_appointed_legal_guardian",
            claim_type="guardian.is_court_appointed_legal_guardian",
            field_type="boolean",
            required=False,
            label_en="Court-Appointed Legal Guardian",
            label_hi="न्यायालय नियुक्त कानूनी अभिभावक",
            help_text_en="If not parents, is applicant appointed guardian by a competent court?",
            help_text_hi="यदि माता-पिता नहीं हैं, क्या आवेदक न्यायालय द्वारा नियुक्त संरक्षक हैं?",
            section_key="guardian_details",
            display_order=7,
            default_value=False,
            condition=FieldCondition(
                field_key="guardian.is_natural_guardian",
                operator=ConditionOperator.EQUALS,
                value=False,
            ),
        ),
        # Section 4: family_limits
        FormFieldDefinition(
            field_key="family.active_ssy_accounts_count",
            claim_type="family.active_ssy_accounts_count",
            field_type="integer",
            required=True,
            label_en="Existing Active SSY Accounts in Family",
            label_hi="परिवार में पहले से सक्रिय सुकन्या खाते",
            help_text_en="Maximum 2 accounts per family allowed under statutory scheme rules",
            help_text_hi="योजना नियमों के तहत प्रति परिवार अधिकतम 2 खाते अनुमत हैं",
            validation_message_en="Enter number of existing SSY accounts in family (0 to 5).",
            validation_message_hi="परिवार में मौजूदा सुकन्या खातों की संख्या दर्ज करें (0 से 5)।",
            section_key="family_limits",
            display_order=8,
            min_value=0,
            max_value=5,
            default_value=0,
        ),
        FormFieldDefinition(
            field_key="family.has_multiple_birth_exception",
            claim_type="family.has_multiple_birth_exception",
            field_type="boolean",
            required=False,
            label_en="Multiple Birth Exception (Twins / Triplets)",
            label_hi="जुड़वां / तिड़वां जन्म अपवाद",
            help_text_en="Applicable only if an additional account is sought due to twin/triplet girl births",
            help_text_hi="केवल तभी लागू जब जुड़वां/तिड़वां जन्म के कारण अतिरिक्त खाते की आवश्यकता हो",
            section_key="family_limits",
            display_order=9,
            default_value=False,
            condition=FieldCondition(
                field_key="family.active_ssy_accounts_count",
                operator=ConditionOperator.GREATER_THAN,
                value=0,
            ),
        ),
        FormFieldDefinition(
            field_key="girl_child_age",
            claim_type="girl_child_age",
            field_type="integer",
            required=False,
            label_en="Girl Child Age (Years)",
            label_hi="बालिका की आयु (वर्ष)",
            help_text_en="Completed age in years",
            help_text_hi="पूर्ण वर्ष में आयु",
            section_key="beneficiary_details",
            display_order=10,
            min_value=0,
            max_value=21,
        ),
        FormFieldDefinition(
            field_key="number_of_daughters",
            claim_type="number_of_daughters",
            field_type="integer",
            required=False,
            label_en="Number of Daughters",
            label_hi="बेटियों की संख्या",
            help_text_en="Total number of girl children in family",
            help_text_hi="परिवार में कुल बेटियों की संख्या",
            section_key="family_limits",
            display_order=11,
            min_value=1,
            max_value=10,
        ),
    ]

    evidence_types = [
        FormEvidenceDefinition(
            evidence_type="BIRTH_CERTIFICATE",
            label_en="Girl Child Birth Certificate",
            label_hi="बालिका का जन्म प्रमाण पत्र",
            description_en="Official birth certificate issued by municipal body or Registrar of Births & Deaths",
            description_hi="नगर पालिका या सक्षम जन्म-मृत्यु रजिस्ट्रार द्वारा जारी जन्म प्रमाण पत्र",
            mandatory=True,
            associated_field_keys=["beneficiary.gender", "beneficiary.date_of_birth"],
        ),
        FormEvidenceDefinition(
            evidence_type="AADHAAR",
            label_en="Guardian Identification Proof (Aadhaar / Voter ID)",
            label_hi="अभिभावक पहचान प्रमाण (आधार / मतदाता पहचान पत्र)",
            description_en="Valid identification and residential proof of the natural/legal guardian",
            description_hi="प्राकृतिक अथवा कानूनी अभिभावक का वैध पहचान एवं निवास प्रमाण पत्र",
            mandatory=True,
            associated_field_keys=["guardian.is_natural_guardian"],
        ),
        FormEvidenceDefinition(
            evidence_type="BANK_PASSBOOK",
            label_en="Guardian Bank / Post Office Document",
            label_hi="अभिभावक बैंक अथवा डाकघर पासबुक",
            description_en="Passbook or bank statement copy of the guardian opening the account",
            description_hi="खाता खोलने वाले अभिभावक के बैंक अथवा डाकघर खाते की प्रति",
            mandatory=False,
        ),
    ]

    cross_field_rules = [
        CrossFieldRule(
            rule_id="SSY_MAX_AGE_AT_OPENING",
            rule_type="AGE_AT_DATE",
            primary_field="beneficiary.date_of_birth",
            secondary_field="account.opening_date",
            parameters={"max_age_years": 10},
            message_en="Girl child must not have attained 10 years of age on account opening date.",
            message_hi="खाता खोलने की तिथि पर बालिका की आयु 10 वर्ष से अधिक नहीं होनी चाहिए।",
        ),
        CrossFieldRule(
            rule_id="SSY_OPENING_AFTER_DOB",
            rule_type="DATE_CHRONOLOGY",
            primary_field="account.opening_date",
            secondary_field="beneficiary.date_of_birth",
            operator="GREATER_THAN_OR_EQUAL",
            message_en="Account opening date cannot be prior to the child's date of birth.",
            message_hi="खाता खोलने की तिथि बालिका की जन्म तिथि से पूर्व नहीं हो सकती।",
        ),
    ]

    return PolicyFormMetadata(
        scheme_code="SSY",
        policy_version_code="v3.0-2024",
        effective_from="2024-04-01",
        sections=sections,
        fields=fields,
        evidence_types=evidence_types,
        cross_field_rules=cross_field_rules,
    )


def _build_ssy_v2_form() -> PolicyFormMetadata:
    """Build form metadata for SSY v2.0-2019."""
    meta = _build_ssy_v3_form()
    meta.policy_version_code = "v2.0-2019"
    meta.effective_from = "2019-12-12"
    return meta


def _build_ssy_v1_form() -> PolicyFormMetadata:
    """Build form metadata for SSY v1.0-2016."""
    meta = _build_ssy_v3_form()
    meta.policy_version_code = "v1.0-2016"
    meta.effective_from = "2016-03-18"
    return meta


def _build_pm_kmy_v1_form() -> PolicyFormMetadata:
    """Build canonical form metadata for PM-KMY v1.0-2019."""
    sections = [
        FormSectionDefinition(
            section_key="applicant_demographics",
            title_en="Applicant Demographic & Pension Status",
            title_hi="आवेदक जनसांख्यिकीय एवं पेंशन स्थिति",
            description_en="Verification of farmer entry age and coverage under statutory social security pensions.",
            description_hi="किसान की प्रवेश आयु और वैधानिक सामाजिक सुरक्षा पेंशन के अंतर्गत स्थिति का सत्यापन।",
            display_order=1,
        ),
        FormSectionDefinition(
            section_key="land_details",
            title_en="Landholding & Cut-off Compliance",
            title_hi="भूमि स्वामित्व एवं कट-ऑफ अनुपालन",
            description_en="Cultivable land area specifications and 01.08.2019 land record entry compliance.",
            description_hi="कृषि योग्य भूमि का क्षेत्रफल और 01.08.2019 भूमि रिकॉर्ड प्रविष्टि अनुपालन।",
            display_order=2,
        ),
        FormSectionDefinition(
            section_key="statutory_exclusions",
            title_en="Statutory Exclusion Disclosures",
            title_hi="वैधानिक बहिष्करण प्रकटीकरण",
            description_en="Mandatory declaration verifying no family member falls under economic exclusion criteria.",
            description_hi="अनिवार्य घोषणा कि परिवार का कोई भी सदस्य आर्थिक बहिष्करण मानदंड के तहत नहीं आता।",
            display_order=3,
        ),
    ]

    fields = [
        FormFieldDefinition(
            field_key="applicant.age",
            claim_type="applicant.age",
            field_type="integer",
            required=True,
            label_en="Applicant Age (Years)",
            label_hi="आवेदक की आयु (वर्ष)",
            help_text_en="Age of the farmer at enrollment (must be between 18 and 40 years).",
            help_text_hi="नामांकन के समय किसान की आयु (18 से 40 वर्ष के बीच होनी चाहिए)।",
            validation_message_en="Applicant age must be between 18 and 40 years.",
            validation_message_hi="आवेदक की आयु 18 से 40 वर्ष के बीच होनी चाहिए।",
            section_key="applicant_demographics",
            display_order=1,
            min_value=18.0,
            max_value=40.0,
            associated_evidence_type="AADHAAR",
        ),
        FormFieldDefinition(
            field_key="applicant.has_other_pension_scheme",
            claim_type="applicant.has_other_pension_scheme",
            field_type="boolean",
            required=True,
            label_en="Covered under Other Social Security (NPS/ESIC/EPFO/PM-SYM)",
            label_hi="अन्य सामाजिक सुरक्षा (NPS/ESIC/EPFO/PM-SYM) में शामिल",
            help_text_en="Is the applicant covered under NPS, ESIC, EPFO, PM-SYM, or PM-LVM?",
            help_text_hi="क्या आवेदक NPS, ESIC, EPFO, PM-SYM, या PM-LVM के तहत कवर है?",
            validation_message_en="Applicant must not be covered under other statutory social security schemes.",
            validation_message_hi="आवेदक अन्य वैधानिक सामाजिक सुरक्षा योजनाओं के अंतर्गत शामिल नहीं होना चाहिए।",
            section_key="applicant_demographics",
            display_order=2,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.owns_cultivable_land",
            claim_type="family.owns_cultivable_land",
            field_type="boolean",
            required=True,
            label_en="Owns Cultivable Landholding",
            label_hi="कृषि योग्य भूमि का स्वामित्व",
            help_text_en="Does the farmer family own cultivable land as per revenue records?",
            help_text_hi="क्या राजस्व अभिलेखों के अनुसार किसान परिवार के पास कृषि योग्य भूमि का स्वामित्व है?",
            validation_message_en="Farmer must own cultivable landholding.",
            validation_message_hi="किसान के पास कृषि योग्य भूमि होना आवश्यक है।",
            section_key="land_details",
            display_order=1,
            default_value=True,
            associated_evidence_type="LAND_RECORD",
        ),
        FormFieldDefinition(
            field_key="land.total_land_area_hectares",
            claim_type="land.total_land_area_hectares",
            field_type="decimal",
            required=True,
            label_en="Total Cultivable Land Area (Hectares)",
            label_hi="कुल कृषि योग्य भूमि क्षेत्रफल (हेक्टेयर)",
            help_text_en="Total cultivable landholding in hectares (max 2.0 hectares for SMFs).",
            help_text_hi="हेक्टेयर में कुल कृषि योग्य भूमि (लघु एवं सीमांत किसानों के लिए अधिकतम 2.0 हेक्टेयर)।",
            validation_message_en="Land area must be greater than 0 and not exceed 2.0 hectares.",
            validation_message_hi="भूमि क्षेत्रफल शून्य से अधिक और 2.0 हेक्टेयर से अधिक नहीं होना चाहिए।",
            section_key="land_details",
            display_order=2,
            min_value=0.01,
            max_value=2.0,
            associated_evidence_type="LAND_RECORD",
        ),
        FormFieldDefinition(
            field_key="land.record_date_valid",
            claim_type="land.record_date_valid",
            field_type="boolean",
            required=True,
            label_en="Land Record Entry on or before 01.08.2019",
            label_hi="01.08.2019 को या उससे पूर्व भूमि रिकॉर्ड प्रविष्टि",
            help_text_en="Was the landholding recorded in state land records on or before 01.08.2019?",
            help_text_hi="क्या भूमि स्वामित्व 01.08.2019 को या उससे पहले राज्य के भूमि रिकॉर्ड में दर्ज था?",
            validation_message_en="Land must be recorded on or before 01.08.2019.",
            validation_message_hi="भूमि 01.08.2019 को या उससे पूर्व दर्ज होनी चाहिए।",
            section_key="land_details",
            display_order=3,
            default_value=True,
            associated_evidence_type="LAND_RECORD",
        ),
        FormFieldDefinition(
            field_key="family.is_institutional_landholder",
            claim_type="family.is_institutional_landholder",
            field_type="boolean",
            required=True,
            label_en="Institutional Landholder",
            label_hi="संस्थागत भूमिधारक",
            help_text_en="Is the applicant an institutional landholder?",
            help_text_hi="क्या आवेदक संस्थागत भूमिधारक है?",
            validation_message_en="Institutional landholders are excluded.",
            validation_message_hi="संस्थागत भूमिधारक योजना से बाहर हैं।",
            section_key="statutory_exclusions",
            display_order=1,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_constitutional_post_holder",
            claim_type="family.has_constitutional_post_holder",
            field_type="boolean",
            required=True,
            label_en="Constitutional Post Holder",
            label_hi="संवैधानिक पद धारक",
            help_text_en="Does any family member hold or held a constitutional post?",
            help_text_hi="क्या परिवार का कोई सदस्य संवैधानिक पद पर है या रहा है?",
            validation_message_en="Constitutional post holders are excluded.",
            validation_message_hi="संवैधानिक पद धारक बहिष्कृत हैं।",
            section_key="statutory_exclusions",
            display_order=2,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_disqualified_government_employee",
            claim_type="family.has_disqualified_government_employee",
            field_type="boolean",
            required=True,
            label_en="Regular Government/PSU Employee",
            label_hi="नियमित सरकारी/पीएसयू कर्मचारी",
            help_text_en="Is any family member a regular serving/retired government employee (excluding Group D)?",
            help_text_hi="क्या परिवार का कोई सदस्य नियमित सेवारत/सेवानिवृत्त सरकारी कर्मचारी है (ग्रुप डी को छोड़कर)?",
            validation_message_en="Government employees are excluded.",
            validation_message_hi="सरकारी कर्मचारी बहिष्कृत हैं।",
            section_key="statutory_exclusions",
            display_order=3,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_income_tax_payer",
            claim_type="family.has_income_tax_payer",
            field_type="boolean",
            required=True,
            label_en="Income Tax Payer in Last Assessment Year",
            label_hi="गत कर निर्धारण वर्ष में आयकर दाता",
            help_text_en="Did any family member pay income tax in the last assessment year?",
            help_text_hi="क्या परिवार के किसी सदस्य ने पिछले कर निर्धारण वर्ष में आयकर का भुगतान किया?",
            validation_message_en="Income tax payers are excluded.",
            validation_message_hi="आयकर दाता बहिष्कृत हैं।",
            section_key="statutory_exclusions",
            display_order=4,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_registered_practicing_professional",
            claim_type="family.has_registered_practicing_professional",
            field_type="boolean",
            required=True,
            label_en="Practicing Professional (Doctor/Engineer/Lawyer/CA/Architect)",
            label_hi="पंजीकृत पेशेवर (डॉक्टर/इंजीनियर/वकील/सीए/वास्तुकार)",
            help_text_en="Is any family member a registered practicing professional?",
            help_text_hi="क्या परिवार का कोई सदस्य पंजीकृत पेशेवर अभ्यासकर्ता है?",
            validation_message_en="Practicing professionals are excluded.",
            validation_message_hi="पंजीकृत पेशेवर बहिष्कृत हैं।",
            section_key="statutory_exclusions",
            display_order=5,
            default_value=False,
        ),
    ]

    evidence_types = [
        FormEvidenceDefinition(
            evidence_type="AADHAAR",
            label_en="Aadhaar Card of Farmer",
            label_hi="किसान का आधार कार्ड",
            description_en="Official Aadhaar card of the applicant farmer for identity and age verification.",
            description_hi="पहचान और आयु सत्यापन के लिए आवेदक किसान का आधिकारिक आधार कार्ड।",
            mandatory=True,
            associated_field_keys=["applicant.age"],
        ),
        FormEvidenceDefinition(
            evidence_type="LAND_RECORD",
            label_en="Land Revenue Record / Khasra-Khatauni",
            label_hi="भूमि राजस्व अभिलेख / खसरा-खतौनी",
            description_en="Certified land record verifying cultivable landholding of up to 2 hectares as on 01.08.2019.",
            description_hi="01.08.2019 को 2 हेक्टेयर तक कृषि योग्य भूमि स्वामित्व को सत्यापित करने वाला प्रमाणित भूमि रिकॉर्ड।",
            mandatory=True,
            associated_field_keys=["family.owns_cultivable_land", "land.total_land_area_hectares", "land.record_date_valid"],
        ),
        FormEvidenceDefinition(
            evidence_type="BANK_PASSBOOK",
            label_en="Savings Bank Passbook / Mandate",
            label_hi="बचत बैंक पासबुक / अधिदेश",
            description_en="Bank passbook with IFSC for auto-debit of pension contributions.",
            description_hi="पेंशन अंशदान के स्वतः कटौती के लिए आईएफएससी युक्त बैंक पासबुक।",
            mandatory=True,
        ),
    ]

    return PolicyFormMetadata(
        scheme_code="PM_KMY",
        policy_version_code="v1.0-2019",
        effective_from="2019-08-01",
        sections=sections,
        fields=fields,
        evidence_types=evidence_types,
    )


def _build_pmuy_v2_form() -> PolicyFormMetadata:
    """Build canonical form metadata for PMUY v2.0-2021 (Ujjwala 2.0)."""
    sections = [
        FormSectionDefinition(
            section_key="applicant_identity",
            title_en="Woman Applicant Identity",
            title_hi="महिला आवेदक की पहचान",
            description_en="Verification that the applicant is an adult woman aged 18 years or older.",
            description_hi="सत्यापन कि आवेदक 18 वर्ष या उससे अधिक आयु की वयस्क महिला है।",
            display_order=1,
        ),
        FormSectionDefinition(
            section_key="household_lpg",
            title_en="Household LPG Status & Deprivation Category",
            title_hi="पारिवारिक एलपीजी स्थिति एवं वंचन श्रेणी",
            description_en="Verification of no existing LPG connection in household and priority poverty category.",
            description_hi="परिवार में किसी पूर्व एलपीजी कनेक्शन न होने और प्राथमिकता निर्धनता श्रेणी का सत्यापन।",
            display_order=2,
        ),
        FormSectionDefinition(
            section_key="statutory_exclusions",
            title_en="Statutory Exclusions & Assets",
            title_hi="वैधानिक बहिष्करण एवं परिसंपत्ति",
            description_en="Declaration of government employment and four-wheeler vehicle exclusion.",
            description_hi="सरकारी रोजगार और चार पहिया वाहन बहिष्करण की घोषणा।",
            display_order=3,
        ),
    ]

    fields = [
        FormFieldDefinition(
            field_key="applicant.gender",
            claim_type="applicant.gender",
            field_type="select",
            required=True,
            label_en="Gender of Applicant",
            label_hi="आवेदक का लिंग",
            help_text_en="PMUY connections are issued strictly in the name of an adult woman.",
            help_text_hi="पीएमयूवाई कनेक्शन केवल वयस्क महिला के नाम पर जारी किए जाते हैं।",
            validation_message_en="Applicant must be female.",
            validation_message_hi="आवेदक महिला होनी चाहिए।",
            section_key="applicant_identity",
            display_order=1,
            options=[
                {"value": "FEMALE", "label_en": "Female", "label_hi": "महिला"},
                {"value": "MALE", "label_en": "Male", "label_hi": "पुरुष"},
                {"value": "OTHER", "label_en": "Other", "label_hi": "अन्य"},
            ],
            default_value="FEMALE",
            associated_evidence_type="AADHAAR",
        ),
        FormFieldDefinition(
            field_key="applicant.age",
            claim_type="applicant.age",
            field_type="integer",
            required=True,
            label_en="Applicant Age (Years)",
            label_hi="आवेदक की आयु (वर्ष)",
            help_text_en="Applicant must have attained at least 18 years of age.",
            help_text_hi="आवेदक की आयु कम से कम 18 वर्ष पूर्ण होनी चाहिए।",
            validation_message_en="Applicant must be at least 18 years of age.",
            validation_message_hi="आवेदक की आयु कम से कम 18 वर्ष होनी चाहिए।",
            section_key="applicant_identity",
            display_order=2,
            min_value=18.0,
            max_value=120.0,
            associated_evidence_type="AADHAAR",
        ),
        FormFieldDefinition(
            field_key="household.has_existing_lpg",
            claim_type="household.has_existing_lpg",
            field_type="boolean",
            required=True,
            label_en="Existing LPG Connection in Household",
            label_hi="परिवार में पूर्व से एलपीजी कनेक्शन",
            help_text_en="Does any member of the household have an active LPG connection from any OMC?",
            help_text_hi="क्या परिवार के किसी सदस्य के पास किसी भी तेल कंपनी से सक्रिय एलपीजी कनेक्शन है?",
            validation_message_en="Household must not possess an existing LPG connection.",
            validation_message_hi="परिवार के पास पूर्व से कोई एलपीजी कनेक्शन नहीं होना चाहिए।",
            section_key="household_lpg",
            display_order=1,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="household.is_deprived_or_qualifying_category",
            claim_type="household.is_deprived_or_qualifying_category",
            field_type="boolean",
            required=True,
            label_en="Belongs to Recognized Poor/Deprivation Category",
            label_hi="मान्यता प्राप्त निर्धन/वंचित श्रेणी से संबंधित",
            help_text_en="Does household belong to SC/ST, PMAY-G, AAY, MBC, Tea Tribe, Forest Dweller, or SECC Poor?",
            help_text_hi="क्या परिवार एससी/एसटी, पीएमएवाई-जी, एएवाई, एमबीसी, चाय जनजाति, वनवासी या एसईसीसी निर्धन श्रेणी में आता है?",
            validation_message_en="Household must belong to a qualifying poor category.",
            validation_message_hi="परिवार को पात्र निर्धन श्रेणी से संबंधित होना चाहिए।",
            section_key="household_lpg",
            display_order=2,
            default_value=True,
            associated_evidence_type="DEPRIVATION_CERTIFICATE",
        ),
        FormFieldDefinition(
            field_key="household.qualifying_category",
            claim_type="household.qualifying_category",
            field_type="select",
            required=True,
            label_en="Qualifying Category Code",
            label_hi="पात्र श्रेणी कोड",
            help_text_en="Select specific statutory category under Ujjwala 2.0.",
            help_text_hi="उज्ज्वला 2.0 के तहत विशिष्ट वैधानिक श्रेणी का चयन करें।",
            section_key="household_lpg",
            display_order=3,
            options=[
                {"value": "SC_ST", "label_en": "Scheduled Caste / Scheduled Tribe", "label_hi": "अनुसूचित जाति / अनुसूचित जनजाति"},
                {"value": "PMAY_G", "label_en": "PMAY (Gramin) Beneficiary", "label_hi": "पीएमएवाई (ग्रामीण) लाभार्थी"},
                {"value": "AAY", "label_en": "Antyodaya Anna Yojana (AAY)", "label_hi": "अंत्योदय अन्न योजना (एएवाई)"},
                {"value": "MOST_BACKWARD_CLASSES", "label_en": "Most Backward Classes (MBC)", "label_hi": "अति पिछड़ा वर्ग (एमबीसी)"},
                {"value": "TEA_GARDEN", "label_en": "Tea & Ex-Tea Garden Tribes", "label_hi": "चाय और पूर्व-चाय बागान जनजाति"},
                {"value": "FOREST_DWELLER", "label_en": "Forest Dwellers", "label_hi": "वनवासी"},
                {"value": "ISLAND", "label_en": "Residents of Islands / River Islands", "label_hi": "द्वीप / नदी द्वीप निवासी"},
                {"value": "SECC_POOR", "label_en": "SECC Poor / 14-Point Declaration", "label_hi": "एसईसीसी निर्धन / 14-सूत्रीय घोषणा"},
            ],
            default_value="SECC_POOR",
            associated_evidence_type="DEPRIVATION_CERTIFICATE",
            condition=FieldCondition(
                field_key="household.is_deprived_or_qualifying_category",
                operator=ConditionOperator.EQUALS,
                value=True,
            ),
        ),
        FormFieldDefinition(
            field_key="household.has_government_employee",
            claim_type="household.has_government_employee",
            field_type="boolean",
            required=True,
            label_en="Government Employee in Household",
            label_hi="परिवार में सरकारी कर्मचारी",
            help_text_en="Is any member of the household a regular employee of Central/State Government?",
            help_text_hi="क्या परिवार का कोई सदस्य केंद्र/राज्य सरकार का नियमित कर्मचारी है?",
            validation_message_en="Households with government employees are excluded.",
            validation_message_hi="सरकारी कर्मचारी वाले परिवार बहिष्कृत हैं।",
            section_key="statutory_exclusions",
            display_order=1,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="household.owns_motorized_four_wheeler",
            claim_type="household.owns_motorized_four_wheeler",
            field_type="boolean",
            required=True,
            label_en="Motorized Four-Wheeler Ownership",
            label_hi="चार पहिया मोटर वाहन का स्वामित्व",
            help_text_en="Does the household own a motorized four-wheeler vehicle?",
            help_text_hi="क्या परिवार के पास चार पहिया मोटर वाहन है?",
            validation_message_en="Households owning motorized four-wheelers are excluded.",
            validation_message_hi="चार पहिया वाहन वाले परिवार बहिष्कृत हैं।",
            section_key="statutory_exclusions",
            display_order=2,
            default_value=False,
        ),
    ]

    evidence_types = [
        FormEvidenceDefinition(
            evidence_type="AADHAAR",
            label_en="Aadhaar Card of Woman Beneficiary",
            label_hi="महिला लाभार्थी का आधार कार्ड",
            description_en="Aadhaar card of the adult woman applying for the connection.",
            description_hi="कनेक्शन के लिए आवेदन करने वाली वयस्क महिला का आधार कार्ड।",
            mandatory=True,
            associated_field_keys=["applicant.gender", "applicant.age"],
        ),
        FormEvidenceDefinition(
            evidence_type="RATION_CARD",
            label_en="Ration Card / Family Composition Document",
            label_hi="राशन कार्ड / परिवार संरचना दस्तावेज",
            description_en="Ration card issued by State/UT or family composition document (or Migrant Self-Declaration Annexure).",
            description_hi="राज्य द्वारा जारी राशन कार्ड या परिवार संरचना दस्तावेज (या प्रवासी स्व-घोषणा पत्र)।",
            mandatory=True,
        ),
        FormEvidenceDefinition(
            evidence_type="DEPRIVATION_CERTIFICATE",
            label_en="Supporting Deprivation / Category Proof",
            label_hi="सहायक वंचन / श्रेणी प्रमाण पत्र",
            description_en="Certificate of BPL, AAY, SC/ST, Forest Dweller, or 14-point deprivation declaration.",
            description_hi="बीपीएल, एएवाई, एससी/एसटी, वनवासी प्रमाण पत्र या 14-सूत्रीय वंचन घोषणा।",
            mandatory=True,
            associated_field_keys=["household.is_deprived_or_qualifying_category", "household.qualifying_category"],
        ),
        FormEvidenceDefinition(
            evidence_type="BANK_PASSBOOK",
            label_en="Bank Account Passbook / Statement",
            label_hi="बैंक खाता पासबुक / विवरण",
            description_en="Bank account details of the woman applicant for LPG subsidy credit.",
            description_hi="एलपीजी सब्सिडी अंतरण के लिए महिला आवेदक का बैंक खाता विवरण।",
            mandatory=True,
        ),
    ]

    return PolicyFormMetadata(
        scheme_code="PMUY",
        policy_version_code="v2.0-2021",
        effective_from="2021-08-10",
        sections=sections,
        fields=fields,
        evidence_types=evidence_types,
    )


def _build_pm_vishwakarma_v1_form() -> PolicyFormMetadata:
    """Build canonical form metadata for PM Vishwakarma v1.0-2023."""
    sections = [
        FormSectionDefinition(
            section_key="artisan_identity",
            title_en="Artisan Identity & Demographics",
            title_hi="कारीगर पहचान एवं जनसांख्यिकी",
            description_en="Verification of artisan identity and minimum age requirement.",
            description_hi="कारीगर की पहचान और न्यूनतम आयु आवश्यकता का सत्यापन।",
            display_order=1,
        ),
        FormSectionDefinition(
            section_key="traditional_trade",
            title_en="Traditional Trade & Livelihood",
            title_hi="पारंपरिक व्यवसाय एवं आजीविका",
            description_en="Registration in one of the 18 family-based traditional trades in the unorganized sector.",
            description_hi="असंगठित क्षेत्र में 18 परिवार-आधारित पारंपरिक व्यवसायों में से एक में पंजीकरण।",
            display_order=2,
        ),
        FormSectionDefinition(
            section_key="family_and_exclusions",
            title_en="Family Declarations & Exclusions",
            title_hi="पारिवारिक घोषणाएं एवं बहिष्करण",
            description_en="Verification of one member per family and government service exclusion.",
            description_hi="प्रति परिवार एक सदस्य और सरकारी सेवा बहिष्करण का सत्यापन।",
            display_order=3,
        ),
    ]

    fields = [
        FormFieldDefinition(
            field_key="applicant.age",
            claim_type="applicant.age",
            field_type="integer",
            required=True,
            label_en="Artisan Age (Years)",
            label_hi="कारीगर की आयु (वर्ष)",
            help_text_en="Artisan must have attained at least 18 years of age on registration date.",
            help_text_hi="पंजीकरण तिथि पर कारीगर की आयु कम से कम 18 वर्ष होनी चाहिए।",
            validation_message_en="Artisan must be at least 18 years old.",
            validation_message_hi="कारीगर की आयु कम से कम 18 वर्ष होनी चाहिए।",
            section_key="artisan_identity",
            display_order=1,
            min_value=18.0,
            max_value=120.0,
            associated_evidence_type="AADHAAR",
        ),
        FormFieldDefinition(
            field_key="trade.is_eligible_trade",
            claim_type="trade.is_eligible_trade",
            field_type="boolean",
            required=True,
            label_en="Practicing One of 18 Traditional Trades",
            label_hi="18 पारंपरिक व्यवसायों में से एक का अभ्यास",
            help_text_en="Is the artisan actively practicing one of the 18 designated family trades?",
            help_text_hi="क्या कारीगर सक्रिय रूप से 18 निर्दिष्ट पारंपरिक व्यवसायों में से एक का अभ्यास कर रहा है?",
            validation_message_en="Artisan must practice one of the 18 traditional trades.",
            validation_message_hi="कारीगर को 18 पारंपरिक व्यवसायों में से एक का अभ्यास करना चाहिए।",
            section_key="traditional_trade",
            display_order=1,
            default_value=True,
            associated_evidence_type="ARTISAN_ID_OR_DECLARATION",
        ),
        FormFieldDefinition(
            field_key="trade.trade_name",
            claim_type="trade.trade_name",
            field_type="select",
            required=True,
            label_en="Designated Trade Name",
            label_hi="निर्दिष्ट व्यवसाय का नाम",
            help_text_en="Select specific trade from the 18 statutory crafts.",
            help_text_hi="18 वैधानिक शिल्पों में से विशिष्ट व्यवसाय का चयन करें।",
            section_key="traditional_trade",
            display_order=2,
            options=[
                {"value": "CARPENTER", "label_en": "Carpenter (Suthar)", "label_hi": "बढ़ई (सुथार)"},
                {"value": "BOAT_MAKER", "label_en": "Boat Maker", "label_hi": "नाव निर्माता"},
                {"value": "ARMOURER", "label_en": "Armourer", "label_hi": "हथियार निर्माता"},
                {"value": "BLACKSMITH", "label_en": "Blacksmith (Lohar)", "label_hi": "लोहार"},
                {"value": "HAMMER_TOOLKIT_MAKER", "label_en": "Hammer and Tool Kit Maker", "label_hi": "हथौड़ा और टूलकिट निर्माता"},
                {"value": "LOCKSMITH", "label_en": "Locksmith", "label_hi": "ताला बनाने वाला"},
                {"value": "GOLDSMITH", "label_en": "Goldsmith (Sonar)", "label_hi": "सुनार"},
                {"value": "POTTER", "label_en": "Potter (Kumhaar)", "label_hi": "कुम्हार"},
                {"value": "SCULPTOR", "label_en": "Sculptor / Stone Carver", "label_hi": "मूर्तिकार / पत्थर तराशने वाला"},
                {"value": "COBBLER", "label_en": "Cobbler (Charmakar)", "label_hi": "मोची (चर्मकार)"},
                {"value": "MASON", "label_en": "Mason (Rajmistri)", "label_hi": "राजमिस्त्री"},
                {"value": "BASKET_MAT_BROOM_MAKER", "label_en": "Basket/Mat/Broom Maker/Coir Weaver", "label_hi": "टोकरी/चटाई/झाड़ू निर्माता"},
                {"value": "DOLL_TOY_MAKER", "label_en": "Doll & Toy Maker (Traditional)", "label_hi": "पारंपरिक गुड़िया और खिलौना निर्माता"},
                {"value": "BARBER", "label_en": "Barber (Naai)", "label_hi": "नाई"},
                {"value": "GARLAND_MAKER", "label_en": "Garland Maker (Malakaar)", "label_hi": "मालाकार"},
                {"value": "WASHERMAN", "label_en": "Washerman (Dhobi)", "label_hi": "धोबी"},
                {"value": "TAILOR", "label_en": "Tailor (Darzi)", "label_hi": "दर्जी"},
                {"value": "FISHING_NET_MAKER", "label_en": "Fishing Net Maker", "label_hi": "मछली का जाल निर्माता"},
            ],
            default_value="CARPENTER",
            associated_evidence_type="ARTISAN_ID_OR_DECLARATION",
            condition=FieldCondition(
                field_key="trade.is_eligible_trade",
                operator=ConditionOperator.EQUALS,
                value=True,
            ),
        ),
        FormFieldDefinition(
            field_key="trade.is_self_employed",
            claim_type="trade.is_self_employed",
            field_type="boolean",
            required=True,
            label_en="Self-Employed with Hands & Tools",
            label_hi="हाथों और औजारों से स्व-नियोजित",
            help_text_en="Does the artisan work with hands and tools in unorganized sector?",
            help_text_hi="क्या कारीगर असंगठित क्षेत्र में हाथों और औजारों से काम करता है?",
            validation_message_en="Artisan must be self-employed in unorganized sector.",
            validation_message_hi="कारीगर को असंगठित क्षेत्र में स्व-नियोजित होना चाहिए।",
            section_key="traditional_trade",
            display_order=3,
            default_value=True,
        ),
        FormFieldDefinition(
            field_key="trade.has_outstanding_similar_loan",
            claim_type="trade.has_outstanding_similar_loan",
            field_type="boolean",
            required=True,
            label_en="Outstanding Unpaid Similar Loan (PMEGP/MUDRA/SVANidhi)",
            label_hi="बकाया गैर-चुकाया समान ऋण (PMEGP/MUDRA/SVANidhi)",
            help_text_en="Does artisan have an outstanding unpaid credit loan under PMEGP, MUDRA, or PM SVANidhi?",
            help_text_hi="क्या कारीगर के पास पीएमईजीपी, मुद्रा या पीएम स्वनिधि के तहत कोई बकाया गैर-चुकाया ऋण है?",
            validation_message_en="Outstanding unpaid loans under similar schemes exclude the applicant.",
            validation_message_hi="समान योजनाओं के तहत बकाया ऋण होने पर आवेदक अपात्र है।",
            section_key="traditional_trade",
            display_order=4,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.other_member_enrolled",
            claim_type="family.other_member_enrolled",
            field_type="boolean",
            required=True,
            label_en="Other Family Member Already Enrolled",
            label_hi="परिवार का अन्य सदस्य पहले से नामांकित",
            help_text_en="Has any other member of the family unit (spouse, unmarried children) registered for PM Vishwakarma?",
            help_text_hi="क्या परिवार इकाई (पति, पत्नी, अविवाहित बच्चे) का कोई अन्य सदस्य पहले से नामांकित है?",
            validation_message_en="Only one member per family can be registered under PM Vishwakarma.",
            validation_message_hi="पीएम विश्वकर्मा के तहत प्रति परिवार केवल एक सदस्य नामांकित हो सकता है।",
            section_key="family_and_exclusions",
            display_order=1,
            default_value=False,
            associated_evidence_type="RATION_CARD",
        ),
        FormFieldDefinition(
            field_key="family.has_government_employee",
            claim_type="family.has_government_employee",
            field_type="boolean",
            required=True,
            label_en="Government Service in Family",
            label_hi="परिवार में सरकारी सेवा",
            help_text_en="Is the applicant or any family member employed in government service?",
            help_text_hi="क्या आवेदक या परिवार का कोई सदस्य सरकारी सेवा में कार्यरत है?",
            validation_message_en="Persons in government service and their family members are excluded.",
            validation_message_hi="सरकारी सेवा में कार्यरत व्यक्ति और उनके परिवार के सदस्य बहिष्कृत हैं।",
            section_key="family_and_exclusions",
            display_order=2,
            default_value=False,
        ),
    ]

    evidence_types = [
        FormEvidenceDefinition(
            evidence_type="AADHAAR",
            label_en="Aadhaar Card of Artisan",
            label_hi="कारीगर का आधार कार्ड",
            description_en="Official biometric Aadhaar card of the artisan verifying identity and age.",
            description_hi="पहचान और आयु सत्यापित करने वाला कारीगर का आधार कार्ड।",
            mandatory=True,
            associated_field_keys=["applicant.age"],
        ),
        FormEvidenceDefinition(
            evidence_type="ARTISAN_ID_OR_DECLARATION",
            label_en="Artisan Certificate / Trade Self-Declaration",
            label_hi="कारीगर प्रमाण पत्र / व्यवसाय स्व-घोषणा",
            description_en="Official Artisan ID Card, Shramik Card, or verified trade practice declaration.",
            description_hi="कारीगर पहचान पत्र, श्रमिक कार्ड, या सत्यापित व्यवसाय अभ्यास घोषणा।",
            mandatory=True,
            associated_field_keys=["trade.is_eligible_trade", "trade.trade_name"],
        ),
        FormEvidenceDefinition(
            evidence_type="RATION_CARD",
            label_en="Ration Card / Family Composition Document",
            label_hi="राशन कार्ड / परिवार संरचना दस्तावेज",
            description_en="Ration card proving family composition (husband, wife, unmarried children).",
            description_hi="परिवार संरचना (पति, पत्नी, अविवाहित बच्चे) को प्रमाणित करने वाला राशन कार्ड।",
            mandatory=True,
            associated_field_keys=["family.other_member_enrolled"],
        ),
        FormEvidenceDefinition(
            evidence_type="BANK_PASSBOOK",
            label_en="Aadhaar-Linked Bank Account Passbook",
            label_hi="आधार से जुड़ा बैंक खाता पासबुक",
            description_en="Bank passbook with IFSC for receiving toolkit incentive and loan credit.",
            description_hi="टूलकिट प्रोत्साहन और ऋण राशि प्राप्त करने के लिए बैंक पासबुक।",
            mandatory=True,
        ),
    ]

    return PolicyFormMetadata(
        scheme_code="PM_VISHWAKARMA",
        policy_version_code="v1.0-2023",
        effective_from="2023-09-17",
        sections=sections,
        fields=fields,
        evidence_types=evidence_types,
    )


def _build_pmay_g_v1_form() -> PolicyFormMetadata:
    """Build canonical form metadata for PMAY-G v1.0-2016."""
    sections = [
        FormSectionDefinition(
            section_key="rural_residence",
            title_en="Rural Jurisdiction & Habitation",
            title_hi="ग्रामीण अधिकार क्षेत्र एवं निवास",
            description_en="Verification of residence within rural Gram Panchayat area.",
            description_hi="ग्रामीण ग्राम पंचायत क्षेत्र में निवास का सत्यापन।",
            display_order=1,
        ),
        FormSectionDefinition(
            section_key="housing_condition",
            title_en="Current Housing & Deprivation Status",
            title_hi="वर्तमान आवास एवं वंचन स्थिति",
            description_en="Assessment of pucca house non-ownership and living in kutcha/dilapidated house.",
            description_hi="पक्के मकान के गैर-स्वामित्व और कच्चे/जीर्ण-शीर्ण मकान में रहने का मूल्यांकन।",
            display_order=2,
        ),
        FormSectionDefinition(
            section_key="automatic_exclusions",
            title_en="10-Point Automatic Exclusions",
            title_hi="10-बिंदु स्वतः बहिष्करण मानदंड",
            description_en="Statutory declarations verifying none of the 10 automatic exclusion parameters apply.",
            description_hi="वैधानिक घोषणाएं कि 10 स्वतः बहिष्करण मापदंडों में से कोई भी लागू नहीं होता है।",
            display_order=3,
        ),
    ]

    fields = [
        FormFieldDefinition(
            field_key="location.is_rural_area",
            claim_type="location.is_rural_area",
            field_type="boolean",
            required=True,
            label_en="Residence in Rural Gram Panchayat Area",
            label_hi="ग्रामीण ग्राम पंचायत क्षेत्र में निवास",
            help_text_en="Is the applicant household located within a recognized rural area?",
            help_text_hi="क्या आवेदक परिवार मान्यता प्राप्त ग्रामीण क्षेत्र में स्थित है?",
            validation_message_en="PMAY-G is applicable only to rural households.",
            validation_message_hi="पीएमएवाई-जी केवल ग्रामीण परिवारों पर लागू है।",
            section_key="rural_residence",
            display_order=1,
            default_value=True,
        ),
        FormFieldDefinition(
            field_key="housing.owns_pucca_house",
            claim_type="housing.owns_pucca_house",
            field_type="boolean",
            required=True,
            label_en="Owns Pucca House Anywhere in India",
            label_hi="भारत में कहीं भी पक्का मकान का स्वामित्व",
            help_text_en="Does the family own a permanent all-weather pucca house anywhere in India?",
            help_text_hi="क्या परिवार के पास भारत में कहीं भी स्थायी पक्का मकान है?",
            validation_message_en="Households owning a pucca house are ineligible.",
            validation_message_hi="पक्का मकान वाले परिवार अपात्र हैं।",
            section_key="housing_condition",
            display_order=1,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="housing.house_type",
            claim_type="housing.house_type",
            field_type="select",
            required=True,
            label_en="Current Dwelling Structure Type",
            label_hi="वर्तमान आवास संरचना प्रकार",
            help_text_en="Type of current living quarters (kutcha walls & roof, or houseless).",
            help_text_hi="वर्तमान आवास का प्रकार (कच्ची दीवारें और छत, या बेघर)।",
            section_key="housing_condition",
            display_order=2,
            options=[
                {"value": "KUTCHA", "label_en": "Kutcha (Thatched/Mud/Unbaked Brick)", "label_hi": "कच्चा (घास-फूस/मिट्टी/कच्ची ईंट)"},
                {"value": "PUCCA", "label_en": "Pucca (Concrete/Baked Brick)", "label_hi": "पक्का (कंक्रीट/पक्की ईंट)"},
                {"value": "SEMI_PUCCA", "label_en": "Semi-Pucca Structure", "label_hi": "अर्ध-पक्का ढांचा"},
                {"value": "HOUSELESS", "label_en": "Houseless / Without Shelter", "label_hi": "बेघर / बिना आश्रय"},
            ],
            default_value="KUTCHA",
            associated_evidence_type="HOUSING_VERIFICATION_CERTIFICATE",
        ),
        FormFieldDefinition(
            field_key="exclusions.owns_motorized_three_four_wheeler",
            claim_type="exclusions.owns_motorized_three_four_wheeler",
            field_type="boolean",
            required=True,
            label_en="Owns Motorised Three/Four Wheeler",
            label_hi="तिपहिया/चार पहिया मोटर वाहन का स्वामित्व",
            help_text_en="Does household own a motorized 3-wheeler or 4-wheeler vehicle?",
            help_text_hi="क्या परिवार के पास तिपहिया या चार पहिया मोटर वाहन है?",
            validation_message_en="Motorized 3/4-wheeler owners are excluded.",
            validation_message_hi="तिपहिया/चार पहिया वाहन मालिक बहिष्कृत हैं।",
            section_key="automatic_exclusions",
            display_order=1,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="exclusions.owns_mechanized_agri_equipment",
            claim_type="exclusions.owns_mechanized_agri_equipment",
            field_type="boolean",
            required=True,
            label_en="Owns Mechanised 3/4-Wheeler Agricultural Equipment",
            label_hi="यंत्रीकृत 3/4 पहिया कृषि उपकरण का स्वामित्व",
            help_text_en="Does household own tractors or heavy mechanized farm equipment?",
            help_text_hi="क्या परिवार के पास ट्रैक्टर या भारी यंत्रीकृत कृषि उपकरण हैं?",
            validation_message_en="Mechanized agri-equipment owners are excluded.",
            validation_message_hi="यंत्रीकृत कृषि उपकरण मालिक बहिष्कृत हैं।",
            section_key="automatic_exclusions",
            display_order=2,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="exclusions.kcc_limit_above_fifty_thousand",
            claim_type="exclusions.kcc_limit_above_fifty_thousand",
            field_type="boolean",
            required=True,
            label_en="Holds Kisan Credit Card with Limit >= Rs 50,000",
            label_hi="50,000 रुपये या अधिक सीमा वाला किसान क्रेडिट कार्ड",
            help_text_en="Does any family member hold a KCC with credit limit of Rs 50,000 or more?",
            help_text_hi="क्या परिवार के किसी सदस्य के पास 50,000 रुपये या उससे अधिक सीमा का केसीसी है?",
            validation_message_en="KCC limit >= 50,000 is an exclusion criterion.",
            validation_message_hi="50,000 या अधिक केसीसी सीमा बहिष्करण का मानदंड है।",
            section_key="automatic_exclusions",
            display_order=3,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_government_employee",
            claim_type="family.has_government_employee",
            field_type="boolean",
            required=True,
            label_en="Regular Government Employee in Household",
            label_hi="परिवार में नियमित सरकारी कर्मचारी",
            help_text_en="Is any member of the household a regular government employee?",
            help_text_hi="क्या परिवार का कोई सदस्य नियमित सरकारी कर्मचारी है?",
            validation_message_en="Government employee households are excluded.",
            validation_message_hi="सरकारी कर्मचारी वाले परिवार बहिष्कृत हैं।",
            section_key="automatic_exclusions",
            display_order=4,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_member_earning_above_fifteen_thousand",
            claim_type="family.has_member_earning_above_fifteen_thousand",
            field_type="boolean",
            required=True,
            label_en="Any Member Earning > Rs 15,000 per Month",
            label_hi="कोई सदस्य 15,000 रुपये प्रति माह से अधिक कमाता है",
            help_text_en="Does any household member earn more than Rs 15,000 per month?",
            help_text_hi="क्या परिवार का कोई सदस्य 15,000 रुपये प्रति माह से अधिक कमाता है?",
            validation_message_en="Monthly income > 15,000 is an exclusion criterion.",
            validation_message_hi="15,000 रुपये से अधिक मासिक आय बहिष्करण मानदंड है।",
            section_key="automatic_exclusions",
            display_order=5,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_income_tax_payer",
            claim_type="family.has_income_tax_payer",
            field_type="boolean",
            required=True,
            label_en="Income Tax Payer in Household",
            label_hi="परिवार में आयकर दाता",
            help_text_en="Does any member of the household pay income tax?",
            help_text_hi="क्या परिवार का कोई सदस्य आयकर देता है?",
            validation_message_en="Income tax payers are excluded.",
            validation_message_hi="आयकर दाता बहिष्कृत हैं।",
            section_key="automatic_exclusions",
            display_order=6,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_professional_tax_payer",
            claim_type="family.has_professional_tax_payer",
            field_type="boolean",
            required=True,
            label_en="Professional Tax Payer in Household",
            label_hi="परिवार में व्यवसाय कर (प्रोफेशनल टैक्स) दाता",
            help_text_en="Does any member of the household pay professional tax?",
            help_text_hi="क्या परिवार का कोई सदस्य व्यवसाय कर देता है?",
            validation_message_en="Professional tax payers are excluded.",
            validation_message_hi="व्यवसाय कर दाता बहिष्कृत हैं।",
            section_key="automatic_exclusions",
            display_order=7,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="land.irrigated_land_acres",
            claim_type="land.irrigated_land_acres",
            field_type="decimal",
            required=True,
            label_en="Total Irrigated Land Owned (Acres)",
            label_hi="स्वामित्व वाली कुल सिंचित भूमि (एकड़)",
            help_text_en="Total irrigated landholding (must be less than 2.5 acres for eligibility).",
            help_text_hi="कुल सिंचित भूमि स्वामित्व (पात्रता के लिए 2.5 एकड़ से कम होना चाहिए)।",
            validation_message_en="Irrigated land must be less than 2.5 acres.",
            validation_message_hi="सिंचित भूमि 2.5 एकड़ से कम होनी चाहिए।",
            section_key="automatic_exclusions",
            display_order=8,
            min_value=0.0,
            max_value=100.0,
            default_value=0.0,
        ),
    ]

    evidence_types = [
        FormEvidenceDefinition(
            evidence_type="AADHAAR",
            label_en="Aadhaar Card of Head of Household",
            label_hi="परिवार के मुखिया का आधार कार्ड",
            description_en="Aadhaar card of the primary applicant / head of the rural household.",
            description_hi="ग्रामीण परिवार के प्राथमिक आवेदक / मुखिया का आधार कार्ड।",
            mandatory=True,
        ),
        FormEvidenceDefinition(
            evidence_type="HOUSING_VERIFICATION_CERTIFICATE",
            label_en="Kutcha House Certificate / Gram Panchayat Inspection",
            label_hi="कच्चा मकान प्रमाण पत्र / ग्राम पंचायत निरीक्षण",
            description_en="Official verification certificate from Gram Panchayat verifying kutcha dwelling.",
            description_hi="कच्चे मकान के सत्यापन हेतु ग्राम पंचायत द्वारा जारी आधिकारिक निरीक्षण प्रमाण पत्र।",
            mandatory=True,
            associated_field_keys=["housing.house_type"],
        ),
        FormEvidenceDefinition(
            evidence_type="JOB_CARD",
            label_en="MGNREGA Job Card",
            label_hi="मनरेगा जॉब कार्ड",
            description_en="Active MGNREGA Job Card of the beneficiary household.",
            description_hi="लाभार्थी परिवार का सक्रिय मनरेगा जॉब कार्ड।",
            mandatory=True,
        ),
        FormEvidenceDefinition(
            evidence_type="BANK_PASSBOOK",
            label_en="Aadhaar-Seeded Bank Passbook",
            label_hi="आधार से जुड़ी बैंक पासबुक",
            description_en="Bank passbook with Aadhaar linkage for DBT housing installment transfers.",
            description_hi="आवास निर्माण किश्तों के डीबीटी अंतरण के लिए आधार से जुड़ी बैंक पासबुक।",
            mandatory=True,
        ),
    ]

    return PolicyFormMetadata(
        scheme_code="PMAY_G",
        policy_version_code="v1.0-2016",
        effective_from="2016-04-01",
        sections=sections,
        fields=fields,
        evidence_types=evidence_types,
    )


def _build_pmay_u_2_0_v1_form() -> PolicyFormMetadata:
    """Build canonical form metadata for PMAY-U 2.0 v1.0-2024."""
    sections = [
        FormSectionDefinition(
            section_key="urban_jurisdiction",
            title_en="Urban Local Body Jurisdiction",
            title_hi="शहरी स्थानीय निकाय अधिकार क्षेत्र",
            description_en="Location within statutory town or notified urban municipal area.",
            description_hi="वैधानिक शहर या अधिसूचित शहरी नगरपालिका क्षेत्र में अवस्थिति।",
            display_order=1,
        ),
        FormSectionDefinition(
            section_key="income_and_vertical",
            title_en="Household Income Category & Vertical",
            title_hi="पारिवारिक आय श्रेणी एवं वर्टिकल",
            description_en="Annual household income bracket (EWS up to 3L, LIG up to 6L, MIG up to 9L).",
            description_hi="वार्षिक पारिवारिक आय सीमा (ईडब्ल्यूएस 3 लाख तक, एलआईजी 6 लाख तक, एमआईजी 9 लाख तक)।",
            display_order=2,
        ),
        FormSectionDefinition(
            section_key="housing_ownership",
            title_en="Housing Ownership & Prior Benefits",
            title_hi="आवास स्वामित्व एवं पूर्व लाभ",
            description_en="Verification of no pucca house ownership and no prior government housing benefits.",
            description_hi="पक्के मकान का स्वामित्व न होने और पूर्व सरकारी आवास लाभ न मिलने का सत्यापन।",
            display_order=3,
        ),
    ]

    fields = [
        FormFieldDefinition(
            field_key="location.is_urban_area",
            claim_type="location.is_urban_area",
            field_type="boolean",
            required=True,
            label_en="Residence in Notified Urban / Municipal Area",
            label_hi="अधिसूचित शहरी / नगरपालिका क्षेत्र में निवास",
            help_text_en="Is the applicant residing in a statutory town or notified ULB?",
            help_text_hi="क्या आवेदक वैधानिक शहर या अधिसूचित यूएलबी में निवास करता है?",
            validation_message_en="PMAY-U 2.0 is applicable only to urban areas.",
            validation_message_hi="पीएमएवाई-यू 2.0 केवल शहरी क्षेत्रों पर लागू है।",
            section_key="urban_jurisdiction",
            display_order=1,
            default_value=True,
        ),
        FormFieldDefinition(
            field_key="family.annual_income",
            claim_type="family.annual_income",
            field_type="decimal",
            required=True,
            label_en="Total Annual Household Income (INR)",
            label_hi="कुल वार्षिक पारिवारिक आय (रुपये)",
            help_text_en="Annual family income (max Rs 9,00,000 for MIG eligibility).",
            help_text_hi="वार्षिक पारिवारिक आय (एमआईजी पात्रता हेतु अधिकतम 9,00,000 रुपये)।",
            validation_message_en="Income must not exceed Rs 9,00,000 per annum.",
            validation_message_hi="आय 9,00,000 रुपये प्रति वर्ष से अधिक नहीं होनी चाहिए।",
            section_key="income_and_vertical",
            display_order=1,
            min_value=0.0,
            max_value=2000000.0,
            associated_evidence_type="INCOME_CERTIFICATE",
        ),
        FormFieldDefinition(
            field_key="family.income_category",
            claim_type="family.income_category",
            field_type="select",
            required=True,
            label_en="Household Income Category",
            label_hi="पारिवारिक आय श्रेणी",
            help_text_en="EWS (<= 3 Lakh), LIG (> 3L to 6 Lakh), or MIG (> 6L to 9 Lakh).",
            help_text_hi="ईडब्ल्यूएस (<= 3 लाख), एलआईजी (> 3 से 6 लाख), या एमआईजी (> 6 से 9 लाख)।",
            section_key="income_and_vertical",
            display_order=2,
            options=[
                {"value": "EWS", "label_en": "Economically Weaker Section (EWS) — Up to Rs 3 Lakh", "label_hi": "आर्थिक रूप से कमजोर वर्ग (ईडब्ल्यूएस) — 3 लाख तक"},
                {"value": "LIG", "label_en": "Low Income Group (LIG) — Rs 3L to Rs 6 Lakh", "label_hi": "निम्न आय वर्ग (एलआईजी) — 3 से 6 लाख"},
                {"value": "MIG", "label_en": "Middle Income Group (MIG) — Rs 6L to Rs 9 Lakh", "label_hi": "मध्यम आय वर्ग (एमआईजी) — 6 से 9 लाख"},
            ],
            default_value="EWS",
            associated_evidence_type="INCOME_CERTIFICATE",
        ),
        FormFieldDefinition(
            field_key="housing.owns_pucca_house",
            claim_type="housing.owns_pucca_house",
            field_type="boolean",
            required=True,
            label_en="Family Owns Pucca House Anywhere in India",
            label_hi="परिवार के पास भारत में कहीं भी पक्का मकान है",
            help_text_en="Does any family member own an all-weather permanent house?",
            help_text_hi="क्या परिवार के किसी सदस्य के पास स्थायी पक्का मकान है?",
            validation_message_en="Households owning a pucca house are ineligible.",
            validation_message_hi="पक्का मकान वाले परिवार अपात्र हैं।",
            section_key="housing_ownership",
            display_order=1,
            default_value=False,
            associated_evidence_type="PROPERTY_DOCUMENT_OR_AFFIDAVIT",
        ),
        FormFieldDefinition(
            field_key="family.has_prior_housing_benefit",
            claim_type="family.has_prior_housing_benefit",
            field_type="boolean",
            required=True,
            label_en="Availed Housing Benefit under Central/State Scheme in Last 20 Years",
            label_hi="पिछले 20 वर्षों में केंद्र/राज्य योजना के तहत आवास लाभ प्राप्त किया",
            help_text_en="Has the family availed of financial assistance under any housing scheme in past 20 years?",
            help_text_hi="क्या परिवार ने पिछले 20 वर्षों में किसी आवास योजना के तहत सहायता प्राप्त की है?",
            validation_message_en="Prior housing scheme beneficiaries are ineligible.",
            validation_message_hi="पूर्व आवास योजना लाभार्थी अपात्र हैं।",
            section_key="housing_ownership",
            display_order=2,
            default_value=False,
        ),
    ]

    evidence_types = [
        FormEvidenceDefinition(
            evidence_type="AADHAAR",
            label_en="Aadhaar Card of Head of Family",
            label_hi="परिवार के मुखिया का आधार कार्ड",
            description_en="Aadhaar identification of primary applicant and adult family members.",
            description_hi="प्राथमिक आवेदक और वयस्क परिवार के सदस्यों की आधार पहचान।",
            mandatory=True,
        ),
        FormEvidenceDefinition(
            evidence_type="INCOME_CERTIFICATE",
            label_en="Income Certificate / Salary Slip",
            label_hi="आय प्रमाण पत्र / वेतन पर्ची",
            description_en="Official income certificate from Tahsildar / competent authority or Form 16.",
            description_hi="तहसीलदार / सक्षम प्राधिकारी द्वारा जारी आय प्रमाण पत्र या फॉर्म 16।",
            mandatory=True,
            associated_field_keys=["family.annual_income", "family.income_category"],
        ),
        FormEvidenceDefinition(
            evidence_type="PROPERTY_DOCUMENT_OR_AFFIDAVIT",
            label_en="Affidavit of Pucca-House Non-Ownership",
            label_hi="पक्के मकान के गैर-स्वामित्व का शपथ पत्र",
            description_en="Notarized affidavit certifying non-ownership of pucca house anywhere in India.",
            description_hi="भारत में कहीं भी पक्का मकान न होने का नोटरीकृत शपथ पत्र।",
            mandatory=True,
            associated_field_keys=["housing.owns_pucca_house"],
        ),
        FormEvidenceDefinition(
            evidence_type="BANK_PASSBOOK",
            label_en="Bank Account Passbook / Statement",
            label_hi="बैंक खाता पासबुक / विवरण",
            description_en="Bank passbook with Aadhaar linkage for DBT subsidy credit.",
            description_hi="डीबीटी सब्सिडी क्रेडिट के लिए आधार से जुड़ी बैंक पासबुक।",
            mandatory=True,
        ),
    ]

    return PolicyFormMetadata(
        scheme_code="PMAY_U_2_0",
        policy_version_code="v1.0-2024",
        effective_from="2024-09-01",
        sections=sections,
        fields=fields,
        evidence_types=evidence_types,
    )


def _build_pm_svanidhi_v1_form() -> PolicyFormMetadata:
    """Build canonical form metadata for PM SVANidhi v1.0-2020."""
    sections = [
        FormSectionDefinition(
            section_key="vendor_identity",
            title_en="Street Vendor Identity & Age",
            title_hi="रेहड़ी-पटरी विक्रेता पहचान एवं आयु",
            description_en="Verification of street vendor age and urban vending engagement.",
            description_hi="रेहड़ी-पटरी विक्रेता की आयु और शहरी वेंडिंग गतिविधि का सत्यापन।",
            display_order=1,
        ),
        FormSectionDefinition(
            section_key="vending_activity",
            title_en="Vending Jurisdiction & Credentials",
            title_hi="वेंडिंग अधिकार क्षेत्र एवं प्रमाण पत्र",
            description_en="Certificate of Vending, ULB Survey identification, or Town Vending Committee LoR.",
            description_hi="वेंडिंग प्रमाण पत्र, यूएलबी सर्वेक्षण पहचान, या टाउन वेंडिंग कमेटी अनुशंसा पत्र।",
            display_order=2,
        ),
        FormSectionDefinition(
            section_key="banking_dbt",
            title_en="DBT Bank Account Verification",
            title_hi="डीबीटी बैंक खाता सत्यापन",
            description_en="Bank account verification for working capital loan disbursement.",
            description_hi="कार्यशील पूंजी ऋण संवितरण के लिए बैंक खाता सत्यापन।",
            display_order=3,
        ),
    ]

    fields = [
        FormFieldDefinition(
            field_key="vendor.is_urban_street_vendor",
            claim_type="vendor.is_urban_street_vendor",
            field_type="boolean",
            required=True,
            label_en="Engaged in Urban Street Vending",
            label_hi="शहरी रेहड़ी-पटरी व्यवसाय में संलग्न",
            help_text_en="Is the applicant actively engaged in street vending in an urban or surrounding area?",
            help_text_hi="क्या आवेदक शहरी या आसपास के क्षेत्र में रेहड़ी-पटरी व्यवसाय में सक्रिय रूप से संलग्न है?",
            validation_message_en="Applicant must be an urban street vendor.",
            validation_message_hi="आवेदक को एक शहरी रेहड़ी-पटरी विक्रेता होना चाहिए।",
            section_key="vendor_identity",
            display_order=1,
            default_value=True,
        ),
        FormFieldDefinition(
            field_key="applicant.age",
            claim_type="applicant.age",
            field_type="integer",
            required=True,
            label_en="Vendor Age (Years)",
            label_hi="विक्रेता की आयु (वर्ष)",
            help_text_en="Vendor must be at least 18 years of age.",
            help_text_hi="विक्रेता की आयु कम से कम 18 वर्ष होनी चाहिए।",
            validation_message_en="Vendor must be at least 18 years old.",
            validation_message_hi="विक्रेता की आयु कम से कम 18 वर्ष होनी चाहिए।",
            section_key="vendor_identity",
            display_order=2,
            min_value=18.0,
            max_value=120.0,
            associated_evidence_type="AADHAAR",
        ),
        FormFieldDefinition(
            field_key="vendor.has_vending_certificate",
            claim_type="vendor.has_vending_certificate",
            field_type="boolean",
            required=True,
            label_en="Possesses Certificate of Vending (CoV) / Vendor ID Card",
            label_hi="वेंडिंग प्रमाणपत्र (CoV) / विक्रेता पहचान पत्र धारक",
            help_text_en="Does vendor have a Certificate of Vending or ID Card issued by the ULB?",
            help_text_hi="क्या विक्रेता के पास यूएलबी द्वारा जारी वेंडिंग प्रमाणपत्र या पहचान पत्र है?",
            section_key="vending_activity",
            display_order=1,
            default_value=True,
            associated_evidence_type="VENDING_PROOF_OR_LOR",
        ),
        FormFieldDefinition(
            field_key="vendor.identified_in_ulb_survey",
            claim_type="vendor.identified_in_ulb_survey",
            field_type="boolean",
            required=True,
            label_en="Identified in ULB Vendor Survey",
            label_hi="यूएलबी विक्रेता सर्वेक्षण में चिन्हित",
            help_text_en="Was vendor identified in the Street Vendor survey conducted by the ULB?",
            help_text_hi="क्या विक्रेता को यूएलबी द्वारा आयोजित स्ट्रीट वेंडर सर्वेक्षण में चिन्हित किया गया था?",
            section_key="vending_activity",
            display_order=2,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="vendor.has_letter_of_recommendation",
            claim_type="vendor.has_letter_of_recommendation",
            field_type="boolean",
            required=True,
            label_en="Possesses Letter of Recommendation (LoR)",
            label_hi="अनुशंसा पत्र (LoR) धारक",
            help_text_en="Does vendor have an LoR from the Urban Local Body or Town Vending Committee?",
            help_text_hi="क्या विक्रेता के पास यूएलबी या टाउन वेंडिंग कमेटी से अनुशंसा पत्र है?",
            section_key="vending_activity",
            display_order=3,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="account.has_active_bank_account",
            claim_type="account.has_active_bank_account",
            field_type="boolean",
            required=True,
            label_en="Has Active Bank Account for Loan Disbursement",
            label_hi="ऋण संवितरण के लिए सक्रिय बैंक खाता धारक",
            help_text_en="Active bank account in vendor's name for direct digital credit of loan proceeds.",
            help_text_hi="ऋण राशि के प्रत्यक्ष डिजिटल अंतरण के लिए विक्रेता के नाम पर सक्रिय बैंक खाता।",
            validation_message_en="An active bank account is required for disbursement.",
            validation_message_hi="संवितरण के लिए एक सक्रिय बैंक खाता आवश्यक है।",
            section_key="banking_dbt",
            display_order=1,
            default_value=True,
            associated_evidence_type="BANK_PASSBOOK",
        ),
    ]

    evidence_types = [
        FormEvidenceDefinition(
            evidence_type="AADHAAR",
            label_en="Aadhaar Card of Street Vendor",
            label_hi="रेहड़ी-पटरी विक्रेता का आधार कार्ड",
            description_en="Aadhaar identification card of the street vendor.",
            description_hi="रेहड़ी-पटरी विक्रेता का आधार पहचान पत्र।",
            mandatory=True,
            associated_field_keys=["applicant.age"],
        ),
        FormEvidenceDefinition(
            evidence_type="VENDING_PROOF_OR_LOR",
            label_en="Certificate of Vending / ID Card / LoR",
            label_hi="वेंडिंग प्रमाण पत्र / पहचान पत्र / अनुशंसा पत्र",
            description_en="Official Certificate of Vending, ULB Vendor ID, or Letter of Recommendation from TVC.",
            description_hi="आधिकारिक वेंडिंग प्रमाण पत्र, यूएलबी वेंडर आईडी, या टीवीसी से अनुशंसा पत्र।",
            mandatory=True,
            associated_field_keys=["vendor.has_vending_certificate"],
        ),
        FormEvidenceDefinition(
            evidence_type="BANK_PASSBOOK",
            label_en="Bank Account Passbook / Statement",
            label_hi="बैंक खाता पासबुक / विवरण",
            description_en="Passbook of operational bank account for loan credit and digital cashback.",
            description_hi="ऋण राशि और डिजिटल कैशबैक के लिए सक्रिय बैंक खाते की पासबुक।",
            mandatory=True,
            associated_field_keys=["account.has_active_bank_account"],
        ),
    ]

    return PolicyFormMetadata(
        scheme_code="PM_SVANIDHI",
        policy_version_code="v1.0-2020",
        effective_from="2020-06-01",
        sections=sections,
        fields=fields,
        evidence_types=evidence_types,
    )


def _build_pmmvy_v2_form() -> PolicyFormMetadata:
    """Build canonical form metadata for PMMVY v2.0-2022 (Mission Shakti)."""
    sections = [
        FormSectionDefinition(
            section_key="maternal_profile",
            title_en="Maternal Demographics & Parity",
            title_hi="मातृत्व जनसांख्यिकी एवं प्रसव क्रम",
            description_en="Mother's age, pregnancy status, and living child birth order.",
            description_hi="माता की आयु, गर्भावस्था की स्थिति, और जीवित बच्चे का जन्म क्रम।",
            display_order=1,
        ),
        FormSectionDefinition(
            section_key="employment_exclusion",
            title_en="Employment & Maternity Benefit Disclosures",
            title_hi="रोजगार एवं मातृत्व लाभ प्रकटीकरण",
            description_en="Declaration verifying applicant is not a regular government/PSU employee.",
            description_hi="घोषणा कि आवेदक नियमित सरकारी/पीएसयू कर्मचारी नहीं है।",
            display_order=2,
        ),
        FormSectionDefinition(
            section_key="socio_economic_entitlement",
            title_en="Socio-Economic Priority Category",
            title_hi="सामाजिक-आर्थिक प्राथमिकता श्रेणी",
            description_en="Verification of belonging to qualifying social or economically disadvantaged section.",
            description_hi="पात्र सामाजिक या आर्थिक रूप से वंचित वर्ग से संबंधित होने का सत्यापन।",
            display_order=3,
        ),
    ]

    fields = [
        FormFieldDefinition(
            field_key="applicant.is_pregnant_or_lactating",
            claim_type="applicant.is_pregnant_or_lactating",
            field_type="boolean",
            required=True,
            label_en="Pregnant Woman / Lactating Mother Status",
            label_hi="गर्भवती महिला / स्तनपान कराने वाली माता की स्थिति",
            help_text_en="Is the applicant a registered pregnant woman or lactating mother?",
            help_text_hi="क्या आवेदक एक पंजीकृत गर्भवती महिला या स्तनपान कराने वाली माता है?",
            validation_message_en="Applicant must be a pregnant woman or lactating mother.",
            validation_message_hi="आवेदक को गर्भवती महिला या स्तनपान कराने वाली माता होना चाहिए।",
            section_key="maternal_profile",
            display_order=1,
            default_value=True,
            associated_evidence_type="MCP_CARD",
        ),
        FormFieldDefinition(
            field_key="applicant.age",
            claim_type="applicant.age",
            field_type="integer",
            required=True,
            label_en="Mother's Age at Childbirth (Years)",
            label_hi="प्रसव के समय माता की आयु (वर्ष)",
            help_text_en="Mother must have attained at least 19 years of age at pregnancy/childbirth.",
            help_text_hi="गर्भावस्था/प्रसव के समय माता की आयु कम से कम 19 वर्ष पूर्ण होनी चाहिए।",
            validation_message_en="Mother must be at least 19 years of age.",
            validation_message_hi="माता की आयु कम से कम 19 वर्ष होनी चाहिए।",
            section_key="maternal_profile",
            display_order=2,
            min_value=19.0,
            max_value=65.0,
            associated_evidence_type="AADHAAR",
        ),
        FormFieldDefinition(
            field_key="maternity.child_order",
            claim_type="maternity.child_order",
            field_type="integer",
            required=True,
            label_en="Birth Order of Living Child",
            label_hi="जीवित बच्चे का जन्म क्रम",
            help_text_en="Enter 1 for first living child, 2 for second living child.",
            help_text_hi="पहले जीवित बच्चे के लिए 1, दूसरे जीवित बच्चे के लिए 2 दर्ज करें।",
            validation_message_en="PMMVY benefits are limited to first and second child.",
            validation_message_hi="पीएमएमवीवाई लाभ प्रथम और द्वितीय बच्चे तक सीमित हैं।",
            section_key="maternal_profile",
            display_order=3,
            min_value=1.0,
            max_value=10.0,
            default_value=1,
        ),
        FormFieldDefinition(
            field_key="maternity.is_girl_child",
            claim_type="maternity.is_girl_child",
            field_type="boolean",
            required=True,
            label_en="Second Child is Female (Girl Child)",
            label_hi="दूसरा बच्चा बालिका (कन्या) है",
            help_text_en="For the second child, benefit is admissible strictly if the newborn is a girl.",
            help_text_hi="दूसरे बच्चे के लिए, लाभ केवल तभी स्वीकार्य है जब नवजात शिशु एक बालिका हो।",
            section_key="maternal_profile",
            display_order=4,
            default_value=True,
            condition=FieldCondition(
                field_key="maternity.child_order",
                operator=ConditionOperator.EQUALS,
                value=2,
            ),
        ),
        FormFieldDefinition(
            field_key="applicant.is_government_or_psu_employee",
            claim_type="applicant.is_government_or_psu_employee",
            field_type="boolean",
            required=True,
            label_en="Regular Employee of Central/State Govt or PSU",
            label_hi="केंद्र/राज्य सरकार या पीएसयू की नियमित कर्मचारी",
            help_text_en="Is the applicant in regular employment with Central/State Govt or PSUs with paid maternity leave?",
            help_text_hi="क्या आवेदक केंद्र/राज्य सरकार या पीएसयू में सवेतन मातृत्व अवकाश वाली नियमित कर्मचारी है?",
            validation_message_en="Regular government and PSU employees are excluded.",
            validation_message_hi="नियमित सरकारी और पीएसयू कर्मचारी बहिष्कृत हैं।",
            section_key="employment_exclusion",
            display_order=1,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="applicant.is_sc_st",
            claim_type="applicant.is_sc_st",
            field_type="boolean",
            required=True,
            label_en="Belongs to Scheduled Caste / Scheduled Tribe",
            label_hi="अनुसूचित जाति / अनुसूचित जनजाति से संबंधित",
            help_text_en="Does the mother belong to an SC or ST community?",
            help_text_hi="क्या माता एससी या एसटी समुदाय से संबंधित है?",
            section_key="socio_economic_entitlement",
            display_order=1,
            default_value=False,
            associated_evidence_type="ELIGIBILITY_PROOF_DOCUMENT",
        ),
        FormFieldDefinition(
            field_key="family.has_bpl_or_nfsa_ration_card",
            claim_type="family.has_bpl_or_nfsa_ration_card",
            field_type="boolean",
            required=True,
            label_en="Family Holds BPL or NFSA Ration Card",
            label_hi="परिवार के पास बीपीएल या एनएफएसए राशन कार्ड है",
            help_text_en="Does the family possess a Below Poverty Line (BPL) or NFSA priority ration card?",
            help_text_hi="क्या परिवार के पास गरीबी रेखा से नीचे (बीपीएल) या एनएफएसए राशन कार्ड है?",
            section_key="socio_economic_entitlement",
            display_order=2,
            default_value=True,
        ),
        FormFieldDefinition(
            field_key="applicant.has_eshram_card",
            claim_type="applicant.has_eshram_card",
            field_type="boolean",
            required=True,
            label_en="Holds Active e-Shram Registration Card",
            label_hi="सक्रिय ई-श्रम पंजीकरण कार्ड धारक",
            help_text_en="Is the applicant registered on the national e-Shram unorganized worker portal?",
            help_text_hi="क्या आवेदक राष्ट्रीय ई-श्रम असंगठित कामगार पोर्टल पर पंजीकृत है?",
            section_key="socio_economic_entitlement",
            display_order=3,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.is_pmjay_beneficiary",
            claim_type="family.is_pmjay_beneficiary",
            field_type="boolean",
            required=True,
            label_en="Beneficiary under PM-JAY (Ayushman Bharat)",
            label_hi="पीएम-जेएवाई (आयुष्मान भारत) के तहत लाभार्थी",
            help_text_en="Is the family enrolled under Pradhan Mantri Jan Aarogya Yojana?",
            help_text_hi="क्या परिवार प्रधानमंत्री जन आरोग्य योजना के तहत नामांकित है?",
            section_key="socio_economic_entitlement",
            display_order=4,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.has_mgnrega_card",
            claim_type="family.has_mgnrega_card",
            field_type="boolean",
            required=True,
            label_en="Family Holds MGNREGA Job Card",
            label_hi="परिवार के पास मनरेगा जॉब कार्ड है",
            help_text_en="Does the family possess an active MGNREGA Job Card?",
            help_text_hi="क्या परिवार के पास सक्रिय मनरेगा जॉब कार्ड है?",
            section_key="socio_economic_entitlement",
            display_order=5,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.is_pmkisan_beneficiary",
            claim_type="family.is_pmkisan_beneficiary",
            field_type="boolean",
            required=True,
            label_en="Farmer Beneficiary under PM-KISAN",
            label_hi="पीएम-किसान के तहत किसान लाभार्थी",
            help_text_en="Is the family a registered beneficiary of PM-KISAN?",
            help_text_hi="क्या परिवार पीएम-किसान का पंजीकृत लाभार्थी है?",
            section_key="socio_economic_entitlement",
            display_order=6,
            default_value=False,
        ),
        FormFieldDefinition(
            field_key="family.annual_income",
            claim_type="family.annual_income",
            field_type="decimal",
            required=True,
            label_en="Total Annual Household Income (INR)",
            label_hi="कुल वार्षिक पारिवारिक आय (रुपये)",
            help_text_en="Annual household income (must be less than Rs 8,00,000 for eligibility).",
            help_text_hi="वार्षिक पारिवारिक आय (पात्रता हेतु 8,00,000 रुपये से कम होनी चाहिए)।",
            section_key="socio_economic_entitlement",
            display_order=7,
            min_value=0.0,
            max_value=5000000.0,
            default_value=120000.0,
        ),
    ]

    evidence_types = [
        FormEvidenceDefinition(
            evidence_type="AADHAAR",
            label_en="Aadhaar Card of Mother",
            label_hi="माता का आधार कार्ड",
            description_en="Official Aadhaar card of the pregnant woman/mother.",
            description_hi="गर्भवती महिला/माता का आधिकारिक आधार कार्ड।",
            mandatory=True,
            associated_field_keys=["applicant.age"],
        ),
        FormEvidenceDefinition(
            evidence_type="MCP_CARD",
            label_en="Mother and Child Protection (MCP) Card",
            label_hi="मातृ एवं बाल सुरक्षा (एमसीपी) कार्ड",
            description_en="Registered MCP Card issued by Anganwadi / Health Center with LMP date.",
            description_hi="एलएमपी तिथि के साथ आंगनवाड़ी / स्वास्थ्य केंद्र द्वारा जारी पंजीकृत एमसीपी कार्ड।",
            mandatory=True,
            associated_field_keys=["applicant.is_pregnant_or_lactating"],
        ),
        FormEvidenceDefinition(
            evidence_type="BANK_PASSBOOK",
            label_en="Aadhaar-Linked Bank Account Passbook",
            label_hi="आधार से जुड़ा बैंक खाता पासबुक",
            description_en="Bank passbook of the mother with active Aadhaar seeding for DBT cash transfer.",
            description_hi="डीबीटी नकद अंतरण के लिए सक्रिय आधार सीडिंग वाली माता की बैंक पासबुक।",
            mandatory=True,
        ),
        FormEvidenceDefinition(
            evidence_type="ELIGIBILITY_PROOF_DOCUMENT",
            label_en="Social / Economic Priority Proof (BPL/SC-ST/e-Shram)",
            label_hi="सामाजिक / आर्थिक प्राथमिकता प्रमाण (बीपीएल/एससी-एसटी/ई-श्रम)",
            description_en="Documentary proof verifying membership in one of the eligible socio-economic priority categories.",
            description_hi="पात्र सामाजिक-आर्थिक प्राथमिकता श्रेणियों में से एक की सदस्यता को सत्यापित करने वाला दस्तावेजी प्रमाण।",
            mandatory=True,
            associated_field_keys=["applicant.is_sc_st", "family.has_bpl_or_nfsa_ration_card"],
        ),
        FormEvidenceDefinition(
            evidence_type="BIRTH_CERTIFICATE",
            label_en="Child Birth Certificate",
            label_hi="बच्चे का जन्म प्रमाण पत्र",
            description_en="Official birth certificate verifying birth order and gender of the second girl child.",
            description_hi="दूसरे बच्चे के जन्म क्रम और बालिका होने को सत्यापित करने वाला आधिकारिक जन्म प्रमाण पत्र।",
            mandatory=False,
            associated_field_keys=["maternity.is_girl_child"],
        ),
    ]

    return PolicyFormMetadata(
        scheme_code="PMMVY",
        policy_version_code="v2.0-2022",
        effective_from="2022-04-01",
        sections=sections,
        fields=fields,
        evidence_types=evidence_types,
    )


def _build_ignoaps_v1_form() -> PolicyFormMetadata:
    """Build canonical form metadata for IGNOAPS v1.0-2011."""
    sections = [
        FormSectionDefinition(
            section_key="senior_demographics",
            title_en="Senior Citizen Demographics & Age",
            title_hi="वरिष्ठ नागरिक जनसांख्यिकी एवं आयु",
            description_en="Verification of senior citizen identity and attainment of 60 years of age.",
            description_hi="वरिष्ठ नागरिक की पहचान और 60 वर्ष की आयु पूर्ण होने का सत्यापन।",
            display_order=1,
        ),
        FormSectionDefinition(
            section_key="bpl_status",
            title_en="Below Poverty Line (BPL) Status",
            title_hi="गरीबी रेखा से नीचे (बीपीएल) स्थिति",
            description_en="Certification that the senior citizen belongs to a verified BPL household.",
            description_hi="प्रमाणन कि वरिष्ठ नागरिक एक सत्यापित बीपीएल परिवार से संबंधित है।",
            display_order=2,
        ),
        FormSectionDefinition(
            section_key="pension_exclusions",
            title_en="Other Social Security Pension Disclosure",
            title_hi="अन्य सामाजिक सुरक्षा पेंशन प्रकटीकरण",
            description_en="Declaration verifying applicant is not receiving another regular government social pension.",
            description_hi="घोषणा कि आवेदक अन्य किसी नियमित सरकारी सामाजिक पेंशन का लाभ नहीं ले रहा है।",
            display_order=3,
        ),
    ]

    fields = [
        FormFieldDefinition(
            field_key="applicant.age",
            claim_type="applicant.age",
            field_type="integer",
            required=True,
            label_en="Senior Citizen Age (Years)",
            label_hi="वरिष्ठ नागरिक की आयु (वर्ष)",
            help_text_en="Applicant must have attained at least 60 years of age.",
            help_text_hi="आवेदक की आयु कम से कम 60 वर्ष पूर्ण होनी चाहिए।",
            validation_message_en="Applicant must be at least 60 years old.",
            validation_message_hi="आवेदक की आयु कम से कम 60 वर्ष होनी चाहिए।",
            section_key="senior_demographics",
            display_order=1,
            min_value=60.0,
            max_value=130.0,
            associated_evidence_type="AADHAAR",
        ),
        FormFieldDefinition(
            field_key="family.is_bpl",
            claim_type="family.is_bpl",
            field_type="boolean",
            required=True,
            label_en="Household Belongs to Below Poverty Line (BPL)",
            label_hi="परिवार गरीबी रेखा से नीचे (बीपीएल) श्रेणी में है",
            help_text_en="Does the applicant household belong to Below Poverty Line category as per GoI criteria?",
            help_text_hi="क्या आवेदक परिवार भारत सरकार के मानदंडों के अनुसार गरीबी रेखा से नीचे (बीपीएल) श्रेणी में आता है?",
            validation_message_en="Applicant must belong to a BPL household.",
            validation_message_hi="आवेदक को बीपीएल परिवार से संबंधित होना चाहिए।",
            section_key="bpl_status",
            display_order=1,
            default_value=True,
            associated_evidence_type="BPL_CARD_OR_CERTIFICATE",
        ),
        FormFieldDefinition(
            field_key="applicant.has_other_social_security_pension",
            claim_type="applicant.has_other_social_security_pension",
            field_type="boolean",
            required=True,
            label_en="In Receipt of Another Statutory Social Security Pension",
            label_hi="अन्य किसी वैधानिक सामाजिक सुरक्षा पेंशन का लाभ प्राप्तकर्ता",
            help_text_en="Is the applicant receiving any other regular government social pension?",
            help_text_hi="क्या आवेदक को कोई अन्य नियमित सरकारी सामाजिक सुरक्षा पेंशन मिल रही है?",
            validation_message_en="Receipt of another regular social pension excludes the applicant.",
            validation_message_hi="अन्य नियमित सामाजिक पेंशन प्राप्त करने वाले बहिष्कृत हैं।",
            section_key="pension_exclusions",
            display_order=1,
            default_value=False,
        ),
    ]

    evidence_types = [
        FormEvidenceDefinition(
            evidence_type="AADHAAR",
            label_en="Aadhaar Card / Proof of Age",
            label_hi="आधार कार्ड / आयु प्रमाण पत्र",
            description_en="Official Aadhaar card or government proof certifying attainment of 60 years of age.",
            description_hi="60 वर्ष की आयु पूर्ण होने को सत्यापित करने वाला आधिकारिक आधार कार्ड या सरकारी आयु प्रमाण।",
            mandatory=True,
            associated_field_keys=["applicant.age"],
        ),
        FormEvidenceDefinition(
            evidence_type="BPL_CARD_OR_CERTIFICATE",
            label_en="BPL Ration Card / BPL Certificate",
            label_hi="बीपीएल राशन कार्ड / बीपीएल प्रमाण पत्र",
            description_en="Certified copy of BPL card or official BPL register certificate.",
            description_hi="बीपीएल कार्ड की प्रमाणित प्रति या आधिकारिक बीपीएल रजिस्टर प्रमाण पत्र।",
            mandatory=True,
            associated_field_keys=["family.is_bpl"],
        ),
        FormEvidenceDefinition(
            evidence_type="BANK_PASSBOOK",
            label_en="Bank / Post Office Account Passbook",
            label_hi="बैंक / डाकघर खाता पासबुक",
            description_en="Passbook of savings account for monthly pension credit via DBT.",
            description_hi="डीबीटी के माध्यम से मासिक पेंशन क्रेडिट के लिए बचत खाते की पासबुक।",
            mandatory=True,
        ),
    ]

    return PolicyFormMetadata(
        scheme_code="IGNOAPS",
        policy_version_code="v1.0-2011",
        effective_from="2011-06-09",
        sections=sections,
        fields=fields,
        evidence_types=evidence_types,
    )


# ==============================================================================
# In-Memory Registry of Policy Form Metadata
# ==============================================================================

_FORM_REGISTRY: Dict[Tuple[str, str], PolicyFormMetadata] = {}

def _register_metadata(meta: PolicyFormMetadata) -> None:
    """Register and validate policy form metadata."""
    validate_policy_form_metadata(meta)
    key = (meta.scheme_code.upper().strip(), meta.policy_version_code.strip())
    _FORM_REGISTRY[key] = meta


# Register all canonical policy versions for the 10 target schemes
_register_metadata(_build_pm_kisan_v3_form())
_register_metadata(_build_pm_kisan_v2_form())
_register_metadata(_build_pm_kisan_v1_form())
_register_metadata(_build_ssy_v3_form())
_register_metadata(_build_ssy_v2_form())
_register_metadata(_build_ssy_v1_form())
_register_metadata(_build_pm_kmy_v1_form())
_register_metadata(_build_pmuy_v2_form())
_register_metadata(_build_pm_vishwakarma_v1_form())
_register_metadata(_build_pmay_g_v1_form())
_register_metadata(_build_pmay_u_2_0_v1_form())
_register_metadata(_build_pm_svanidhi_v1_form())
_register_metadata(_build_pmmvy_v2_form())
_register_metadata(_build_ignoaps_v1_form())


# Default policy version fallback mapping
_DEFAULT_VERSIONS: Dict[str, str] = {
    "PM_KISAN": "v3.0-2023",
    "SSY": "v3.0-2024",
    "PM_KMY": "v1.0-2019",
    "PMUY": "v2.0-2021",
    "PM_VISHWAKARMA": "v1.0-2023",
    "PMAY_G": "v1.0-2016",
    "PMAY_U_2_0": "v1.0-2024",
    "PM_SVANIDHI": "v1.0-2020",
    "PMMVY": "v2.0-2022",
    "IGNOAPS": "v1.0-2011",
}


def get_policy_form_metadata(
    scheme_code: str,
    version_code: Optional[str] = None,
) -> PolicyFormMetadata:
    """Retrieve validated policy form metadata for a scheme and version.
    
    Raises:
        SchemeFormNotSupportedError: If scheme is not supported or has no metadata.
    """
    normalized_code = scheme_code.upper().strip()
    target_version = version_code.strip() if version_code else _DEFAULT_VERSIONS.get(normalized_code)

    if not target_version:
        raise SchemeFormNotSupportedError(
            f"Statutory form configuration is not available for scheme '{scheme_code}'. "
            f"Supported schemes: {sorted(_DEFAULT_VERSIONS.keys())}."
        )

    key = (normalized_code, target_version)
    if key not in _FORM_REGISTRY:
        # Fall back to default version if specific version isn't in registry
        default_v = _DEFAULT_VERSIONS.get(normalized_code)
        if default_v and (normalized_code, default_v) in _FORM_REGISTRY:
            key = (normalized_code, default_v)
        else:
            raise SchemeFormNotSupportedError(
                f"Statutory form configuration is not available for scheme '{scheme_code}' version '{target_version}'."
            )

    return _FORM_REGISTRY[key].model_copy(deep=True)


def list_supported_form_schemes() -> List[str]:
    """Return list of schemes that have registered generic form metadata."""
    return sorted(list({code for (code, _) in _FORM_REGISTRY.keys()}))
