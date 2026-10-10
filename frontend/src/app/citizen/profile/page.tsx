"use client";

import React from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/context/AuthContext";
import {
  User,
  Mail,
  MapPin,
  ShieldCheck,
  KeyRound,
  LogOut,
  ArrowLeft,
  Calendar,
} from "lucide-react";

function CitizenProfileContent() {
  const { citizen, logoutCitizen } = useAuth();

  return (
    <div className="gov-container py-8 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gov-border">
        <div>
          <div className="flex items-center space-x-2 text-gov-secondary text-xs mb-1">
            <Link href="/citizen/dashboard" className="hover:text-primary">
              नागरिक डैशबोर्ड / Dashboard
            </Link>
            <span>/</span>
            <span className="text-gov-text font-medium">मेरी प्रोफ़ाइल / My Profile</span>
          </div>
          <h1 className="text-2xl font-bold text-gov-text">
            नागरिक प्रोफ़ाइल विवरण / Citizen Profile Details
          </h1>
          <p className="text-xs text-gov-secondary mt-1">
            प्रमाणीकृत नागरिक लाभार्थी खाता / Authenticated Beneficiary Account
          </p>
        </div>

        <button
          type="button"
          onClick={logoutCitizen}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 px-3 py-2 rounded-md transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>लॉगआउट / Sign Out</span>
        </button>
      </div>

      {/* Main Profile Card */}
      <div className="bg-white border border-gov-border rounded-xl shadow-sm overflow-hidden">
        <div className="p-6 sm:p-8 space-y-6">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 rounded-full bg-primary-50 border border-primary-200 flex items-center justify-center text-primary flex-shrink-0">
              <User className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gov-text">
                {citizen?.citizen_name || "नागरिक"}
              </h2>
              <p className="text-xs text-gov-secondary">
                सत्यापित नागरिक लाभार्थी / Verified Citizen Beneficiary
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gov-border">
            <div className="p-4 bg-gray-50 rounded-lg border border-gov-border">
              <div className="text-xs font-semibold text-gov-secondary flex items-center gap-1.5 mb-1">
                <KeyRound className="w-3.5 h-3.5 text-primary" />
                सिंथेटिक संदर्भ संख्या / Synthetic Reference
              </div>
              <div className="font-mono text-sm font-bold text-primary">
                {citizen?.citizen_ref}
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg border border-gov-border">
              <div className="text-xs font-semibold text-gov-secondary flex items-center gap-1.5 mb-1">
                <Mail className="w-3.5 h-3.5 text-primary" />
                ईमेल पता / Registered Email
              </div>
              <div className="text-sm font-medium text-gov-text">
                {citizen?.email}
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg border border-gov-border">
              <div className="text-xs font-semibold text-gov-secondary flex items-center gap-1.5 mb-1">
                <MapPin className="w-3.5 h-3.5 text-primary" />
                राज्य एवं जिला / State & District
              </div>
              <div className="text-sm font-medium text-gov-text">
                {citizen?.district ? `${citizen.district}, ` : ""}
                {citizen?.state || "अनिर्दिष्ट / Not Specified"}
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg border border-gov-border">
              <div className="text-xs font-semibold text-gov-secondary flex items-center gap-1.5 mb-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                उत्पाद भूमिका / Product Role
              </div>
              <div className="text-sm font-bold text-emerald-700">
                CITIZEN (नागरिक)
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CitizenProfilePage() {
  return (
    <ProtectedRoute requiredRole="CITIZEN">
      <CitizenProfileContent />
    </ProtectedRoute>
  );
}
