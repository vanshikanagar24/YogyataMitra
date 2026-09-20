"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { officerApi } from "@/api/officer";
import { OfficerLoginResponse, OfficerProfile } from "@/types/officer";

interface OfficerAuthContextType {
  officer: OfficerProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isSupervisor: boolean;
  login: (email: string, password: string) => Promise<OfficerLoginResponse>;
  logout: () => void;
}

const OfficerAuthContext = createContext<OfficerAuthContextType | undefined>(undefined);

const TOKEN_KEY = "yogyatamitra_officer_token";
const PROFILE_KEY = "yogyatamitra_officer_profile";

export function OfficerAuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [officer, setOfficer] = useState<OfficerProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  useEffect(() => {
    // Restore session from localStorage on client mount
    try {
      const savedToken = localStorage.getItem(TOKEN_KEY);
      const savedProfile = localStorage.getItem(PROFILE_KEY);

      if (savedToken && savedProfile) {
        setToken(savedToken);
        setOfficer(JSON.parse(savedProfile));

        // Background verification of token validity
        officerApi
          .getProfile(savedToken)
          .then((profile) => {
            setOfficer(profile);
            localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
          })
          .catch(() => {
            // Token expired or invalid
            logout();
          });
      }
    } catch {
      // Storage parsing failed
      logout();
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string): Promise<OfficerLoginResponse> => {
    setIsLoading(true);
    try {
      const res = await officerApi.login({ email, password });
      const profile: OfficerProfile = {
        email,
        name: res.officer_name,
        role: res.officer_role,
        designation: res.designation,
        department: res.department,
      };

      setToken(res.access_token);
      setOfficer(profile);

      localStorage.setItem(TOKEN_KEY, res.access_token);
      localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));

      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setOfficer(null);
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(PROFILE_KEY);
    } catch {
      // Ignore storage errors
    }
    router.push("/officer/login");
  };

  const isSupervisor = officer?.role === "SUPERVISOR";

  return (
    <OfficerAuthContext.Provider
      value={{
        officer,
        token,
        isAuthenticated: !!token && !!officer,
        isLoading,
        isSupervisor,
        login,
        logout,
      }}
    >
      {children}
    </OfficerAuthContext.Provider>
  );
}

export function useOfficerAuth() {
  const context = useContext(OfficerAuthContext);
  if (!context) {
    throw new Error("useOfficerAuth must be used within an OfficerAuthProvider");
  }
  return context;
}
