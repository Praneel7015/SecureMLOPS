import { SecurityEvent } from '../../api';
import { EventFieldProps } from './EventField';

const asString = (value: unknown) => {
  if (value === null || value === undefined || value === '') return undefined;
  return String(value);
};

const asNumber = (value: unknown, digits = 4) => {
  if (value === null || value === undefined || value === '') return undefined;
  const num = Number(value);
  if (!Number.isFinite(num)) return undefined;
  return String(Number(num.toFixed(digits)));
};

const asPercent = (value: unknown) => {
  if (value === null || value === undefined || value === '') return undefined;
  const num = Number(value);
  if (!Number.isFinite(num)) return undefined;
  const normalized = num <= 1 ? num * 100 : num;
  return `${normalized.toFixed(1)}%`;
};

const asTitle = (value: string) =>
  value
    .replace(/[._]/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());

export const getEventCategory = (eventType: string) => {
  const prefix = eventType.split('.')[0] || 'system';
  return asTitle(prefix);
};

export const getEventStatusSummary = (event: SecurityEvent) => {
  const meta = event.metadata || {};
  return (
    asString(meta.status) ||
    asString(meta.decision_reason) ||
    asString(meta.verdict) ||
    event.description ||
    'Event recorded'
  );
};

const pick = (meta: Record<string, unknown>, keys: string[]) =>
  keys.map((key) => meta[key]).find((value) => value !== undefined && value !== null && value !== '');

const field = (
  label: string,
  value: unknown,
  options?: Partial<EventFieldProps>,
): EventFieldProps | null => {
  const formatted =
    typeof value === 'number'
      ? asNumber(value)
      : typeof value === 'boolean'
        ? value
          ? 'Yes'
          : 'No'
        : asString(value);
  if (!formatted) return null;
  return { label, value: formatted, ...options };
};

const buildDriftFields = (meta: Record<string, unknown>): EventFieldProps[] => {
  return [
    field('Drift Score', pick(meta, ['drift_score', 'score']), { variant: 'metric', highlight: true }),
    field('Severity', pick(meta, ['severity', 'drift_severity']), { variant: 'badge' }),
    field('Distance', pick(meta, ['distance', 'drift_distance']), { variant: 'metric' }),
    field('Model', pick(meta, ['model_name', 'model_type'])),
    field('Model Type', meta.model_type),
    field('Reference Baseline', pick(meta, ['reference', 'drift_reference'])),
    field('Status', pick(meta, ['status', 'drift_status'])),
    field('Filename', meta.filename, { variant: 'badge' }),
  ].filter(Boolean) as EventFieldProps[];
};

const buildInferenceFields = (meta: Record<string, unknown>): EventFieldProps[] => {
  return [
    field('Prediction', meta.prediction, { highlight: true }),
    field('Confidence', meta.confidence !== undefined ? asPercent(meta.confidence) : undefined, {
      variant: 'metric',
    }),
    field('Risk Score', pick(meta, ['risk_score', 'risk_level']), { variant: 'metric', highlight: true }),
    field('Decision', pick(meta, ['verdict', 'status']), { variant: 'badge' }),
    field('Model Used', pick(meta, ['model_name', 'model_type'])),
    field('Model Source', meta.model_source, { variant: 'badge' }),
    field('Risk Level', meta.risk_level, { variant: 'badge' }),
    field('Drift Score', meta.drift_score, { variant: 'metric' }),
    field('Session ID', meta.session_id, { variant: 'badge' }),
    field('Filename', meta.filename),
  ].filter(Boolean) as EventFieldProps[];
};

const buildTrainingFields = (meta: Record<string, unknown>): EventFieldProps[] => {
  return [
    field('Model Architecture', pick(meta, ['model_type', 'model_name']), { highlight: true }),
    field('Dataset', pick(meta, ['dataset_id', 'source_name'])),
    field('Accuracy', pick(meta, ['validation_accuracy', 'final_val_accuracy']), {
      variant: 'metric',
      highlight: true,
    }),
    field('Epochs', meta.epochs, { variant: 'metric' }),
    field('Status', meta.status, { variant: 'badge' }),
    field('Duration', meta.total_duration_sec ? `${meta.total_duration_sec}s` : undefined),
    field('Job ID', meta.job_id, { variant: 'badge' }),
    field('Model ID', meta.model_id, { variant: 'badge' }),
    field('Image Count', meta.image_count, { variant: 'metric' }),
  ].filter(Boolean) as EventFieldProps[];
};

