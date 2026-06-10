export type AppRole = 'admin' | 'workshop' | 'secretaria' | 'mecanico';

export const APP_SESSION_STORAGE_KEY = 'acb_session';

export type AppSession = {
  id: number;
  email: string;
  fullName: string;
  phone: string;
  role: AppRole;
  status: string;
  accessToken: string | null;
  tokenType: string | null;
};

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const [, encodedPayload] = token.split('.');

    if (!encodedPayload) {
      return null;
    }

    const base64 = encodedPayload.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
    const payloadText = atob(padded);
    const payload = JSON.parse(payloadText) as Record<string, unknown>;

    return payload;
  } catch {
    return null;
  }
}

function isTokenExpired(token: string | null): boolean {
  if (!isNonEmptyString(token)) {
    return true;
  }

  const payload = decodeJwtPayload(token);
  const exp = payload?.['exp'];

  if (typeof exp !== 'number') {
    return true;
  }

  return exp <= Math.floor(Date.now() / 1000);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function isAppRole(value: unknown): value is AppRole {
  return value === 'admin' || value === 'workshop' || value === 'secretaria' || value === 'mecanico';
}

export function parseStoredSession(raw: string | null): AppSession | null {
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<AppSession>;

    if (
      typeof parsed.id !== 'number' ||
      !isNonEmptyString(parsed.email) ||
      !isNonEmptyString(parsed.fullName) ||
      !isNonEmptyString(parsed.phone) ||
      !isAppRole(parsed.role) ||
      !isNonEmptyString(parsed.status)
    ) {
      return null;
    }

    const accessToken = parsed.accessToken ?? null;
    if (isTokenExpired(accessToken)) {
      return null;
    }

    return {
      id: parsed.id,
      email: parsed.email,
      fullName: parsed.fullName,
      phone: parsed.phone,
      role: parsed.role,
      status: parsed.status,
      accessToken,
      tokenType: parsed.tokenType ?? null,
    };
  } catch {
    return null;
  }
}

export function clearStoredSession(): void {
  window.localStorage.removeItem(APP_SESSION_STORAGE_KEY);
  window.sessionStorage.removeItem(APP_SESSION_STORAGE_KEY);
}

export function getStoredSession(): AppSession | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw =
    window.localStorage.getItem(APP_SESSION_STORAGE_KEY) ||
    window.sessionStorage.getItem(APP_SESSION_STORAGE_KEY);

  return parseStoredSession(raw);
}
