"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import i18n from "../i18n";

interface LanguageContextType {
  language: string;
  setLanguage: (lang: string) => void;
  isHindi: boolean;
  t: (key: string, options?: Record<string, unknown>) => string;
}

const LanguageContext = createContext<LanguageContextType>({
  language: "hi",
  setLanguage: () => {},
  isHindi: true,
  t: (k) => k,
});

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLangState] = useState<string>("hi");

  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem("ym_lang") : null;
    if (saved && (saved === "en" || saved === "hi")) {
      setLangState(saved);
      i18n.changeLanguage(saved);
    }
  }, []);

  const setLanguage = (lang: string) => {
    setLangState(lang);
    if (typeof window !== "undefined") {
      localStorage.setItem("ym_lang", lang);
    }
    i18n.changeLanguage(lang);
  };

  const t = (key: string, options?: Record<string, unknown>): string => {
    return i18n.t(key, options) as string;
  };

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage,
        isHindi: language === "hi",
        t,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
