"use client";

import React, { useState, useEffect } from "react";
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
} from "lucide-react";
import { useLanguage } from "../../context/LanguageContext";

export const GlobalNavbar: React.FC = () => {
  const pathname = usePathname();
  const { language, setLanguage, isHindi, t } = useLanguage();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  if (pathname?.startsWith("/officer")) {
    return null;
  }

  // Handle Escape key to close mobile menu
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && mobileMenuOpen) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileMenuOpen]);

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
            className="flex items-center space-x-3.5 group focus-visible:ring-2 focus-visible:ring-primary rounded-md p-1"
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
            <div className="flex flex-col">
              <span className="text-xl font-extrabold text-primary-dark tracking-tight">
                {isHindi ? "योग्यता मित्र" : "YogyataMitra"}
              </span>
              <span className="text-xs text-gov-secondary font-normal tracking-tight line-clamp-1">
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
          <div className="flex items-center space-x-3">
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
                className={`px-2.5 py-1 rounded transition-all min-h-[32px] ${
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
                className={`px-2.5 py-1 rounded transition-all min-h-[32px] ${
                  language === "hi"
                    ? "bg-primary-dark text-white shadow-xs"
                    : "text-gov-secondary hover:text-gov-text"
                }`}
                aria-label="Switch to Hindi / हिंदी में बदलें"
              >
                हिंदी
              </button>
            </div>

            {/* Profile Avatar (Visual/Civic Status Icon) */}
            <div
              className="relative group hidden sm:block"
              title={t("nav.profile_label")}
            >
              <div
                className="w-9 h-9 rounded-full border border-gov-border flex items-center justify-center text-gov-secondary bg-gray-50"
                aria-label={t("nav.profile_label")}
                role="img"
              >
                <User className="w-4 h-4" aria-hidden="true" />
              </div>
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
          className="lg:hidden border-t border-gov-border bg-white px-4 pt-2 pb-4 space-y-1 shadow-lg animate-in slide-in-from-top-2"
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
        </div>
      )}
    </header>
  );
};
