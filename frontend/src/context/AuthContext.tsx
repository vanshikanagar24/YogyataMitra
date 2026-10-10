"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { citizenApi } from "@/api/citizen";
import { officerApi } from "@/api/officer";
import {
  CitizenAuthResponse,
  CitizenLoginPayload,
  CitizenProfile,
  CitizenSignupPayload,
  ProductRole,
} from "@/types/auth";
import { OfficerLoginResponse, OfficerProfile } from "@/types/officer";

interface AuthContextType {
  // Common
  role: ProductRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  logout: () => void;

  // Citizen
  citizen: CitizenProfile | null;
  citizenToken: string | null;
  loginCitizen: (credentials: CitizenLoginPayload) => Promise<CitizenAuthResponse>;
  signupCitizen: (payload: CitizenSignupPayload) => Promise<CitizenAuthResponse>;
  logoutCitizen: () => void;

  // Officer
  officer: OfficerProfile | null;
  officerToken: string | null;
  isSupervisor: boolean;
  loginOfficer: (credentials: { email: string; password: string }) => Promise<OfficerLoginResponse>;
  logoutOfficer: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const CITIZEN_TOKEN_KEY = "yogyatamitra_citizen_token";
const CITIZEN_PROFILE_KEY = "yogyatamitra_citizen_profile";
const OFFICER_TOKEN_KEY = "yogyatamitra_officer_token";
const OFFICER_PROFILE_KEY = "yogyatamitra_officer_profile";
const ACTIVE_ROLE_KEY = "yogyatamitra_active_role";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<ProductRole | null>(null);
  const [citizenToken, setCitizenToken] = useState<string | null>(null);
  const [citizen, setCitizen] = useState<CitizenProfile | null>(null);
  const [officerToken, setOfficerToken] = useState<string | null>(null);
  const [officer, setOfficer] = useState<OfficerProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  // Restore sessions on client mount
  useEffect(() => {
    try {
      const savedRole = localStorage.getItem(ACTIVE_ROLE_KEY) as ProductRole | null;
      const savedCitToken = localStorage.getItem(CITIZEN_TOKEN_KEY);
      const savedCitProfile = localStorage.getItem(CITIZEN_PROFILE_KEY);
      const savedOffToken = localStorage.getItem(OFFICER_TOKEN_KEY);
      const savedOffProfile = localStorage.getItem(OFFICER_PROFILE_KEY);

      if (savedCitToken && savedCitProfile) {
        setCitizenToken(savedCitToken);
        setCitizen(JSON.parse(savedCitProfile));
      }

      if (savedOffToken && savedOffProfile) {
        setOfficerToken(savedOffToken);
        setOfficer(JSON.parse(savedOffProfile));
      }

      if (savedRole === "OFFICER" && savedOffToken) {
        setRole("OFFICER");
      } else if (savedRole === "CITIZEN" && savedCitToken) {
        setRole("CITIZEN");
      } else if (savedCitToken) {
        setRole("CITIZEN");
      } else if (savedOffToken) {
        setRole("OFFICER");
      } else {
        setRole(null);
      }

      // Verify citizen token if active
      if (savedCitToken) {
        citizenApi
          .getProfile(savedCitToken)
          .then((profile) => {
            setCitizen(profile);
            localStorage.setItem(CITIZEN_PROFILE_KEY, JSON.stringify(profile));
          })
          .catch(() => {
            // Token expired
            if (savedRole === "CITIZEN") {
              setRole(null);
            }
            setCitizenToken(null);
            setCitizen(null);
            localStorage.removeItem(CITIZEN_TOKEN_KEY);
            localStorage.removeItem(CITIZEN_PROFILE_KEY);
          });
      }

      // Verify officer token if active
      if (savedOffToken) {
        officerApi
          .getProfile(savedOffToken)
          .then((profile) => {
            setOfficer(profile);
            localStorage.setItem(OFFICER_PROFILE_KEY, JSON.stringify(profile));
          })
          .catch(() => {
            if (savedRole === "OFFICER") {
              setRole(null);
            }
            setOfficerToken(null);
            setOfficer(null);
            localStorage.removeItem(OFFICER_TOKEN_KEY);
            localStorage.removeItem(OFFICER_PROFILE_KEY);
          });
      }
    } catch {
      // Storage or JSON parse error
    } finally {
      setIsLoading(false);
    }
  }, []);

