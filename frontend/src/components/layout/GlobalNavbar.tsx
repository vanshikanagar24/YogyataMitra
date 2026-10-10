"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  LayoutGrid,
  ClipboardCheck,
  ShieldCheck,
  History,
  User,
  Menu,
  X,
  Shield,
  LogOut,
  ChevronDown,
  LayoutDashboard,
  ClipboardList,
  Sparkles,
  FileCode2,
} from "lucide-react";
import { useLanguage } from "../../context/LanguageContext";
import { useAuth } from "../../context/AuthContext";

export const GlobalNavbar: React.FC = () => {
  const pathname = usePathname();
  const { language, setLanguage, isHindi, t } = useLanguage();
  const { role, citizen, officer, isAuthenticated, logoutCitizen, logoutOfficer } = useAuth();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close menus on route change
  useEffect(() => {
    setMobileMenuOpen(false);
    setProfileDropdownOpen(false);
  }, [pathname]);


  // Handle outside click to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setProfileDropdownOpen(false);
      }
    };
    if (profileDropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [profileDropdownOpen]);

  // Handle Escape key to close menus
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (profileDropdownOpen) setProfileDropdownOpen(false);
        if (mobileMenuOpen) setMobileMenuOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [profileDropdownOpen, mobileMenuOpen]);

  if (pathname?.startsWith("/officer")) {
    return null;
  }

  const navItems = [
    {
      href: "/",
      labelKey: "nav.home",
      icon: Home,
    },
    {
      href: "/schemes",
      labelKey: "nav.schemes",
      icon: LayoutGrid,
    },
    {
      href: "/eligibility",
      labelKey: "nav.eligibility",
      icon: ClipboardCheck,
    },
    {
      href: "/policy-verification",
      labelKey: "nav.policy_verification",
      icon: ShieldCheck,
    },
    {
      href: "/audit-history",
      labelKey: "nav.audit_history",
      icon: History,
    },
  ];

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <header className="bg-white border-b border-gov-border sticky top-0 z-50 shadow-sm" role="banner">
      {/* National Tricolor Top Accent */}
      <div
        className="h-1 bg-gradient-to-r from-[#FF9933] via-white to-[#138808]"
        role="presentation"
        aria-hidden="true"
      />

      <div className="gov-container">
        <div className="flex items-center justify-between h-20">
          {/* Brand Identity */}
          <Link
            href="/"
            className="flex items-center space-x-2 sm:space-x-3.5 min-w-0 group focus-visible:ring-2 focus-visible:ring-primary rounded-md p-1"
            aria-label={`${t("brand.title")} — ${t("brand.subtitle")}`}
          >
            <div className="relative w-11 h-11 flex items-center justify-center flex-shrink-0">
              <img
                src="/images/logo.png"
                alt="YM Logo - YogyataMitra"
                className="w-11 h-11 object-contain"
              />
              <span className="sr-only">YM</span>
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-lg sm:text-xl font-extrabold text-primary-dark tracking-tight truncate">
                {isHindi ? "योग्यता मित्र" : "YogyataMitra"}
              </span>
              <span className="text-xs text-gov-secondary font-normal tracking-tight hidden sm:inline line-clamp-1">
                {t("brand.subtitle")}
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden lg:flex items-center space-x-1.5" aria-label={isHindi ? "मुख्य नेविगेशन" : "Main Navigation"}>
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-md text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-primary ${
                    active
                      ? "bg-primary-50 text-primary font-semibold border border-primary-100"
                      : "text-gov-secondary hover:text-gov-text hover:bg-gray-50"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${active ? "text-primary" : "text-gov-secondary"}`} aria-hidden="true" />
                  <span>{t(item.labelKey)}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Action Area */}
          <div className="flex items-center space-x-1.5 sm:space-x-3 flex-shrink-0">
            {/* Language Switcher */}
            <div
              className="bg-gray-100 p-0.5 rounded-md flex items-center border border-gov-border text-xs font-semibold"
              role="group"
              aria-label={t("a11y.language_switcher")}
            >
              <button
                type="button"
                onClick={() => setLanguage("en")}
                aria-pressed={language === "en"}
                className={`px-1.5 sm:px-2.5 py-1 rounded transition-all min-h-[32px] ${
                  language === "en"
                    ? "bg-primary-dark text-white shadow-xs"
                    : "text-gov-secondary hover:text-gov-text"
                }`}
                aria-label="Switch to English / अंग्रेज़ी में बदलें"
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLanguage("hi")}
                aria-pressed={language === "hi"}
                className={`px-1.5 sm:px-2.5 py-1 rounded transition-all min-h-[32px] ${
                  language === "hi"
                    ? "bg-primary-dark text-white shadow-xs"
                    : "text-gov-secondary hover:text-gov-text"
                }`}
                aria-label="Switch to Hindi / हिंदी में बदलें"
              >
                हिंदी
              </button>
            </div>

            {/* Profile Dropdown Popover */}
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
                aria-expanded={profileDropdownOpen}
                aria-haspopup="true"
                aria-label="उपयोगकर्ता प्रोफ़ाइल और पोर्टल भूमिका / User Profile and Portal Role"
                className={`flex items-center space-x-2 p-1 sm:px-2.5 sm:py-1.5 rounded-full sm:rounded-lg border transition-all focus-visible:ring-2 focus-visible:ring-primary ${
                  profileDropdownOpen
                    ? "border-primary bg-primary-50 text-primary shadow-sm"
                    : "border-gov-border hover:border-gray-300 bg-gray-50 text-gov-secondary hover:text-gov-text"
                }`}
              >
                <div className="w-8 h-8 rounded-full bg-white border border-gov-border flex items-center justify-center text-primary relative">
                  {role === "OFFICER" ? (
                    <Shield className="w-4 h-4 text-blue-700" aria-hidden="true" />
                  ) : role === "CITIZEN" ? (
                    <User className="w-4 h-4 text-emerald-700" aria-hidden="true" />
                  ) : (
                    <User className="w-4 h-4 text-gov-secondary" aria-hidden="true" />
                  )}
                  {isAuthenticated && (
                    <span
                      className={`absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-white ${
                        role === "CITIZEN" ? "bg-emerald-500" : "bg-blue-600"
                      }`}
                      aria-hidden="true"
                    />
                  )}
                </div>

                <div className="hidden md:flex flex-col text-left">
                  <span className="text-xs font-bold text-gov-text leading-tight truncate max-w-[120px]">
                    {role === "CITIZEN"
                      ? citizen?.citizen_name?.split(" ")[0] || "नागरिक"
                      : role === "OFFICER"
                      ? officer?.name?.split(" ")[0] || "अधिकारी"
                      : "पोर्टल लॉगिन"}
                  </span>
                  <span className="text-[10px] text-gov-secondary leading-none">
                    {role === "CITIZEN"
                      ? "नागरिक / Citizen"
                      : role === "OFFICER"
                      ? "अधिकारी / Officer"
                      : "भूमिका चुनें / Choose Role"}
                  </span>
                </div>

                <ChevronDown className={`w-3.5 h-3.5 text-gov-secondary transition-transform hidden sm:block ${profileDropdownOpen ? "rotate-180" : ""}`} />
              </button>

              {/* Popover Card */}
              {profileDropdownOpen && (
                <div
                  className="absolute right-0 mt-2 w-80 bg-white border border-gov-border rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2"
                  role="menu"
                >
                  <div
                    className="h-1 bg-gradient-to-r from-[#FF9933] via-white to-[#138808]"
                    role="presentation"
                    aria-hidden="true"
                  />

                  {/* 1. CITIZEN AUTHENTICATED */}
                  {isAuthenticated && role === "CITIZEN" && (
                    <div className="p-4 space-y-3">
                      <div className="flex items-center space-x-3 pb-3 border-b border-gov-border">
                        <div className="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700">
                          <User className="w-5 h-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between">
                            <h3 className="text-xs font-bold text-gov-text truncate">
                              {citizen?.citizen_name}
                            </h3>
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                              नागरिक
                            </span>
                          </div>
                          <p className="text-[11px] font-mono text-primary font-medium truncate">
                            {citizen?.citizen_ref}
                          </p>
                          <p className="text-[11px] text-gov-secondary truncate">
                            {citizen?.email}
                          </p>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <Link
                          href="/citizen/dashboard"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-semibold text-gov-text hover:bg-primary-50 hover:text-primary transition-colors"
                        >
                          <LayoutDashboard className="w-4 h-4 text-gov-secondary" />
                          <span>नागरिक डैशबोर्ड / Dashboard</span>
                        </Link>
                        <Link
                          href="/citizen/applications"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-semibold text-gov-text hover:bg-primary-50 hover:text-primary transition-colors"
                        >
                          <ClipboardList className="w-4 h-4 text-gov-secondary" />
                          <span>मेरे आवेदन / My Applications</span>
                        </Link>
                        <Link
                          href="/citizen/profile"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-semibold text-gov-text hover:bg-primary-50 hover:text-primary transition-colors"
                        >
                          <User className="w-4 h-4 text-gov-secondary" />
                          <span>मेरी प्रोफ़ाइल / My Profile</span>
                        </Link>
                      </div>

                      <div className="pt-2 border-t border-gov-border">
                        <button
                          type="button"
                          onClick={() => {
                            logoutCitizen();
                            setProfileDropdownOpen(false);
                          }}
                          className="w-full flex items-center space-x-2 px-3 py-2 rounded-md text-xs font-semibold text-red-600 hover:bg-red-50 transition-colors"
                        >
                          <LogOut className="w-4 h-4" />
                          <span>लॉगआउट / Sign Out</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* 2. OFFICER AUTHENTICATED */}
                  {isAuthenticated && role === "OFFICER" && (
                    <div className="p-4 space-y-3">
                      <div className="flex items-center space-x-3 pb-3 border-b border-gov-border">
                        <div className="w-10 h-10 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700">
                          <Shield className="w-5 h-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between">
                            <h3 className="text-xs font-bold text-gov-text truncate">
                              {officer?.name}
                            </h3>
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-800">
                              {officer?.role}
                            </span>
                          </div>
                          <p className="text-[11px] text-gov-secondary truncate">
                            {officer?.designation}
                          </p>
                          <p className="text-[10px] text-gov-secondary truncate">
                            {officer?.department}
                          </p>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <Link
                          href="/officer/queue"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-semibold text-gov-text hover:bg-primary-50 hover:text-primary transition-colors"
                        >
                          <ShieldCheck className="w-4 h-4 text-gov-secondary" />
                          <span>सत्यापन कतार / Verification Queue</span>
                        </Link>
                        <Link
                          href="/officer/policy-discovery"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-semibold text-gov-text hover:bg-primary-50 hover:text-primary transition-colors"
                        >
                          <Sparkles className="w-4 h-4 text-gov-secondary" />
                          <span>नीति खोज / Policy Discovery</span>
                        </Link>
                        <Link
                          href="/officer/policy-authoring"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-center space-x-2.5 px-3 py-2 rounded-md text-xs font-semibold text-gov-text hover:bg-primary-50 hover:text-primary transition-colors"
                        >
                          <FileCode2 className="w-4 h-4 text-gov-secondary" />
                          <span>नीति निर्माण / Policy Authoring</span>
                        </Link>
                      </div>

                      <div className="pt-2 border-t border-gov-border">
                        <button
                          type="button"
                          onClick={() => {
                            logoutOfficer();
                            setProfileDropdownOpen(false);
                          }}
                          className="w-full flex items-center space-x-2 px-3 py-2 rounded-md text-xs font-semibold text-red-600 hover:bg-red-50 transition-colors"
                        >
                          <LogOut className="w-4 h-4" />
                          <span>लॉगआउट / Sign Out</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* 3. GUEST / ROLE SELECTION */}
                  {!isAuthenticated && (
                    <div className="p-4 space-y-3">
                      <div className="pb-2 border-b border-gov-border">
                        <h3 className="text-xs font-bold text-gov-text">
                          पोर्टल भूमिका चुनें / Select Portal Role
                        </h3>
                        <p className="text-[11px] text-gov-secondary mt-0.5">
                          अपनी आवश्यकतानुसार उपयुक्त पोर्टल में प्रवेश करें
                        </p>
                      </div>

                      <div className="space-y-2">
                        {/* Option 1: Citizen */}
                        <Link
                          href="/citizen/login"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-start space-x-3 p-3 rounded-lg border border-gov-border hover:border-primary-300 hover:bg-primary-50/50 transition-all group"
                        >
                          <div className="w-8 h-8 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 flex-shrink-0 mt-0.5 group-hover:scale-105 transition-transform">
                            <User className="w-4 h-4" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-gov-text group-hover:text-primary">
                                Citizen / नागरिक
                              </span>
                              <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                                लाभार्थी
                              </span>
                            </div>
                            <p className="text-[11px] text-gov-secondary mt-0.5 leading-snug">
                              Apply for schemes, track applications, verify eligibility
                            </p>
                          </div>
                        </Link>

                        {/* Option 2: Officer */}
                        <Link
                          href="/officer/login"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-start space-x-3 p-3 rounded-lg border border-gov-border hover:border-blue-300 hover:bg-blue-50/50 transition-all group"
                        >
                          <div className="w-8 h-8 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700 flex-shrink-0 mt-0.5 group-hover:scale-105 transition-transform">
                            <Shield className="w-4 h-4" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-gov-text group-hover:text-blue-700">
                                Officer / अधिकारी
                              </span>
                              <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
                                सत्यापनकर्ता
                              </span>
                            </div>
                            <p className="text-[11px] text-gov-secondary mt-0.5 leading-snug">
                              Verification queue, review evidence, policy discovery & authoring
                            </p>
                          </div>
                        </Link>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Mobile Hamburger Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2.5 rounded-md text-gov-secondary hover:text-gov-text hover:bg-gray-100 min-w-[44px] min-h-[44px] flex items-center justify-center focus-visible:ring-2 focus-visible:ring-primary"
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-navigation"
              aria-label={t("a11y.toggle_menu")}
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6" aria-hidden="true" />
              ) : (
                <Menu className="w-6 h-6" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div
          id="mobile-navigation"
          role="navigation"
          aria-label={isHindi ? "मोबाइल नेविगेशन" : "Mobile Navigation"}
          className="lg:hidden border-t border-gov-border bg-white px-4 pt-2 pb-4 space-y-2 shadow-lg animate-in slide-in-from-top-2"
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                aria-current={active ? "page" : undefined}
                className={`flex items-center space-x-2.5 px-3 py-3 rounded-md text-sm font-medium min-h-[44px] ${
                  active
                    ? "bg-primary-50 text-primary font-semibold"
                    : "text-gov-secondary hover:text-gov-text hover:bg-gray-50"
                }`}
              >
                <Icon className="w-4 h-4" aria-hidden="true" />
                <span>{t(item.labelKey)}</span>
              </Link>
            );
          })}

          {/* Mobile Role Selection / Status */}
          <div className="pt-3 mt-2 border-t border-gov-border space-y-1">
            <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-gov-secondary">
              पोर्टल भूमिका / Portal Access
            </p>
            {isAuthenticated ? (
              <div className="px-3 py-2 bg-gray-50 rounded-md">
                <div className="flex items-center justify-between text-xs font-bold text-gov-text">
                  <span>{role === "CITIZEN" ? citizen?.citizen_name : officer?.name}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary-100 text-primary font-semibold">
                    {role === "CITIZEN" ? "नागरिक" : "अधिकारी"}
                  </span>
                </div>
                <div className="mt-2 flex gap-2">
                  <Link
                    href={role === "CITIZEN" ? "/citizen/dashboard" : "/officer/queue"}
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex-1 py-1.5 text-center text-xs font-semibold bg-primary text-white rounded"
                  >
                    डैशबोर्ड / Portal
                  </Link>
                  <button
                    type="button"
                    onClick={() => {
                      if (role === "CITIZEN") logoutCitizen();
                      else logoutOfficer();
                      setMobileMenuOpen(false);
                    }}
                    className="px-3 py-1.5 text-xs font-semibold text-red-600 bg-red-50 rounded border border-red-200"
                  >
                    लॉगआउट
                  </button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <Link
                  href="/citizen/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-md text-xs font-semibold text-center border border-gov-border bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
                >
                  नागरिक लॉगिन
                </Link>
                <Link
                  href="/officer/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-md text-xs font-semibold text-center border border-gov-border bg-blue-50 text-blue-800 hover:bg-blue-100"
                >
                  अधिकारी लॉगिन
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
