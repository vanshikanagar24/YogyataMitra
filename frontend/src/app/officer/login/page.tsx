"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, Lock, AlertTriangle, KeyRound, UserCheck, CheckCircle2 } from "lucide-react";
import { useOfficerAuth } from "@/context/OfficerAuthContext";

export default function OfficerLoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login, isAuthenticated } = useOfficerAuth();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) {
      router.push("/officer/queue");
    }
  }, [isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
      router.push("/officer/queue");
    } catch (err: any) {
      setError(
        err?.message ||
          "Authentication failed. Please verify demo credentials or check if the backend service is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="max-w-xl mx-auto py-8">
      {/* Formal Header Card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        {/* Banner */}
        <div className="bg-slate-900 text-white p-6 border-b border-slate-800">
          <div className="flex items-center space-x-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-sm">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">
                DEVELOPMENT OFFICER LOGIN
              </h1>
              <p className="text-xs text-blue-300 font-medium">
                DEMO ENVIRONMENT ONLY &bull; BACK-OFFICE VERIFICATION
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed mt-2">
            Authorized portal for inspecting citizen claims, reviewing documentary evidence,
            and recording statutory verification determinations.
          </p>
        </div>

        {/* Demo Notice Warning */}
        <div className="p-4 bg-amber-50 border-b border-amber-200 flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900 leading-relaxed">
            <strong>Demonstration & Local Testing Notice:</strong> Production deployments
            integrate with official Government Single Sign-On (e.g. Parichay / e-Pramaan / Jan Parichay).
            Do not enter real citizen Aadhaar numbers or production government credentials here.
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Quick-Fill Demo Accounts Section */}
          <div className="space-y-2.5">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Quick-Fill Demo Credentials:
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => handleQuickFill("officer@yogyatamitra.local", "Officer@123")}
                className="p-3 text-left rounded-lg border border-slate-200 hover:border-blue-500 hover:bg-blue-50/50 transition-colors group"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-slate-900 group-hover:text-blue-700">
                    Verification Officer
                  </span>
                  <span className="px-1.5 py-0.5 text-[10px] font-bold bg-blue-100 text-blue-800 rounded">
                    OFFICER
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 font-mono">
                  officer@yogyatamitra.local
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill("supervisor@yogyatamitra.local", "Supervisor@123")}
                className="p-3 text-left rounded-lg border border-slate-200 hover:border-purple-500 hover:bg-purple-50/50 transition-colors group"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-slate-900 group-hover:text-purple-700">
                    Welfare Supervisor
                  </span>
                  <span className="px-1.5 py-0.5 text-[10px] font-bold bg-purple-100 text-purple-800 rounded">
                    SUPERVISOR
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 font-mono">
                  supervisor@yogyatamitra.local
                </div>
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1.5">
                Officer Email / User ID
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="officer@yogyatamitra.local"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-lg shadow-sm transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              {loading ? (
                <span>Authenticating Officer...</span>
              ) : (
                <>
                  <KeyRound className="w-4 h-4" />
                  <span>Sign In to Verification Portal</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