  // --- Citizen Login ---
  const loginCitizen = async (
    credentials: CitizenLoginPayload
  ): Promise<CitizenAuthResponse> => {
    setIsLoading(true);
    try {
      const res = await citizenApi.login(credentials);
      const profile: CitizenProfile = {
        email: res.email,
        citizen_name: res.citizen_name,
        citizen_ref: res.citizen_ref,
        role: "CITIZEN",
        state: res.state,
        district: res.district,
      };

      setCitizenToken(res.access_token);
      setCitizen(profile);
      setRole("CITIZEN");

      localStorage.setItem(CITIZEN_TOKEN_KEY, res.access_token);
      localStorage.setItem(CITIZEN_PROFILE_KEY, JSON.stringify(profile));
      localStorage.setItem(ACTIVE_ROLE_KEY, "CITIZEN");

      return res;
    } finally {
      setIsLoading(false);
    }
  };

  // --- Citizen Signup ---
  const signupCitizen = async (
    payload: CitizenSignupPayload
  ): Promise<CitizenAuthResponse> => {
    setIsLoading(true);
    try {
      const res = await citizenApi.signup(payload);
      const profile: CitizenProfile = {
        email: res.email,
        citizen_name: res.citizen_name,
        citizen_ref: res.citizen_ref,
        role: "CITIZEN",
        state: res.state,
        district: res.district,
      };

      setCitizenToken(res.access_token);
      setCitizen(profile);
      setRole("CITIZEN");

      localStorage.setItem(CITIZEN_TOKEN_KEY, res.access_token);
      localStorage.setItem(CITIZEN_PROFILE_KEY, JSON.stringify(profile));
      localStorage.setItem(ACTIVE_ROLE_KEY, "CITIZEN");

      return res;
    } finally {
      setIsLoading(false);
    }
  };

  // --- Citizen Logout ---
  const logoutCitizen = useCallback(() => {
    setCitizenToken(null);
    setCitizen(null);
    if (role === "CITIZEN") {
      setRole(null);
      localStorage.removeItem(ACTIVE_ROLE_KEY);
    }
    try {
      localStorage.removeItem(CITIZEN_TOKEN_KEY);
      localStorage.removeItem(CITIZEN_PROFILE_KEY);
    } catch {
      // Ignore
    }
  }, [role]);

  // --- Officer Login ---
  const loginOfficer = async (credentials: {
    email: string;
    password: string;
  }): Promise<OfficerLoginResponse> => {
    setIsLoading(true);
    try {
      const res = await officerApi.login(credentials);
      const profile: OfficerProfile = {
        email: credentials.email,
        name: res.officer_name,
        role: res.officer_role,
        designation: res.designation,
        department: res.department,
      };

      setOfficerToken(res.access_token);
      setOfficer(profile);
      setRole("OFFICER");

      localStorage.setItem(OFFICER_TOKEN_KEY, res.access_token);
      localStorage.setItem(OFFICER_PROFILE_KEY, JSON.stringify(profile));
      localStorage.setItem(ACTIVE_ROLE_KEY, "OFFICER");

      return res;
    } finally {
      setIsLoading(false);
    }
  };

  // --- Officer Logout ---
  const logoutOfficer = useCallback(() => {
    setOfficerToken(null);
    setOfficer(null);
    if (role === "OFFICER") {
      setRole(null);
      localStorage.removeItem(ACTIVE_ROLE_KEY);
    }
    try {
      localStorage.removeItem(OFFICER_TOKEN_KEY);
      localStorage.removeItem(OFFICER_PROFILE_KEY);
    } catch {
      // Ignore
    }
    router.push("/officer/login");
  }, [role, router]);

  // General Logout
  const logout = useCallback(() => {
    if (role === "CITIZEN") {
      logoutCitizen();
      router.push("/");
    } else if (role === "OFFICER") {
      logoutOfficer();
    } else {
      logoutCitizen();
      logoutOfficer();
      router.push("/");
    }
  }, [role, logoutCitizen, logoutOfficer, router]);

  const isSupervisor = officer?.role === "SUPERVISOR";
  const isAuthenticated = role === "CITIZEN" ? !!citizenToken : role === "OFFICER" ? !!officerToken : false;

  return (
    <AuthContext.Provider
      value={{
        role,
        isAuthenticated,
        isLoading,
        logout,
        citizen,
        citizenToken,
        loginCitizen,
        signupCitizen,
        logoutCitizen,
        officer,
        officerToken,
        isSupervisor,
        loginOfficer,
        logoutOfficer,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    return {
      role: null,
      isAuthenticated: false,
      isLoading: false,
      logout: () => {},
      citizen: null,
      citizenToken: null,
      loginCitizen: async () => {
        throw new Error("useAuth must be used within an AuthProvider");
      },
      signupCitizen: async () => {
        throw new Error("useAuth must be used within an AuthProvider");
      },
      logoutCitizen: () => {},
      officer: null,
      officerToken: null,
      isSupervisor: false,
      loginOfficer: async () => {
        throw new Error("useAuth must be used within an AuthProvider");
      },
      logoutOfficer: () => {},
    };
  }
  return context;
}
