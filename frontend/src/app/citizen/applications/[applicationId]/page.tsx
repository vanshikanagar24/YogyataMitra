"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/context/AuthContext";
import { citizenApi } from "@/api/citizen";
import { CitizenApplicationDetail } from "@/types/citizen";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Shield,
  FileText,
  Building2,
  Calendar,
  ExternalLink,
  RefreshCw,
  FileCheck2,
  UserCheck,
  History,
  MessageSquare,
  Send,
  UploadCloud,
} from "lucide-react";

function getStatusBadge(app: CitizenApplicationDetail) {
  if (app.state === "DRAFT") {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-300">
        <Clock className="w-4 h-4 text-amber-600" />
        प्रारूप / Draft (Unsubmitted)
      </span>
    );
  }

  if (app.state === "EVALUATED") {
    if (app.evaluation_outcome === "ELIGIBLE") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          पात्र / Eligible ({app.policy_version_code || "Evaluated"})
        </span>
      );
    }
    if (app.evaluation_outcome === "INELIGIBLE") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-900 border border-red-300">
          <AlertTriangle className="w-4 h-4 text-red-600" />
          अपात्र / Ineligible
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-900 border border-blue-300">
        <CheckCircle2 className="w-4 h-4 text-blue-600" />
        मूल्यांकित / Evaluated
      </span>
    );
  }

  if (app.state === "ACTION_REQUIRED") {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
        <AlertTriangle className="w-4 h-4 text-amber-700" />
        कार्रवाई आवश्यक / Action Required
      </span>
    );
  }

  if (app.state === "VERIFICATION_IN_PROGRESS") {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-900 border border-blue-300">
        <Clock className="w-4 h-4 text-blue-600" />
        सत्यापन प्रगति पर / Under Verification
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-800 border border-gray-300">
      {app.status_label_hi} / {app.status_label_en}
    </span>
  );
}

