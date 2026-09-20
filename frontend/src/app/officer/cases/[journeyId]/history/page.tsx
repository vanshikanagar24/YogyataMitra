"use client";

import React from "react";
import { History, Shield, User, Clock, ArrowRight, CheckCircle2, AlertCircle } from "lucide-react";
import { useCase } from "../CaseContext";

export default function CaseHistoryPage() {
  const { caseData, loading } = useCase();

  if (loading || !caseData) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
        Loading case audit history...
      </div>
    );
  }

  const events = caseData.audit_history || [];

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
            <History className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Immutable Verification Audit Trail ({events.length} events)
            </h2>
            <p className="text-xs text-slate-500">
              Complete chronological record of all officer actions and determinations on this journey.
            </p>
          </div>
        </div>

        <span className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
          Append-Only Log
        </span>
      </div>

      {/* Events Timeline / Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {events.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No audit actions have been recorded on this case yet.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {events.map((evt, idx) => (
              <div key={evt.id} className="p-5 hover:bg-slate-50/60 transition-colors space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-2.5">
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                      {evt.action}
                    </span>

                    {evt.previous_status && (
                      <div className="flex items-center space-x-1.5 text-xs text-slate-500 font-medium">
                        <span className="font-semibold text-slate-700">{evt.previous_status}</span>
                        <ArrowRight className="w-3 h-3 text-slate-400" />
                        <span className="font-bold text-slate-900">{evt.new_status}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-2 text-xs text-slate-500">
                    <Clock className="w-3.5 h-3.5" />
                    <span>
                      {new Date(evt.created_at).toLocaleString("en-IN", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                  </div>
                </div>

                {/* Actor */}
                <div className="text-xs text-slate-600 flex items-center space-x-2">
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  <span>
                    Actor: <strong className="text-slate-800">{evt.actor_identity}</strong>
                  </span>
                  <span
                    className={`px-1.5 py-0.2 rounded text-[10px] font-bold uppercase ${
                      evt.actor_role === "SUPERVISOR"
                        ? "bg-purple-100 text-purple-800"
                        : "bg-blue-100 text-blue-800"
                    }`}
                  >
                    {evt.actor_role}
                  </span>
                </div>

                {/* Reason */}
                {evt.reason && (
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-800 space-y-1">
                    <span className="font-bold text-slate-600 uppercase tracking-wider text-[10px] block">
                      Justification Reason:
                    </span>
                    <p className="leading-relaxed">{evt.reason}</p>
                  </div>
                )}

                {/* Details */}
                {evt.details_json && Object.keys(evt.details_json).length > 0 && (
                  <div className="text-[11px] font-mono text-slate-500 bg-slate-50/50 p-2 rounded">
                    Details: {JSON.stringify(evt.details_json)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
