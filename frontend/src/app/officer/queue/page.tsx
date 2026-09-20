"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FileText,
  Filter,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Search,
  ShieldAlert,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { officerApi } from "@/api/officer";
import { OfficerQueueItem, OfficerQueueMetrics } from "@/types/officer";

export default function OfficerQueuePage() {
  const { isAuthenticated, isLoading: authLoading, token } = useOfficerAuth();
  const router = useRouter();

  const [items, setItems] = useState<OfficerQueueItem[]>([]);
  const [metrics, setMetrics] = useState<OfficerQueueMetrics>({
    total_cases: 0,
    pending_cases: 0,
    in_review_cases: 0,
    escalated_cases: 0,
    completed_cases: 0,
  });
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [schemeFilter, setSchemeFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/officer/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const loadQueue = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await officerApi.getQueue(
        { status: statusFilter, scheme: schemeFilter },
        token
      );
      setItems(res.items);
      setMetrics(res.metrics);
    } catch (err: any) {
      setError(err?.message || "Failed to load verification queue");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && token) {
      loadQueue();
    }
  }, [isAuthenticated, token, statusFilter, schemeFilter]);

  const filteredItems = items.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.citizen_ref.toLowerCase().includes(q) ||
      item.scheme_name.toLowerCase().includes(q) ||
      item.scheme_code.toLowerCase().includes(q)
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PENDING":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            Pending Review
          </span>
        );
      case "IN_REVIEW":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            In Review
          </span>
        );
      case "ESCALATED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
            Escalated to Supervisor
          </span>
        );
      case "CLARIFICATION_REQUIRED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-200">
            Clarification Required
          </span>
        );
      case "VERIFIED":
      case "COMPLETED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-800 border border-green-200">
            Completed
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-800 border border-red-200">
            Rejected
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  const getEligibilityBadge = (determination?: string | null) => {
    if (!determination) {
      return (
        <span className="text-xs text-slate-400 italic">Not Evaluated</span>
      );
    }
    if (determination === "ELIGIBLE") {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-green-50 text-green-700 border border-green-200">
          ELIGIBLE
        </span>
      );
    }
    if (determination === "INELIGIBLE") {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-red-50 text-red-700 border border-red-200">
          INELIGIBLE
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
        INSUFFICIENT INFO
      </span>
    );
  };

  if (authLoading) {
    return (
      <div className="py-16 text-center text-slate-500 text-sm">
        Authenticating officer session...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Title Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Verification Queue
          </h1>
          <p className="text-sm text-slate-600">
            Active welfare evaluation cases requiring authorized human review and evidence verification.
          </p>
        </div>
        <button
          onClick={loadQueue}
          disabled={loading}
          className="self-start sm:self-auto px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-sm flex items-center space-x-2 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Operational Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Total in Queue
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-1">
            {metrics.total_cases}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-amber-200 bg-amber-50/20 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-amber-700">
            Pending Review
          </div>
          <div className="text-2xl font-bold text-amber-900 mt-1">
            {metrics.pending_cases}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-blue-200 bg-blue-50/20 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-blue-700">
            In Review
          </div>
          <div className="text-2xl font-bold text-blue-900 mt-1">
            {metrics.in_review_cases}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-purple-200 bg-purple-50/20 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-purple-700">
            Escalated
          </div>
          <div className="text-2xl font-bold text-purple-900 mt-1">
            {metrics.escalated_cases}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-green-200 bg-green-50/20 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-green-700">
            Completed
          </div>
          <div className="text-2xl font-bold text-green-900 mt-1">
            {metrics.completed_cases}
          </div>
        </div>
      </div>

      {/* Filter and Search Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Status Filter */}
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Status:
            </span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border border-slate-300 rounded-md px-2.5 py-1.5 bg-white text-slate-700 focus:ring-1 focus:ring-blue-500 outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending Review</option>
              <option value="IN_REVIEW">In Review</option>
              <option value="ESCALATED">Escalated</option>
              <option value="COMPLETED">Completed</option>
            </select>
          </div>

          {/* Scheme Filter */}
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Scheme:
            </span>
            <select
              value={schemeFilter}
              onChange={(e) => setSchemeFilter(e.target.value)}
              className="text-xs border border-slate-300 rounded-md px-2.5 py-1.5 bg-white text-slate-700 focus:ring-1 focus:ring-blue-500 outline-none"
            >
              <option value="ALL">All Schemes</option>
              <option value="PM_KISAN">PM-KISAN</option>
              <option value="SSY">Sukanya Samriddhi (SSY)</option>
            </select>
          </div>
        </div>

        {/* Search Query Input */}
        <div className="relative w-full md:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search citizen ref or scheme..."
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-2">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Cases Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="px-5 py-3.5">Citizen Reference</th>
                <th className="px-5 py-3.5">Scheme</th>
                <th className="px-5 py-3.5">Submission Date</th>
                <th className="px-5 py-3.5">Auto Determination</th>
                <th className="px-5 py-3.5">Review Status</th>
                <th className="px-5 py-3.5">Evidence Verified</th>
                <th className="px-5 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-500 text-xs">
                    Loading cases from verification queue...
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-500 text-xs">
                    No cases match the selected queue criteria.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => (
                  <tr
                    key={item.journey_id}
                    className="hover:bg-slate-50/70 transition-colors"
                  >
                    <td className="px-5 py-4 font-mono text-xs font-semibold text-slate-800">
                      {item.citizen_ref}
                    </td>
                    <td className="px-5 py-4">
                      <div className="font-medium text-slate-900 text-xs">
                        {item.scheme_name}
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        {item.scheme_code}
                      </div>
                    </td>
                    <td className="px-5 py-4 text-xs text-slate-600">
                      {new Date(item.submitted_at).toLocaleDateString("en-IN", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </td>
                    <td className="px-5 py-4">
                      {getEligibilityBadge(item.automated_eligibility)}
                    </td>
                    <td className="px-5 py-4">
                      {getStatusBadge(item.review_status)}
                    </td>
                    <td className="px-5 py-4 text-xs font-medium text-slate-700">
                      {item.verified_evidence_count} / {item.evidence_count} items
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        href={`/officer/cases/${item.journey_id}`}
                        className="inline-flex items-center space-x-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold transition-colors shadow-sm"
                      >
                        <span>Inspect Case</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