function CitizenApplicationDetailPage() {
  const params = useParams();
  const applicationId = params?.applicationId as string;
  const { citizen, citizenToken } = useAuth();

  const [application, setApplication] = useState<CitizenApplicationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Phase E: Clarification Response State
  const [responseTextMap, setResponseTextMap] = useState<Record<string, string>>({});
  const [docNameMap, setDocNameMap] = useState<Record<string, string>>({});
  const [storageRefMap, setStorageRefMap] = useState<Record<string, string>>({});
  const [submittingClarificationId, setSubmittingClarificationId] = useState<string | null>(null);
  const [clarificationError, setClarificationError] = useState<string | null>(null);
  const [clarificationSuccess, setClarificationSuccess] = useState<string | null>(null);

  const handleClarificationSubmit = async (clarificationId: string) => {
    if (!applicationId || !citizenToken) return;
    const responseText = responseTextMap[clarificationId]?.trim();
    if (!responseText) {
      setClarificationError("कृपया स्पष्टीकरण विवरण दर्ज करें / Please provide your clarification explanation.");
      return;
    }

    setSubmittingClarificationId(clarificationId);
    setClarificationError(null);
    setClarificationSuccess(null);

    const docName = docNameMap[clarificationId]?.trim();
    const storageRef = storageRefMap[clarificationId]?.trim();

    try {
      await citizenApi.respondClarification(
        applicationId,
        clarificationId,
        {
          response_text: responseText,
          replacement_evidence:
            docName && storageRef
              ? {
                  document_name: docName,
                  storage_reference: storageRef,
                }
              : undefined,
        },
        citizenToken
      );
      setClarificationSuccess("स्पष्टीकरण सफलतापूर्वक दर्ज किया गया / Clarification response submitted successfully.");
      await fetchDetail();
    } catch (err: any) {
      setClarificationError(err?.message || "स्पष्टीकरण सबमिट करने में विफल / Failed to submit clarification.");
    } finally {
      setSubmittingClarificationId(null);
    }
  };

  const fetchDetail = async () => {
    if (!applicationId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await citizenApi.getApplicationDetail(applicationId, citizenToken);
      setApplication(data);
    } catch (err: any) {
      setError(
        err?.response?.status === 404
          ? "Application not found or does not belong to your account."
          : err?.message || "Failed to load application details."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [applicationId, citizenToken]);

  if (loading) {
    return (
      <div className="gov-container py-12 max-w-4xl mx-auto text-center space-y-3">
        <RefreshCw className="w-7 h-7 animate-spin mx-auto text-primary" />
        <p className="text-xs text-gov-secondary">
          आवेदन डोज़ियर लोड हो रहा है... / Loading application dossier...
        </p>
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="gov-container py-12 max-w-2xl mx-auto">
        <div className="bg-white border border-red-200 rounded-xl p-6 text-center space-y-4 shadow-sm">
          <AlertTriangle className="w-8 h-8 text-red-600 mx-auto" />
          <h2 className="text-base font-bold text-gov-text">
            आवेदन नहीं मिल सका / Application Unavailable
          </h2>
          <p className="text-xs text-gov-secondary leading-relaxed">
            {error || "यह आवेदन मौजूद नहीं है अथवा आपके खाते से संबद्ध नहीं है।"}
          </p>
          <div className="pt-2">
            <Link
              href="/citizen/applications"
              className="gov-button-primary inline-flex items-center space-x-1.5 text-xs font-semibold px-4 py-2 rounded-md"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>मेरे आवेदनों पर लौटें / Back to My Applications</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="gov-container py-8 max-w-5xl mx-auto space-y-6">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center justify-between gap-4">
        <Link
          href="/citizen/applications"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-primary hover:underline"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>मेरे आवेदन सूची पर लौटें / Back to Applications</span>
        </Link>

        <span className="text-xs text-gov-secondary">
          सत्यापित सत्र / Authenticated Citizen Dossier
        </span>
      </div>

      {/* Draft State Notice Banner */}
      {application.state === "DRAFT" && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
          <div className="flex items-start sm:items-center space-x-3">
            <AlertTriangle className="w-6 h-6 text-amber-700 flex-shrink-0 mt-0.5 sm:mt-0" />
            <div>
              <h2 className="text-sm font-bold text-amber-900">
                यह आवेदन अभी प्रारूप में है / Application is in Draft State
              </h2>
              <p className="text-xs text-amber-800 mt-0.5 leading-relaxed">
                यह आवेदन अभी तक औपचारिक रूप से प्रस्तुत नहीं किया गया है। योजना मानदंडों के अनुसार तथ्य भरें, दस्तावेज़ संलग्न करें तथा वैधानिक घोषणा के साथ इसे जमा करें।
              </p>
            </div>
          </div>
          <Link
            href={`/citizen/applications/new?scheme=${application.scheme_code}&applicationId=${application.id}`}
            className="gov-button-primary inline-flex items-center space-x-1.5 text-xs font-semibold px-4 py-2 rounded-md flex-shrink-0 shadow-sm"
          >
            <span>आवेदन पूरा करें एवं जमा करें / Complete & Submit</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Action Required Banner for Clarifications (Phase E) */}
      {(application.state === "ACTION_REQUIRED" ||
        application.clarifications?.some((c) => c.status === "OPEN")) && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
          <div className="flex items-start sm:items-center space-x-3">
            <AlertTriangle className="w-6 h-6 text-amber-700 flex-shrink-0 mt-0.5 sm:mt-0" />
            <div>
              <h2 className="text-sm font-bold text-amber-900">
                कार्रवाई आवश्यक: स्पष्टीकरण अपेक्षित / Action Required: Clarification Requested
              </h2>
              <p className="text-xs text-amber-800 mt-0.5 leading-relaxed">
                सत्यापन अधिकारी ने आपके आवेदन के साक्ष्यों पर स्पष्टीकरण मांगा है। कृपया नीचे दिए गए खंड में अपना उत्तर अथवा पूरक साक्ष्य प्रस्तुत करें।
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Dossier Header Card */}
      <div className="bg-white border border-gov-border rounded-xl p-6 sm:p-8 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gov-border">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs font-bold text-primary bg-primary-50 px-3 py-1 rounded border border-primary-200">
                {application.application_ref}
              </span>
              <span className="text-xs font-semibold text-gov-secondary">
                योजना कोड: {application.scheme_code}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-gov-text">
              {application.scheme_name}
            </h1>
            {application.scheme_name_hi && (
              <p className="text-sm font-semibold text-gov-secondary">
                {application.scheme_name_hi}
              </p>
            )}
          </div>

          <div className="flex-shrink-0">{getStatusBadge(application)}</div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 text-xs">
          <div className="p-3 bg-gray-50 rounded-lg border border-gov-border">
            <span className="text-gov-secondary block mb-1">आवेदक संदर्भ / Beneficiary</span>
            <span className="font-mono font-bold text-primary">
              {application.citizen_ref}
            </span>
          </div>

          <div className="p-3 bg-gray-50 rounded-lg border border-gov-border">
            <span className="text-gov-secondary block mb-1">प्रस्तुत तिथि / Submitted On</span>
            <span className="font-semibold text-gov-text">
              {application.submitted_at
                ? new Date(application.submitted_at).toLocaleDateString("en-IN", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })
                : "असमर्पित प्रारूप / Draft (Not Yet Submitted)"}
            </span>
          </div>

          <div className="p-3 bg-gray-50 rounded-lg border border-gov-border">
            <span className="text-gov-secondary block mb-1">नोडल मंत्रालय / Ministry</span>
            <span className="font-semibold text-gov-text truncate block">
              {application.ministry || "भारत सरकार / Govt. of India"}
            </span>
          </div>
        </div>

        {application.official_url && (
          <div className="pt-2 flex items-center justify-end">
            <a
              href={application.official_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1.5 text-xs text-primary hover:underline"
            >
              <span>आधिकारिक पोर्टल विवरण / Official Scheme Guidelines</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        )}
      </div>

      {/* Statutory Evaluation Outcome Card (If Evaluated) */}
      {application.latest_evaluation && (
        <div
          className={`border rounded-xl p-6 shadow-sm space-y-4 ${
            application.latest_evaluation.result_state === "ELIGIBLE"
              ? "bg-emerald-50/70 border-emerald-200"
              : application.latest_evaluation.result_state === "INELIGIBLE"
              ? "bg-red-50/70 border-red-200"
              : application.latest_evaluation.result_state === "VERIFICATION_REQUIRED"
              ? "bg-blue-50/70 border-blue-200"
              : "bg-amber-50/70 border-amber-200"
          }`}
        >
          <div className="flex items-center space-x-3">
            {application.latest_evaluation.result_state === "ELIGIBLE" ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-700 flex-shrink-0" />
            ) : application.latest_evaluation.result_state === "INELIGIBLE" ? (
              <AlertTriangle className="w-6 h-6 text-red-700 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-6 h-6 text-amber-700 flex-shrink-0" />
            )}
            <div>
              <h2 className="text-base font-bold text-gov-text">
                वैधानिक पात्रता निर्णय / Statutory Eligibility Determination:{" "}
                <span
                  className={
                    application.latest_evaluation.result_state === "ELIGIBLE"
                      ? "text-emerald-800"
                      : application.latest_evaluation.result_state === "INELIGIBLE"
                      ? "text-red-800"
                      : application.latest_evaluation.result_state === "VERIFICATION_REQUIRED"
                      ? "text-blue-800"
                      : "text-amber-800"
                  }
                >
                  {application.latest_evaluation.result_state}
                </span>
              </h2>
              <p className="text-xs text-gov-secondary mt-0.5">
                लागू नियम संस्करण / Governing Policy:{" "}
                <strong>{application.latest_evaluation.policy_version_code || "Active Guidelines"}</strong> • मूल्यांकन तिथि:{" "}
                {application.latest_evaluation.evaluation_date}
              </p>
            </div>
          </div>

          {/* Bilingual Explainability Points */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            {/* English Reasons */}
            <div className="bg-white/80 p-4 rounded-lg border border-gov-border">
              <h3 className="text-xs font-bold text-gov-text mb-2 flex items-center gap-1.5">
                <FileCheck2 className="w-4 h-4 text-primary" />
                Statutory Assessment Findings (English)
              </h3>
              <ul className="text-xs text-gov-secondary space-y-1.5 list-disc pl-4">
                {application.latest_evaluation.reasons_en.length > 0 ? (
                  application.latest_evaluation.reasons_en.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))
                ) : (
                  <li>Criteria evaluated deterministically against policy ruleset.</li>
                )}
              </ul>
            </div>

            {/* Hindi Reasons */}
            <div className="bg-white/80 p-4 rounded-lg border border-gov-border">
              <h3 className="text-xs font-bold text-gov-text mb-2 flex items-center gap-1.5">
                <FileCheck2 className="w-4 h-4 text-primary" />
                वैधानिक मूल्यांकन निष्कर्ष (हिंदी)
              </h3>
              <ul className="text-xs text-gov-secondary space-y-1.5 list-disc pl-4">
                {application.latest_evaluation.reasons_hi.length > 0 ? (
                  application.latest_evaluation.reasons_hi.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))
                ) : (
                  <li>योजना दिशा-निर्देशों के अनुरूप सभी अनिवार्य मानदंडों का सत्यापन संपन्न।</li>
                )}
              </ul>
            </div>
          </div>

          {/* Statutory Disclaimers */}
          <div className="pt-2 border-t border-gov-border/60 text-[11px] text-gov-secondary space-y-1">
            <p>
              <strong>Notice:</strong> This eligibility evaluation is generated deterministically based on verified statutory criteria and documentary evidence. It does not constitute a final official government disbursement order.
            </p>
            <p>
              <strong>सूचना:</strong> यह पात्रता मूल्यांकन सत्यापित वैधानिक मानदंडों और दस्तावेजी साक्ष्यों के आधार पर निर्धारणात्मक रूप से उत्पन्न किया गया है। यह अंतिम आधिकारिक सरकारी संवितरण आदेश नहीं है।
            </p>
          </div>
        </div>
      )}

      {/* Clarification Requests & Citizen Responses (Phase E) */}
      {application.clarifications && application.clarifications.length > 0 && (
        <div className="bg-white border border-gov-border rounded-xl shadow-sm overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-gov-border bg-amber-50/50 flex items-center justify-between">
            <h2 className="text-sm font-bold text-gov-text flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-amber-700" />
              स्पष्टीकरण एवं पूरक साक्ष्य / Clarifications & Evidence Actions ({application.clarifications.length})
            </h2>
            <span className="text-xs font-semibold text-amber-800 bg-amber-100 px-2.5 py-0.5 rounded-full border border-amber-200">
              {application.verification_status || "सत्यापन / Verification"}
            </span>
          </div>

          <div className="p-5 space-y-6">
            {clarificationSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>{clarificationSuccess}</span>
              </div>
            )}

            {clarificationError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
                <span>{clarificationError}</span>
              </div>
            )}

            {application.clarifications.map((item) => (
              <div
                key={item.id}
                className={`p-4 rounded-xl border ${
                  item.status === "OPEN"
                    ? "bg-amber-50/40 border-amber-300"
                    : "bg-gray-50/60 border-gov-border"
                } space-y-3.5`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-2 border-gov-border/60">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-white border border-gov-border text-gov-text">
                      चरण {item.round} / Round {item.round}
                    </span>
                    <span className="text-xs font-bold text-gov-text">
                      {item.status === "OPEN"
                        ? "स्पष्टीकरण अपेक्षित / Action Required"
                        : `स्थिति: ${item.status}`}
                    </span>
                  </div>
                  <span className="text-[11px] text-gov-secondary">
                    अनुरोध तिथि / Requested:{" "}
                    {new Date(item.requested_at).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                <div className="text-xs text-gov-text">
                  <span className="font-semibold text-gov-secondary block mb-1">
                    अधिकारी द्वारा स्पष्टीकरण का कारण / Clarification Reason:
                  </span>
                  <p className="bg-white p-3 rounded-lg border border-gov-border text-slate-800">
                    {item.request_reason}
                  </p>
                </div>

                {/* If already responded */}
                {item.status !== "OPEN" && item.response_text && (
                  <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-lg text-xs space-y-1.5">
                    <span className="font-bold text-emerald-900 block">
                      आपका प्रस्तुत उत्तर / Your Submitted Response:
                    </span>
                    <p className="text-emerald-950 whitespace-pre-wrap">{item.response_text}</p>
                    {item.replacement_evidence_name && (
                      <p className="text-[11px] text-emerald-800 font-mono pt-1">
                        संलग्न पूरक दस्तावेज़: {item.replacement_evidence_name}
                      </p>
                    )}
                    {item.responded_at && (
                      <p className="text-[10px] text-emerald-700">
                        उत्तर दिया गया / Submitted on:{" "}
                        {new Date(item.responded_at).toLocaleString("en-IN")}
                      </p>
                    )}
                  </div>
                )}

                {/* If OPEN, show response form */}
                {item.status === "OPEN" && (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleClarificationSubmit(item.id);
                    }}
                    className="pt-2 space-y-3"
                  >
                    <div>
                      <label className="block text-xs font-bold text-gov-text mb-1">
                        आपका स्पष्टीकरण विवरण / Your Explanation *
                      </label>
                      <textarea
                        required
                        rows={3}
                        value={responseTextMap[item.id] || ""}
                        onChange={(e) =>
                          setResponseTextMap((prev) => ({
                            ...prev,
                            [item.id]: e.target.value,
                          }))
                        }
                        placeholder="कृपया स्पष्टीकरण का विवरण यहाँ लिखें / Please explain details clearly..."
                        className="w-full text-xs p-3 border border-gov-border rounded-lg focus:ring-1 focus:ring-primary outline-none"
                      />
                    </div>

                    <div className="bg-white p-3.5 rounded-lg border border-gov-border space-y-3">
                      <span className="text-xs font-bold text-gov-text block">
                        वैकल्पिक: पूरक / प्रतिस्थापन दस्तावेज़ संलग्न करें / Optional: Attach Replacement Evidence
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div>
                          <label className="block text-gov-secondary text-[11px] mb-1">
                            दस्तावेज़ का नाम / Document Name
                          </label>
                          <input
                            type="text"
                            value={docNameMap[item.id] || ""}
                            onChange={(e) =>
                              setDocNameMap((prev) => ({
                                ...prev,
                                [item.id]: e.target.value,
                              }))
                            }
                            placeholder="e.g. Land Revenue Record 2026.pdf"
                            className="w-full p-2 border border-gov-border rounded text-xs outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-gov-secondary text-[11px] mb-1">
                            भंडारण संदर्भ / Storage Reference
                          </label>
                          <input
                            type="text"
                            value={storageRefMap[item.id] || ""}
                            onChange={(e) =>
                              setStorageRefMap((prev) => ({
                                ...prev,
                                [item.id]: e.target.value,
                              }))
                            }
                            placeholder="e.g. docs/rev_rec_2026.pdf"
                            className="w-full p-2 border border-gov-border rounded text-xs outline-none font-mono"
                          />
                        </div>
                      </div>
                    </div>

                    <div className="flex justify-end pt-1">
                      <button
                        type="submit"
                        disabled={submittingClarificationId === item.id}
                        className="gov-button-primary inline-flex items-center space-x-1.5 text-xs font-semibold px-4 py-2 rounded-md shadow-sm disabled:opacity-50"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>
                          {submittingClarificationId === item.id
                            ? "स्पष्टीकरण भेजा जा रहा है... / Submitting..."
                            : "स्पष्टीकरण प्रस्तुत करें / Submit Clarification Response"}
                        </span>
                      </button>
                    </div>
                  </form>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Asserted Claims Section */}
      <div className="bg-white border border-gov-border rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-gov-border bg-gray-50 flex items-center justify-between">
          <h2 className="text-sm font-bold text-gov-text flex items-center gap-2">
            <FileText className="w-4 h-4 text-primary" />
            प्रस्तुत तथ्य एवं दावे / Asserted Factual Claims ({application.claims.length})
          </h2>
          <span className="text-xs text-gov-secondary">स्व-घोषणा / Declarations</span>
        </div>

        <div className="p-5 divide-y divide-gov-border">
          {application.claims.map((claim) => (
            <div key={claim.id} className="py-3.5 first:pt-0 last:pb-0 space-y-2">
              <div className="flex items-center justify-between gap-4">
                <div className="space-y-0.5">
                  <span className="font-mono text-xs font-bold text-gov-text">
                    {claim.claim_type.replace(/_/g, " ").toUpperCase()}
                  </span>
                  <div className="text-xs text-gov-secondary">
                    स्रोत / Source: {claim.source}
                  </div>
                </div>
                <span
                  className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                    claim.status === "VERIFIED"
                      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                      : claim.status === "REJECTED"
                      ? "bg-red-50 text-red-800 border-red-200"
                      : "bg-blue-50 text-blue-800 border-blue-200"
                  }`}
                >
                  {claim.status}
                </span>
              </div>

              {/* Claim Value Details */}
              <div className="p-3 bg-gray-50 rounded text-xs font-mono text-gov-text">
                <pre className="whitespace-pre-wrap font-sans text-xs">
                  {Object.entries(claim.value_json).map(([k, v]) => (
                    <span key={k} className="inline-block mr-4">
                      <strong>{k.replace(/_/g, " ")}:</strong> {String(v)}
                    </span>
                  ))}
                </pre>
              </div>

              {/* Attached Evidence for this claim */}
              {claim.evidence_items && claim.evidence_items.length > 0 && (
                <div className="pl-4 border-l-2 border-primary/30 mt-2 space-y-2">
                  <span className="text-[11px] font-bold text-gov-secondary uppercase tracking-wider block">
                    संलग्न दस्तावेज़ साक्ष्य / Attached Evidence:
                  </span>
                  {claim.evidence_items.map((ev) => (
                    <div
                      key={ev.id}
                      className="p-3 bg-white rounded border border-gov-border flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                    >
                      <div>
                        <div className="font-semibold text-gov-text">
                          दस्तावेज़: {ev.evidence_type.replace(/_/g, " ")}
                        </div>
                        <div className="text-[11px] text-gov-secondary font-mono">
                          {ev.storage_reference}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-bold border ${
                            ev.status === "VERIFIED"
                              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                              : ev.status === "REJECTED"
                              ? "bg-red-50 text-red-800 border-red-200"
                              : "bg-amber-50 text-amber-800 border-amber-200"
                          }`}
                        >
                          {ev.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Progress Timeline / Audit History */}
      <div className="bg-white border border-gov-border rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-gov-border bg-gray-50 flex items-center justify-between">
          <h2 className="text-sm font-bold text-gov-text flex items-center gap-2">
            <History className="w-4 h-4 text-primary" />
            प्रगति एवं सत्यापन इतिहास / Lifecycle Progress & Audit History
          </h2>
          <span className="text-xs text-gov-secondary">अपरिवर्तनीय लॉग / Immutable Audit</span>
        </div>

        <div className="p-6">
          <div className="relative border-l-2 border-primary/40 pl-6 space-y-6">
            {application.transitions.map((t, idx) => (
              <div key={t.id || idx} className="relative">
                {/* Timeline Dot */}
                <div className="absolute -left-[31px] top-0.5 w-3.5 h-3.5 rounded-full bg-primary border-2 border-white" />
                <div className="space-y-1">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-xs font-bold text-gov-text">
                      {t.from_state} → {t.to_state}
                    </span>
                    <span className="text-[11px] font-semibold text-primary bg-primary-50 px-2 py-0.5 rounded border border-primary-200">
                      कर्त्ता / Actor: {t.actor}
                    </span>
                    <span className="text-[11px] text-gov-secondary">
                      {new Date(t.created_at).toLocaleString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  {t.reason && (
                    <p className="text-xs text-gov-secondary leading-relaxed bg-gray-50 p-2 rounded border border-gov-border">
                      {t.reason}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CitizenApplicationDetailView() {
  return (
    <ProtectedRoute requiredRole="CITIZEN">
      <CitizenApplicationDetailPage />
    </ProtectedRoute>
  );
}
