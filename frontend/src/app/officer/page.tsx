"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FileText,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Users,
  ShieldCheck,
  ArrowRight,
  RefreshCw,
  Inbox,
  AlertCircle,
} from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";
import { officerApi } from "@/api/officer";
import { OfficerDashboardStats } from "@/types/officer";

export default function OfficerDashboardPage() {
  const { isAuthenticated, isLoading: authLoading, token, officer } = useOfficerAuth();
  const router = useRouter();

  const [stats, setStats] = useState<OfficerDashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/officer/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const loadStats = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await officerApi.getDashboardStats(token);
      setStats(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load officer dashboard statistics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && token) {
      loadStats();
    }
  }, [isAuthenticated, token]);

  if (authLoading || (loading && !stats)) {
    return (
      <div className="py-16 text-center text-slate-500 text-sm">
        <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-400" />
        Authenticating officer session and retrieving operational metrics...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Title & Profile Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Officer Verification Dashboard
          </h1>
          <p className="text-xs sm:text-sm text-slate-600">
            Workload distribution, operational queue metrics, and SLA compliance tracking.
          </p>
        </div>
        <button
          onClick={loadStats}
          disabled={loading}
          className="self-start sm:self-auto px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-sm flex items-center space-x-2 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {/* Non-Statutory Operational Notice */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600 flex items-start space-x-3">
        <ShieldCheck className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-800">Statutory Notice:</span>{" "}
          YogyataMitra prepares deterministic verification assessments. Official statutory sanction
          and benefit authorization remain strictly within the authority of the competent government authority.
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Primary Workload & SLA KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* 1. My Active Workload */}
        <Link
          href="/officer/queue?assigned_to_me=true"
          className="bg-white p-4 rounded-xl border border-blue-200 hover:border-blue-400 bg-blue-50/10 shadow-sm transition-all group"
        >
          <div className="text-xs font-semibold uppercase tracking-wider text-blue-700 flex items-center justify-between">
            <span>My Active</span>
            <Users className="w-3.5 h-3.5 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-blue-900 mt-1">
            {stats?.my_active_requests ?? 0}
          </div>
          <div className="text-[11px] text-blue-600 mt-1 flex items-center group-hover:translate-x-0.5 transition-transform">
            <span>Assigned to me</span>
            <ArrowRight className="w-3 h-3 ml-1" />
          </div>
        </Link>

        {/* 2. Unassigned Queue */}
        <Link
          href="/officer/queue?unassigned=true"
          className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-400 shadow-sm transition-all group"
        >
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-600 flex items-center justify-between">
            <span>Unassigned</span>
            <Inbox className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-1">
            {stats?.unassigned_requests ?? 0}
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center group-hover:translate-x-0.5 transition-transform">
            <span>Awaiting balancer</span>
            <ArrowRight className="w-3 h-3 ml-1" />
          </div>
        </Link>

        {/* 3. Due Soon */}
        <Link
          href="/officer/queue?sla=DUE_SOON"
          className="bg-white p-4 rounded-xl border border-amber-200 hover:border-amber-400 bg-amber-50/20 shadow-sm transition-all group"
        >
          <div className="text-xs font-semibold uppercase tracking-wider text-amber-700 flex items-center justify-between">
            <span>Due Soon</span>
            <Clock className="w-3.5 h-3.5 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-amber-900 mt-1">
            {stats?.due_soon ?? 0}
          </div>
          <div className="text-[11px] text-amber-600 mt-1 flex items-center group-hover:translate-x-0.5 transition-transform">
            <span>Within 12 hours</span>
            <ArrowRight className="w-3 h-3 ml-1" />
          </div>
        </Link>

        {/* 4. Overdue */}
        <Link
          href="/officer/queue?sla=OVERDUE"
          className="bg-white p-4 rounded-xl border border-red-200 hover:border-red-400 bg-red-50/20 shadow-sm transition-all group"
        >
          <div className="text-xs font-semibold uppercase tracking-wider text-red-700 flex items-center justify-between">
            <span>Overdue SLA</span>
            <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
          </div>
          <div className="text-2xl font-bold text-red-900 mt-1">
            {stats?.overdue ?? 0}
          </div>
          <div className="text-[11px] text-red-600 mt-1 flex items-center group-hover:translate-x-0.5 transition-transform">
            <span>Past SLA target</span>
            <ArrowRight className="w-3 h-3 ml-1" />
          </div>
        </Link>

        {/* 5. Completed */}
        <Link
          href="/officer/queue?status=COMPLETED"
          className="bg-white p-4 rounded-xl border border-green-200 hover:border-green-400 bg-green-50/20 shadow-sm transition-all group"
        >
          <div className="text-xs font-semibold uppercase tracking-wider text-green-700 flex items-center justify-between">
            <span>Completed</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-green-900 mt-1">
            {stats?.completed ?? 0}
          </div>
          <div className="text-[11px] text-green-600 mt-1 flex items-center group-hover:translate-x-0.5 transition-transform">
            <span>Resolved cases</span>
            <ArrowRight className="w-3 h-3 ml-1" />
          </div>
        </Link>

        {/* 6. Total Active Workload */}
        <Link
          href="/officer/queue"
          className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-400 shadow-sm transition-all group"
        >
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center justify-between">
            <span>Total Active</span>
            <FileText className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-1">
            {stats?.total_active_workload ?? 0}
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center group-hover:translate-x-0.5 transition-transform">
            <span>All active cases</span>
            <ArrowRight className="w-3 h-3 ml-1" />
          </div>
        </Link>
      </div>

      {/* Operational Policy & Capacity Context */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-2">
            <Users className="w-4 h-4 text-blue-600" />
            <span>Workload Capacity Governance</span>
          </h2>
          <div className="text-xs text-slate-600 space-y-2">
            <p>
              Officer workload capacity is governed by operational thresholds to prevent verification
              bottlenecks. The current configured operational capacity is{" "}
              <span className="font-semibold text-slate-900">
                {stats?.max_capacity_per_officer ?? 15} active cases
              </span>{" "}
              per officer.
            </p>
            <p className="text-[11px] text-slate-500">
              * Capacity is an operational workflow control, not a statutory restriction. The least-loaded
              deterministic algorithm routes new applications to officers with the lowest active backlog.
            </p>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-2">
            <Clock className="w-4 h-4 text-amber-600" />
            <span>SLA Target Duration</span>
          </h2>
          <div className="text-xs text-slate-600 space-y-2">
            <p>
              Standard verification turnaround targets are configured at{" "}
              <span className="font-semibold text-slate-900">
                {stats?.default_sla_duration_hours ?? 48} hours (2 days)
              </span>{" "}
              from assignment timestamp.
            </p>
            <p className="text-[11px] text-slate-500">
              * Turnaround targets represent internal service level benchmarks to monitor workflow
              efficiency. Statutory authority granting timeframes are governed separately by official Citizen Charters.
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Actions */}
      <div className="flex flex-wrap gap-3">
        <Link
          href="/officer/queue"
          className="px-4 py-2.5 bg-blue-700 hover:bg-blue-800 text-white text-xs font-semibold rounded-lg shadow-sm flex items-center space-x-2 transition-colors"
        >
          <FileText className="w-4 h-4" />
          <span>Open Full Verification Queue</span>
        </Link>
        <Link
          href="/officer/queue?assigned_to_me=true"
          className="px-4 py-2.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-sm flex items-center space-x-2 transition-colors"
        >
          <Users className="w-4 h-4 text-slate-500" />
          <span>View My Assigned Cases</span>
        </Link>
        <Link
          href="/officer/queue?unassigned=true"
          className="px-4 py-2.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-sm flex items-center space-x-2 transition-colors"
        >
          <Inbox className="w-4 h-4 text-slate-500" />
          <span>Inspect Unassigned Pool</span>
        </Link>
      </div>
    </div>
  );
}
