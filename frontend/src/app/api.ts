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
