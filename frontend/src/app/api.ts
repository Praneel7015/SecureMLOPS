export type SampleImage = {
  name: string;
  url: string;
};

export type PipelineStep = {
  id: string;
  number: string;
  title: string;
  label: string;
  body: string;
  badge: string;
  status: 'pass' | 'warn' | 'fail' | 'pending';
  details?: Array<{ label: string; value: string }>;
  top5?: Array<{ label: string; confidence: number }>;
};

export type AuditEntry = {
  stage: string;
  decision: 'pass' | 'warn' | 'fail';
  message: string;
};

export type AnalysisResult = {
  timestamp: string;
  username: string;
  status: 'allowed' | 'allowed_with_warning' | 'blocked';
  risk_level: string;
  decision_reason: string;
  prediction?: string | null;
  confidence?: number | null;
  verdict?: string;
  anomaly?: boolean;
  adversarial?: boolean;
  issues?: string[];
  filename?: string;
  audit_log?: AuditEntry[];
  pipeline_steps?: PipelineStep[];
};

type ApiResponse<T> = {
  success: boolean;
  message?: string;
} & T;

export async function apiBootstrap() {
  const response = await fetch('/api/bootstrap', {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error('Failed to load application bootstrap data.');
  }

  return (await response.json()) as {
    authenticated: boolean;
    username: string | null;
    sample_images: SampleImage[];
    max_upload_size_mb: number;
  };
}

export async function apiLogin(username: string, password: string) {
  const response = await fetch('/login', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ username, password }),
  });

  const data = (await response.json()) as ApiResponse<{ username?: string }>;
  return {
    success: response.ok && data.success,
    message: data.message,
    username: data.username,
  };
}

export async function apiLogout() {
  const response = await fetch('/logout', {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    throw new Error('Logout failed.');
  }

  return response.json();
}

export async function apiAnalyze(formData: FormData) {
  const response = await fetch('/analyze?format=json', {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
    body: formData,
  });

  const data = (await response.json()) as ApiResponse<{
    result?: AnalysisResult;
    sample_images?: SampleImage[];
    selected_image_url?: string | null;
    selected_sample?: string | null;
  }>;

  return {
    ok: response.ok,
    status: response.status,
    ...data,
  };
}

export async function apiCurrentUser() {
  const response = await fetch('/settings?format=json', {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    return null;
  }

  const data = (await response.json()) as { success: boolean; username?: string };
  return data.username ?? null;
}
