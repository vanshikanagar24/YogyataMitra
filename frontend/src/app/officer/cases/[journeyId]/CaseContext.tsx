"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { OfficerCaseDetail } from "@/types/officer";
import { officerApi } from "@/api/officer";
import { useOfficerAuth } from "@/context/OfficerAuthContext";

interface CaseContextType {
  caseData: OfficerCaseDetail | null;
  loading: boolean;
  error: string | null;
  reloadCase: () => Promise<void>;
  journeyId: string;
}

const CaseContext = createContext<CaseContextType | undefined>(undefined);

export function CaseProvider({
  journeyId,
  children,
}: {
  journeyId: string;
  children: React.ReactNode;
}) {
  const { token, isAuthenticated } = useOfficerAuth();
  const [caseData, setCaseData] = useState<OfficerCaseDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const reloadCase = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await officerApi.getCaseDetail(journeyId, token);
      setCaseData(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load case dossier details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && token && journeyId) {
      reloadCase();
    }
  }, [isAuthenticated, token, journeyId]);

  return (
    <CaseContext.Provider
      value={{
        caseData,
        loading,
        error,
        reloadCase,
        journeyId,
      }}
    >
      {children}
    </CaseContext.Provider>
  );
}

export function useCase() {
  const context = useContext(CaseContext);
  if (!context) {
    throw new Error("useCase must be used within a CaseProvider");
  }
  return context;
}