const buildIntegrityFields = (meta: Record<string, unknown>, event: SecurityEvent): EventFieldProps[] => {
  const details = Array.isArray(meta.details) ? meta.details.join(', ') : asString(meta.details);
  return [
    field('Checkpoint', pick(meta, ['checkpoint_filename', 'checkpoint_name', 'model_name'])),
    field('Validation Status', event.event_type.includes('success') ? 'Passed' : 'Failed', {
      variant: 'badge',
      highlight: true,
    }),
    field('Architecture Match', meta.architecture_match ?? (event.event_type.includes('mismatch') ? 'No' : undefined), {
      variant: 'badge',
    }),
    field('Failure Reason', pick(meta, ['failure_reason', 'reason']) || event.description),
    field('Reconstruction Status', meta.reconstruction_status, { variant: 'badge' }),
    field('Affected Files', details),
  ].filter(Boolean) as EventFieldProps[];
};

const buildAdversarialFields = (meta: Record<string, unknown>, event: SecurityEvent): EventFieldProps[] => {
  return [
    field('Attack Detected', meta.adversarial ?? true, { variant: 'badge', highlight: true }),
    field('Detector Confidence', pick(meta, ['confidence', 'attack_confidence']), { variant: 'metric' }),
    field('Risk Escalation', pick(meta, ['risk_level', 'risk_score']), { variant: 'metric', highlight: true }),
    field('Final Decision', pick(meta, ['verdict', 'status']) || event.description, { variant: 'badge' }),
    field('Model', pick(meta, ['model_name', 'model_type'])),
    field('Prediction', meta.prediction),
  ].filter(Boolean) as EventFieldProps[];
};

const buildValidationFields = (meta: Record<string, unknown>, event: SecurityEvent): EventFieldProps[] => {
  const issues = Array.isArray(meta.issues) ? meta.issues.join('; ') : asString(meta.issues);
  return [
    field('Validation Result', event.event_type.includes('failed') ? 'Failed' : 'Warning', {
      variant: 'badge',
      highlight: true,
    }),
    field('Filename', pick(meta, ['filename', 'source_name'])),
    field('Issue Details', issues || event.description),
    field('Dataset ID', meta.dataset_id, { variant: 'badge' }),
  ].filter(Boolean) as EventFieldProps[];
};

const buildSystemFields = (meta: Record<string, unknown>, event: SecurityEvent): EventFieldProps[] => {
  return [
    field('Component', event.source, { variant: 'badge' }),
    field('Failure Type', asTitle(event.event_type.split('.')[1] || 'unknown'), { variant: 'badge' }),
    field('Details', event.description, { highlight: true }),
    field('Model', pick(meta, ['model_name', 'model_type'])),
    field('Original Event', meta.original_event_type, { variant: 'badge' }),
  ].filter(Boolean) as EventFieldProps[];
};

const GENERIC_KEYS: Array<[string, string]> = [
  ['model_name', 'Model'],
  ['model_type', 'Model Type'],
  ['job_id', 'Job ID'],
  ['dataset_id', 'Dataset ID'],
  ['session_id', 'Session ID'],
  ['filename', 'Filename'],
  ['owner', 'Owner'],
];

const buildGenericFields = (meta: Record<string, unknown>, usedLabels: Set<string>): EventFieldProps[] => {
  const fields: EventFieldProps[] = [];
  for (const [key, label] of GENERIC_KEYS) {
    if (usedLabels.has(label)) continue;
    const entry = field(label, meta[key], key.includes('id') ? { variant: 'badge' } : undefined);
    if (entry) {
      fields.push(entry);
      usedLabels.add(label);
    }
  }
  return fields;
};

export const getEventMetadataFields = (event: SecurityEvent): EventFieldProps[] => {
  const meta = event.metadata || {};
  const type = event.event_type || '';

  let fields: EventFieldProps[] = [];
  if (type.startsWith('drift.')) fields = buildDriftFields(meta);
  else if (type.startsWith('inference.')) fields = buildInferenceFields(meta);
  else if (type.startsWith('training.')) fields = buildTrainingFields(meta);
  else if (type.startsWith('integrity.')) fields = buildIntegrityFields(meta, event);
  else if (type.startsWith('adversarial.')) fields = buildAdversarialFields(meta, event);
  else if (type.startsWith('validation.')) fields = buildValidationFields(meta, event);
  else if (type.startsWith('system.')) fields = buildSystemFields(meta, event);
  else fields = buildGenericFields(meta, new Set());

  const usedLabels = new Set(fields.map((item) => item.label));
  fields = [...fields, ...buildGenericFields(meta, usedLabels)];

  // Deduplicate by label
  const seen = new Set<string>();
  return fields.filter((item) => {
    if (seen.has(item.label)) return false;
    seen.add(item.label);
    return true;
  });
};

export const formatEventTimestamp = (value?: string) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};
