/**
 * Open-Redirect Defense-in-Depth Utilities.
 *
 * Validates that a redirect target is strictly a safe internal application path:
 * - Starts with exactly "/"
 * - Does NOT start with "//" or "/\"
 * - Does NOT use an absolute URL or protocol schemes (http:, https:, javascript:, data:, etc.)
 * - Does NOT escape the application origin
 */

export function isSafeInternalRedirect(target: string | null | undefined): boolean {
  if (!target || typeof target !== "string") {
    return false;
  }
  const trimmed = target.trim();
  // Must start with exactly "/" and not "//" or "/\"
  if (!trimmed.startsWith("/") || trimmed.startsWith("//") || trimmed.startsWith("/\\")) {
    return false;
  }
  // Check that path part before query/hash does not contain protocol schemes (e.g., http:, javascript:) or backslashes
  const pathPart = trimmed.split("?")[0].split("#")[0];
  if (pathPart.includes(":") || pathPart.includes("\\")) {
    return false;
  }
  return true;
}

export function getSafeRedirectUrl(
  target: string | null | undefined,
  fallback = "/citizen/dashboard"
): string {
  return isSafeInternalRedirect(target) ? (target as string).trim() : fallback;
}
