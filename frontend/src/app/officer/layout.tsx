"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, Lock, LogOut, CheckCircle2, UserCheck, AlertTriangle, FileText, Sparkles, FileCode2 } from "lucide-react";
import { OfficerAuthProvider, useOfficerAuth } from "@/context/OfficerAuthContext";

function OfficerHeader() {
  const { officer, isAuthenticated, logout } = useOfficerAuth();
  const pathname = usePathname();
  const isLoginPage = pathname === "/officer/login";

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50">
      {/* Top Warning Banner */}
      <div className="bg-amber-500 text-slate-950 text-xs px-4 py-1.5 font-medium flex items-center justify-between">
        <div className="flex items-center space-x-2 max-w-7xl mx-auto w-full">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 text-slate-950" />
          <span>
            <strong>DEVELOPMENT DEMO ENVIRONMENT:</strong> For local evaluation and testing only.
            Production systems require official Government SSO (Parichay / e-Pramaan). Real citizen Aadhaar data is not accepted.
          </span>
        </div>
      </div>

      {/* Main Officer Nav */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link href="/officer" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-md">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="text-base font-bold tracking-tight text-white group-hover:text-blue-300 transition-colors">
                YogyataMitra
              </div>
              <div className="text-xs text-blue-400 font-medium">
                Officer Verification Portal
              </div>
            </div>
          </Link>

          <span className="hidden sm:inline-block px-2.5 py-0.5 rounded text-[11px] font-semibold tracking-wide uppercase bg-slate-800 text-slate-300 border border-slate-700">
            Internal Back-Office
          </span>
        </div>

        {/* Right side authentication profile & logout */}
        <div className="flex items-center space-x-4">
          {isAuthenticated && officer ? (
            <>
              <nav className="hidden md:flex items-center space-x-2 mr-2">
                <Link
                  href="/officer/queue"
                  className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                    pathname?.startsWith("/officer/queue") || pathname?.startsWith("/officer/cases")
                      ? "bg-blue-600/30 text-blue-300 border border-blue-500/40"
                      : "text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Verification Queue</span>
                </Link>

                <Link
                  href="/officer/policy-discovery"
                  className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                    pathname?.startsWith("/officer/policy-discovery")
                      ? "bg-blue-600/30 text-blue-300 border border-blue-500/40"
                      : "text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                  <span>Policy Discovery</span>
                </Link>

                <Link
                  href="/officer/policy-authoring"
                  className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                    pathname?.startsWith("/officer/policy-authoring")
                      ? "bg-blue-600/30 text-blue-300 border border-blue-500/40"
                      : "text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  <FileCode2 className="w-3.5 h-3.5 text-amber-400" />
                  <span>Policy Authoring</span>
                </Link>
              </nav>

              <div className="flex items-center space-x-3 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60">
                <div className="text-right hidden sm:block">
                  <div className="text-xs font-semibold text-white leading-tight">
                    {officer.name}
                  </div>
                  <div className="text-[11px] text-slate-400">
                    {officer.designation}
                  </div>
                </div>

                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                    officer.role === "SUPERVISOR"
                      ? "bg-purple-900/80 text-purple-200 border border-purple-600/50"
                      : "bg-blue-900/80 text-blue-200 border border-blue-600/50"
                  }`}
                >
                  {officer.role}
                </span>

                <button
                  onClick={logout}
                  title="Sign out of Officer Portal"
                  className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-700/50 rounded transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </>
          ) : !isLoginPage ? (
            <Link
              href="/officer/login"
              className="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-md transition-colors flex items-center space-x-1.5"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Officer Login</span>
            </Link>
          ) : null}
        </div>
      </div>
    </header>
  );
}

export default function OfficerLayout({ children }: { children: React.ReactNode }) {
  return (
    <OfficerAuthProvider>
      <div className="min-h-screen bg-slate-100 flex flex-col">
        <OfficerHeader />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>
      </div>
    </OfficerAuthProvider>
  );
}
