"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { ProductRole } from "@/types/auth";
import { ShieldAlert, ArrowLeft, LogIn } from "lucide-react";
import Link from "next/link";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole: ProductRole;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
}) => {
  const { role, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      const redirectParam = pathname ? `?redirect=${encodeURIComponent(pathname)}` : "";
      if (requiredRole === "OFFICER") {
        router.push(`/officer/login${redirectParam}`);
      } else {
        router.push(`/citizen/login${redirectParam}`);
      }
    }
  }, [isLoading, isAuthenticated, requiredRole, pathname, router]);

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center p-8 text-center" role="status">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm font-medium text-gov-secondary">
          प्रमाणीकरण की पुष्टि हो रही है... / Verifying authorization...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect via useEffect
  }

  // Cross-role access violation
  if (role !== requiredRole) {
    const isCitizenTryingOfficer = role === "CITIZEN" && requiredRole === "OFFICER";
    return (
      <div className="gov-container py-12 max-w-2xl mx-auto">
        <div className="bg-white border-2 border-red-200 rounded-lg p-8 shadow-sm">
          <div className="flex items-center space-x-3 text-red-600 mb-4">
            <ShieldAlert className="w-8 h-8" />
            <h1 className="text-xl font-bold text-gov-text">
              {isCitizenTryingOfficer
                ? "अनाधिकृत पहुंच / Access Restricted: Officer Portal"
                : "अनाधिकृत पहुंच / Access Restricted: Citizen Portal"}
            </h1>
          </div>

          <p className="text-sm text-gov-secondary mb-6 leading-relaxed">
            {isCitizenTryingOfficer
              ? "Your current session is logged in as a Citizen. Access to the internal Officer Verification & Policy Portal is restricted to authorized government officers. Please log in with official officer credentials."
              : "Your current session is logged in as an Officer. This section is specifically for citizen beneficiaries. Please log in with a citizen account to access your personal citizen claims."}
          </p>

          <div className="flex flex-wrap gap-4 pt-4 border-t border-gov-border">
            <Link
              href={isCitizenTryingOfficer ? "/officer/login" : "/citizen/login"}
              className="gov-button-primary inline-flex items-center space-x-2 text-sm px-4 py-2.5 rounded-md"
            >
              <LogIn className="w-4 h-4" />
              <span>
                {isCitizenTryingOfficer
                  ? "अधिकारी लॉगिन / Officer Login"
                  : "नागरिक लॉगिन / Citizen Login"}
              </span>
            </Link>
            <Link
              href="/"
              className="gov-button-secondary inline-flex items-center space-x-2 text-sm px-4 py-2.5 rounded-md"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>मुख्य पृष्ठ पर लौटें / Return Home</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
