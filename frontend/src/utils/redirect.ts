/**
 * Security utility to validate internal redirect destinations.
 * Prevents open redirect vulnerabilities by rejecting external or protocol-relative URLs.
 */

export function getSafeRedirectUrl(target: unknown, fallback = "/"): string {
  if (typeof target !== "string" || !target.trim()) {
    return fallback;
  }

  const trimmed = target.trim();

  // Must begin with a single slash and must NOT begin with double slashes (protocol-relative)
  if (!trimmed.startsWith("/") || trimmed.startsWith("//")) {
    return fallback;
  }

  // Reject URLs containing protocol schemes like javascript: or https:
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(trimmed)) {
    return fallback;
  }

  // Reject control characters or whitespace within path
  if (/[\r\n\t]/.test(trimmed)) {
    return fallback;
  }

  return trimmed;
}
