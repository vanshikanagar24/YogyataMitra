/**
 * YogyataMitra Authentication & Role Types (Phase A).
 *
 * Enforces strictly TWO user-facing product roles:
 * 1. CITIZEN
 * 2. OFFICER
 */

export type ProductRole = "CITIZEN" | "OFFICER";

export interface CitizenProfile {
  email: string;
  citizen_name: string;
  citizen_ref: string;
  role: "CITIZEN";
  state?: string | null;
  district?: string | null;
}

export interface CitizenAuthResponse {
  access_token: string;
  token_type: string;
  citizen_name: string;
  citizen_ref: string;
  email: string;
  role: "CITIZEN";
  state?: string | null;
  district?: string | null;
}

export interface CitizenSignupPayload {
  email: string;
  password: string;
  name: string;
  state?: string;
  district?: string;
}

export interface CitizenLoginPayload {
  identifier: string;
  password: string;
}

export interface AuthSession {
  role: ProductRole | null;
  token: string | null;
  citizenProfile: CitizenProfile | null;
  officerProfile: {
    email: string;
    name: string;
    role: string;
    designation: string;
    department: string;
  } | null;
  isAuthenticated: boolean;
}
