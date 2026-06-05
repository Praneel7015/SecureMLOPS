export type SampleImage = {
  name: string;
  url: string;
};

export type SupportedModel = {
  id: string;
  label: string;
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
  model_type?: string;
  model_source?: string;
  model_name?: string;
  checkpoint_loaded?: boolean;
  class_names?: string[];
  num_classes?: number;
  model_created_at?: string;
  reconstruction_status?: string;
  prediction?: string | null;
  confidence?: number | null;
  verdict?: string;
  anomaly?: boolean;
  adversarial?: boolean;
  issues?: string[];
  drift_score?: number | null;
  drift_severity?: string;
  drift_status?: string;
  drift_distance?: number | null;
  drift_reference?: string | null;
  drift_projection?: [number, number] | null;
  filename?: string;
  audit_log?: AuditEntry[];
  pipeline_steps?: PipelineStep[];
};

export type DriftEvent = {
  timestamp: string;
  score: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  status: string;
  distance?: number | null;
  reference?: string | null;
  model_name?: string;
  model_type?: string;
  projection_x?: number | null;
  projection_y?: number | null;
  filename?: string;
};

export type DriftSummary = {
  total: number;
  avg_score: number;
  severity_counts: Record<'LOW' | 'MEDIUM' | 'HIGH', number>;
  latest?: DriftEvent | null;
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
    display_name?: string | null;
    email?: string | null;
    sample_images: SampleImage[];
    max_upload_size_mb: number;
    max_dataset_upload_mb: number;
    max_model_upload_mb: number;
    supported_models: SupportedModel[];
  };
}

export type DatasetSummary = {
  dataset_id: string;
  class_names: string[];
  image_count: number;
  class_distribution?: Record<string, number>;
  source_name?: string;
  created_at?: string;
};

export type TrainingJob = {
  job_id: string;
  dataset_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at?: string;
  updated_at?: string;
  epochs?: number;
  current_epoch?: number;
  progress?: number;
  metrics?: {
    train_loss?: number[];
    val_loss?: number[];
    train_accuracy?: number[];
    val_accuracy?: number[];
    precision?: number[];
    recall?: number[];
    f1?: number[];
    epoch_durations?: number[];
    confusion_matrix?: number[][];
    per_class_accuracy?: Record<string, number>;
    class_names?: string[];
    final_val_accuracy?: number;
    final_train_loss?: number;
    final_val_loss?: number;
    final_train_accuracy?: number;
    final_precision?: number;
    final_recall?: number;
    final_f1?: number;
    total_duration_sec?: number;
  };
  logs?: Array<{ timestamp: string; message: string }>;
  error?: string | null;
  model_id?: string | null;
  config?: Record<string, unknown>;
};

export type TrainingModel = {
  model_id: string;
  model_type: string;
  model_label?: string;
  class_names: string[];
  metrics?: Record<string, unknown>;
  created_at?: string;
  file_name?: string;
};

export type SecurityEvent = {
  id: string;
  timestamp: string;
  severity: 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL' | string;
  event_type: string;
  source: string;
  title: string;
  description: string;
  metadata?: Record<string, unknown>;
};

export type DashboardMetrics = {
  total_inferences: number;
  high_risk_events: number;
  drift_alerts: number;
  models_registered: number;
  active_training_jobs: number;
  last_training_accuracy?: number | null;
  average_drift_score: number;
  severity_counts: Record<string, number>;
  total_events: number;
};

export type DashboardTrainingJob = {
  job_id: string;
  dataset_id?: string;
  status?: string;
  model_type?: string;
  epochs?: number;
  current_epoch?: number;
  validation_accuracy?: number | null;
  created_at?: string;
  updated_at?: string;
  model_id?: string | null;
};

export type DashboardModel = {
  model_id: string;
  model_type?: string;
  model_label?: string;
  class_names?: string[];
  num_classes?: number;
  created_at?: string;
  file_name?: string;
  inference_ready?: boolean;
  metrics?: Record<string, unknown>;
};

export type SystemStatus = {
  monitoring_status: string;
  drift_monitoring_status: string;
  security_engine_status: string;
  active_training_jobs: number;
  last_inference_at?: string | null;
  last_drift_event_at?: string | null;
  last_security_event_at?: string | null;
};

export type DashboardSummary = {
  metrics: DashboardMetrics;
  recent_training: DashboardTrainingJob[];
  recent_models: DashboardModel[];
  system_status: SystemStatus;
};

