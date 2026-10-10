"use client";

import React, { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  User,
  Lock,
  Mail,
  MapPin,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Shield,
  Eye,
  EyeOff,
  Sparkles,
} from "lucide-react";
import { getSafeRedirectUrl } from "@/utils/redirects";

function CitizenLoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawRedirect = searchParams.get("redirect");
  const redirectUrl = getSafeRedirectUrl(rawRedirect, "/citizen/dashboard");

  const { loginCitizen, signupCitizen, isLoading: authLoading } = useAuth();

  const [mode, setMode] = useState<"login" | "signup">("login");
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Login fields
  const [identifier, setIdentifier] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Signup fields
  const [name, setName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [state, setState] = useState("Maharashtra");
  const [district, setDistrict] = useState("Pune");

  const fillDemoCredentials = () => {
    setMode("login");
    setIdentifier("citizen.test@yogyatamitra.local");
    setLoginPassword("Citizen@123");
    setErrorMsg(null);
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      await loginCitizen({
        identifier: identifier.trim(),
        password: loginPassword,
      });
      router.push(redirectUrl);
    } catch (err: any) {
      setErrorMsg(
        err?.message ||
          "लॉगिन विफल रहा। कृपया अपनी ईमेल/संदर्भ आईडी और पासवर्ड की जांच करें। / Login failed. Please check your credentials."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      await signupCitizen({
        email: signupEmail.trim(),
        password: signupPassword,
        name: name.trim(),
        state: state.trim(),
        district: district.trim(),
      });
      router.push(redirectUrl);
    } catch (err: any) {
      setErrorMsg(
        err?.message ||
          "पंजीकरण विफल रहा। कृपया विवरण पुनः जांचें। / Registration failed. Please check your input."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="gov-container py-12 max-w-xl mx-auto">
      {/* Tricolor Accent Header Card */}
      <div className="bg-white border border-gov-border rounded-xl shadow-sm overflow-hidden">
        <div
          className="h-1.5 bg-gradient-to-r from-[#FF9933] via-white to-[#138808]"
          role="presentation"
          aria-hidden="true"
        />

        <div className="p-6 sm:p-8">
          {/* Header Title */}
          <div className="text-center mb-6">
            <div className="inline-flex p-3 rounded-full bg-primary-50 text-primary mb-3">
              <User className="w-8 h-8" />
            </div>
            <h1 className="text-2xl font-extrabold text-gov-text">
              नागरिक सेवा पोर्टल / Citizen Services Portal
            </h1>
            <p className="text-xs text-gov-secondary mt-1">
              सरकारी योजनाओं के लिए पात्रता जांच, दावा आवेदन और स्थिति ट्रैकिंग
            </p>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="flex border-b border-gov-border mb-6">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setErrorMsg(null);
              }}
              className={`flex-1 pb-3 text-sm font-semibold text-center border-b-2 transition-colors ${
                mode === "login"
                  ? "border-primary text-primary"
                  : "border-transparent text-gov-secondary hover:text-gov-text"
              }`}
            >
              लॉगिन करें / Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("signup");
                setErrorMsg(null);
              }}
              className={`flex-1 pb-3 text-sm font-semibold text-center border-b-2 transition-colors ${
                mode === "signup"
                  ? "border-primary text-primary"
                  : "border-transparent text-gov-secondary hover:text-gov-text"
              }`}
            >
              नया पंजीकरण / Register
            </button>
          </div>

          {/* Error Notice */}
          {errorMsg && (
            <div
              className="mb-5 p-3.5 bg-red-50 border border-red-200 rounded-md flex items-start space-x-2.5 text-xs text-red-700"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Quick Fill Demo Banner */}
          {mode === "login" && (
            <div className="mb-6 p-3.5 bg-amber-50/80 border border-amber-200 rounded-lg flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-amber-900 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-700" />
                  डेमो नागरिक खाता / Quick Demo Account
                </p>
                <p className="text-[11px] text-amber-800">
                  citizen.test@yogyatamitra.local / Citizen@123
                </p>
              </div>
              <button
                type="button"
                onClick={fillDemoCredentials}
                className="px-2.5 py-1 text-xs font-medium bg-amber-100 hover:bg-amber-200 text-amber-900 border border-amber-300 rounded transition-colors"
              >
                स्वतः भरें / Auto Fill
              </button>
            </div>
          )}

          {/* LOGIN FORM */}
          {mode === "login" ? (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="citizen-identifier"
                  className="block text-xs font-semibold text-gov-text mb-1"
                >
                  ईमेल पता या सिंथेटिक संदर्भ संख्या / Email or Synthetic Reference ID
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gov-secondary">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    id="citizen-identifier"
                    type="text"
                    required
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="उदा. citizen.test@yogyatamitra.local या SYN-CIT-DEMO0001"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-gov-border rounded-md focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="citizen-password"
                  className="block text-xs font-semibold text-gov-text mb-1"
                >
                  पासवर्ड / Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gov-secondary">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    id="citizen-password"
                    type={showPassword ? "text" : "password"}
                    required
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-10 py-2 text-sm border border-gov-border rounded-md focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gov-secondary hover:text-gov-text"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || authLoading}
                className="w-full mt-2 gov-button-primary py-2.5 px-4 rounded-md text-sm font-semibold flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <span>
                  {isSubmitting ? "सत्यापित किया जा रहा है... / Verifying..." : "प्रवेश करें / Sign In"}
                </span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          ) : (
            /* SIGNUP FORM */
            <form onSubmit={handleSignupSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="signup-name"
                  className="block text-xs font-semibold text-gov-text mb-1"
                >
                  पूरा नाम / Full Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gov-secondary">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    id="signup-name"
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="उदा. रमेश कुमार / Ramesh Kumar"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-gov-border rounded-md focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="signup-email"
                  className="block text-xs font-semibold text-gov-text mb-1"
                >
                  ईमेल पता / Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gov-secondary">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    id="signup-email"
                    type="email"
                    required
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value)}
                    placeholder="name@example.com"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-gov-border rounded-md focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="signup-password"
                  className="block text-xs font-semibold text-gov-text mb-1"
                >
                  पासवर्ड बनाएं / Create Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gov-secondary">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    id="signup-password"
                    type={showPassword ? "text" : "password"}
                    required
                    minLength={6}
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    placeholder="कम से कम 6 वर्ण / At least 6 characters"
                    className="w-full pl-9 pr-10 py-2 text-sm border border-gov-border rounded-md focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gov-secondary hover:text-gov-text"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label
                    htmlFor="signup-state"
                    className="block text-xs font-semibold text-gov-text mb-1"
                  >
                    राज्य / State
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gov-secondary">
                      <MapPin className="w-4 h-4" />
                    </div>
                    <input
                      id="signup-state"
                      type="text"
                      required
                      value={state}
                      onChange={(e) => setState(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm border border-gov-border rounded-md focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="signup-district"
                    className="block text-xs font-semibold text-gov-text mb-1"
                  >
                    जिला / District
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gov-secondary">
                      <MapPin className="w-4 h-4" />
                    </div>
                    <input
                      id="signup-district"
                      type="text"
                      required
                      value={district}
                      onChange={(e) => setDistrict(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm border border-gov-border rounded-md focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-md text-[11px] text-blue-900 flex items-start space-x-2">
                <Shield className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                <span>
                  <strong>गोपनीयता सुरक्षा / Privacy Protection:</strong> वास्तविक आधार या पहचान विवरण संग्रहीत नहीं किए जाते हैं। प्रत्येक नागरिक को एक अद्वितीय सिंथेटिक संदर्भ आईडी सौंपी जाती है।
                </span>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || authLoading}
                className="w-full mt-2 gov-button-primary py-2.5 px-4 rounded-md text-sm font-semibold flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <span>
                  {isSubmitting ? "पंजीकरण किया जा रहा है... / Registering..." : "खाता बनाएं / Create Account"}
                </span>
                <CheckCircle2 className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* Footer Switching to Officer */}
          <div className="mt-8 pt-6 border-t border-gov-border text-center">
            <p className="text-xs text-gov-secondary mb-2">
              क्या आप सत्यापन अधिकारी हैं? / Are you a Government Verification Officer?
            </p>
            <Link
              href="/officer/login"
              className="inline-flex items-center space-x-1.5 text-xs font-semibold text-primary hover:underline"
            >
              <Shield className="w-3.5 h-3.5" />
              <span>अधिकारी सत्यापन पोर्टल पर जाएं / Go to Officer Portal</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CitizenLoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[50vh] flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <CitizenLoginContent />
    </Suspense>
  );
}