export type SecurityEventPagination = {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_more: boolean;
  has_new?: boolean;
};

export type SecurityEventFilters = {
  severity?: string;
  event_type?: string;
  source?: string;
  model?: string;
  category?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
  since_id?: string;
  order?: string;
};

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

export async function apiRegister(payload: {
  name: string;
  email: string;
  password: string;
}) {
  const response = await fetch('/register', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
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

export async function apiInference(formData: FormData) {
  const response = await fetch('/api/inference', {
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

export async function apiGetDriftTelemetry() {
  const response = await fetch('/api/monitoring/drift', {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });

  const data = (await response.json()) as ApiResponse<{
    events?: DriftEvent[];
    summary?: DriftSummary;
  }>;

  return {
    ok: response.ok,
    status: response.status,
    ...data,
  };
}

export async function apiUploadDataset(datasetFile: File) {
  const formData = new FormData();
  formData.append('dataset', datasetFile);

  const response = await fetch('/api/training/datasets', {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json' },
    body: formData,
  });

  const data = (await response.json()) as ApiResponse<{ dataset?: DatasetSummary }>;
  return { ok: response.ok, ...data };
}

export async function apiListDatasets() {
  const response = await fetch('/api/training/datasets', {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });

  const data = (await response.json()) as ApiResponse<{ datasets?: DatasetSummary[] }>;
  return { ok: response.ok, ...data };
}

export async function apiStartTraining(payload: {
  dataset_id: string;
  model_type: string;
  epochs: number;
  batch_size: number;
  learning_rate: number;
  freeze_backbone: boolean;
}) {
  const response = await fetch('/api/training/start', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = (await response.json()) as ApiResponse<{ job?: TrainingJob }>;
  return { ok: response.ok, ...data };
}

export async function apiListJobs() {
  const response = await fetch('/api/training/jobs', {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });

  const data = (await response.json()) as ApiResponse<{ jobs?: TrainingJob[] }>;
  return { ok: response.ok, ...data };
}

export async function apiGetJob(jobId: string) {
  const response = await fetch(`/api/training/jobs/${jobId}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });

  const data = (await response.json()) as ApiResponse<{ job?: TrainingJob }>;
  return { ok: response.ok, ...data };
}

export async function apiListModels() {
  const response = await fetch('/api/training/models', {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });

  const data = (await response.json()) as ApiResponse<{ models?: TrainingModel[] }>;
  return { ok: response.ok, ...data };
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

function buildQuery(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

export async function apiGetDashboardSummary() {
  const response = await fetch('/api/dashboard/summary', {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  const data = (await response.json()) as ApiResponse<{ summary?: DashboardSummary }>;
  return { ok: response.ok, status: response.status, ...data };
}

export async function apiGetDashboardActivity(limit = 20) {
  const response = await fetch(`/api/dashboard/activity${buildQuery({ limit })}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  const data = (await response.json()) as ApiResponse<{ activity?: SecurityEvent[] }>;
  return { ok: response.ok, status: response.status, ...data };
}

export async function apiGetDashboardSecuritySummary(limit = 10) {
  const response = await fetch(`/api/dashboard/security-summary${buildQuery({ limit })}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  const data = (await response.json()) as ApiResponse<{ events?: SecurityEvent[] }>;
  return { ok: response.ok, status: response.status, ...data };
}

export async function apiGetDashboardStatus() {
  const response = await fetch('/api/dashboard/status', {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  const data = (await response.json()) as ApiResponse<{ status?: SystemStatus }>;
  return { ok: response.ok, status: response.status, ...data };
}

export async function apiGetSecurityEvents(filters: SecurityEventFilters = {}) {
  const response = await fetch(`/api/security/events${buildQuery(filters)}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  const data = (await response.json()) as ApiResponse<{
    events?: SecurityEvent[];
    pagination?: SecurityEventPagination;
  }>;
  return { ok: response.ok, status: response.status, ...data };
}

export async function apiExportSecurityEvents(
  format: 'json' | 'csv',
  filters: SecurityEventFilters = {},
) {
  const response = await fetch(
    `/api/security/events/export${buildQuery({ ...filters, format })}`,
    {
      method: 'GET',
      credentials: 'include',
    },
  );
  if (!response.ok) {
    throw new Error('Export failed.');
  }
  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename=([^;]+)/);
  const filename = match?.[1]?.replace(/"/g, '') || `security_events.${format}`;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
