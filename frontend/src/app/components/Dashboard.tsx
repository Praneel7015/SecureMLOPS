import { Fragment, useEffect, useMemo, useState, useRef } from 'react';
import { Upload, Image as ImageIcon, CheckCircle2, XCircle, AlertCircle, ChevronDown, ChevronUp, Shield, Settings as SettingsIcon, LogOut, Menu, X, TrendingUp, FileCheck, Activity, Zap, Database, Lock, BarChart3, PlayCircle, Download, RefreshCw, History } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import {
  apiInference,
  apiUploadDataset,
  apiListDatasets,
  apiStartTraining,
  apiListJobs,
  apiGetJob,
  apiListModels,
  AnalysisResult,
  SampleImage,
  SupportedModel,
  DatasetSummary,
  TrainingJob,
  TrainingModel,
} from '../api';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from './ui/chart';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, XAxis, YAxis } from 'recharts';

interface DashboardProps {
  username: string;
  sampleImages: SampleImage[];
  supportedModels: SupportedModel[];
  maxDatasetUploadMb: number;
  maxModelUploadMb: number;
  onLogout: () => void | Promise<void>;
  onNavigateToSettings: () => void;
}

type PipelineStage = {
  id: number;
  name: string;
  status: 'pending' | 'running' | 'success' | 'warning' | 'error';
  message?: string;
  progress?: number;
  duration?: string;
};

type AuditEntry = {
  id: number;
  timestamp?: string;
  action: string;
  status: 'info' | 'success' | 'warning' | 'error';
  details?: string;
};

type MetricPoint = {
  epoch: number;
  trainLoss?: number | null;
  valLoss?: number | null;
  trainAccuracy?: number | null;
  valAccuracy?: number | null;
  precision?: number | null;
  recall?: number | null;
  f1?: number | null;
  epochDuration?: number | null;
};

type LineMetricKey = Exclude<keyof MetricPoint, 'epoch' | 'epochDuration'>;

type LineSeries = {
  key: LineMetricKey;
  name?: string;
};

const toNumber = (value: unknown) => {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

export function Dashboard({
  username,
  sampleImages,
  supportedModels,
  maxDatasetUploadMb,
  maxModelUploadMb,
  onLogout,
  onNavigateToSettings,
}: DashboardProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedSample, setSelectedSample] = useState<string>('');
  const [selectedModelFile, setSelectedModelFile] = useState<File | null>(null);
  const [activeSection, setActiveSection] = useState<'dashboard' | 'inference' | 'training' | 'monitoring' | 'logs'>('inference');
  const [isInputPanelOpen, setIsInputPanelOpen] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [expandedStage, setExpandedStage] = useState<number | null>(null);
  const [backendResult, setBackendResult] = useState<AnalysisResult | null>(null);
  const [message, setMessage] = useState<string>('');
  const [messageType, setMessageType] = useState<'success' | 'error' | ''>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modelInputRef = useRef<HTMLInputElement>(null);
  const datasetInputRef = useRef<HTMLInputElement>(null);
  const trainingLogRef = useRef<HTMLDivElement>(null);
  const [isLogPinned, setIsLogPinned] = useState(true);

  const [pipelineStages, setPipelineStages] = useState<PipelineStage[]>([
    { id: 1, name: 'Authentication', status: 'pending', progress: 0 },
    { id: 2, name: 'Rate Limiting', status: 'pending', progress: 0 },
    { id: 3, name: 'Input Validation', status: 'pending', progress: 0 },
    { id: 4, name: 'Weight Inspection', status: 'pending', progress: 0 },
    { id: 5, name: 'Behavioral Analysis', status: 'pending', progress: 0 },
    { id: 6, name: 'Signature Scanning', status: 'pending', progress: 0 },
    { id: 7, name: 'Anomaly Detection', status: 'pending', progress: 0 },
    { id: 8, name: 'Risk Assessment', status: 'pending', progress: 0 },
    { id: 9, name: 'Report Generation', status: 'pending', progress: 0 },
  ]);

  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);

  const [samples, setSamples] = useState(
    sampleImages.map((item) => ({ value: item.name, label: item.name, url: item.url }))
  );

  useEffect(() => {
    setSamples(sampleImages.map((item) => ({ value: item.name, label: item.name, url: item.url })));
  }, [sampleImages]);

  useEffect(() => {
    if (supportedModels.length && !supportedModels.find((model) => model.id === trainingConfig.model_type)) {
      setTrainingConfig((prev) => ({ ...prev, model_type: supportedModels[0].id }));
    }
  }, [supportedModels]);

  const loadTrainingOverview = async () => {
    try {
      const [datasetsRes, jobsRes, modelsRes] = await Promise.all([
        apiListDatasets(),
        apiListJobs(),
        apiListModels(),
      ]);

      if (datasetsRes.ok && datasetsRes.datasets) {
        setDatasets(datasetsRes.datasets);
        if (!selectedDatasetId && datasetsRes.datasets.length) {
          setSelectedDatasetId(datasetsRes.datasets[0].dataset_id);
        }
      }

      if (jobsRes.ok && jobsRes.jobs) {
        setTrainingJobs(jobsRes.jobs);
      }

      if (modelsRes.ok && modelsRes.models) {
        setModels(modelsRes.models);
      }
    } catch (_error) {
      setTrainingError('Unable to load training resources from the backend.');
    }
  };

  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [models, setModels] = useState<TrainingModel[]>([]);
  const [trainingJobs, setTrainingJobs] = useState<TrainingJob[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<TrainingJob | null>(null);
  const [datasetFile, setDatasetFile] = useState<File | null>(null);
  const [trainingMessage, setTrainingMessage] = useState<string>('');
  const [trainingError, setTrainingError] = useState<string>('');
  const [isDatasetUploading, setIsDatasetUploading] = useState(false);
  const [isTrainingStarting, setIsTrainingStarting] = useState(false);
  const [trainingConfig, setTrainingConfig] = useState({
    model_type: supportedModels[0]?.id || 'efficientnet-b0',
    epochs: 5,
    batch_size: 16,
    learning_rate: 0.001,
    freeze_backbone: false,
  });
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');

  useEffect(() => {
    void loadTrainingOverview();
  }, []);

  useEffect(() => {
    if (!activeJobId) {
      return;
    }

    let isMounted = true;
    const pollJob = async () => {
      const response = await apiGetJob(activeJobId);
      if (!isMounted) {
        return;
      }
      if (response.ok && response.job) {
        setActiveJob(response.job);
        setTrainingJobs((prev) => {
          const filtered = prev.filter((job) => job.job_id !== response.job?.job_id);
          return [response.job!, ...filtered];
        });
        if (['completed', 'failed', 'cancelled'].includes(response.job.status)) {
          setActiveJobId(null);
          void loadTrainingOverview();
        }
      }
    };

    void pollJob();
    const interval = window.setInterval(pollJob, 3000);
    return () => {
      isMounted = false;
      window.clearInterval(interval);
    };
  }, [activeJobId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setSelectedSample('');
    }
  };

  const handleSampleSelect = (value: string) => {
    setSelectedSample(value);
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedModelFile(e.target.files[0]);
    }
  };

  const handleDatasetUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetFile) {
      setTrainingError('Please select a dataset ZIP to upload.');
      return;
    }

    setIsDatasetUploading(true);
    setTrainingError('');
    setTrainingMessage('');

    const response = await apiUploadDataset(datasetFile);
    if (!response.ok) {
      setTrainingError(response.message || 'Dataset upload failed.');
      setIsDatasetUploading(false);
      return;
    }

    setTrainingMessage('Dataset validated successfully.');
    setDatasetFile(null);
    if (response.dataset) {
      setDatasets((prev) => [response.dataset!, ...prev.filter((d) => d.dataset_id !== response.dataset?.dataset_id)]);
      setSelectedDatasetId(response.dataset.dataset_id);
    }
    setIsDatasetUploading(false);
  };

  const handleTrainingStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDatasetId) {
      setTrainingError('Select a validated dataset before starting training.');
      return;
    }

    setIsTrainingStarting(true);
    setTrainingError('');
    setTrainingMessage('');

    const response = await apiStartTraining({
      dataset_id: selectedDatasetId,
      model_type: trainingConfig.model_type,
      epochs: trainingConfig.epochs,
      batch_size: trainingConfig.batch_size,
      learning_rate: trainingConfig.learning_rate,
      freeze_backbone: trainingConfig.freeze_backbone,
    });

    if (!response.ok || !response.job) {
      setTrainingError(response.message || 'Training could not be started.');
      setIsTrainingStarting(false);
      return;
    }

    setTrainingMessage('Training job queued.');
    setActiveJobId(response.job.job_id);
    setActiveJob(response.job);
    setTrainingJobs((prev) => [response.job!, ...prev.filter((job) => job.job_id !== response.job?.job_id)]);
    setIsTrainingStarting(false);
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile && !selectedSample) {
      setMessageType('error');
      setMessage('Please upload an image or choose a sample image.');
      return;
    }

    setIsAnalyzing(true);
    setMessage('');
    setMessageType('');

    try {
      const formData = new FormData();
      if (selectedFile) {
        formData.append('image', selectedFile);
      }
      if (selectedSample) {
        formData.append('sample_image', selectedSample);
      }
      if (selectedModelFile) {
        formData.append('model', selectedModelFile);
      }

      const response = await apiInference(formData);

      if (response.sample_images?.length) {
        setSamples(response.sample_images.map((item: SampleImage) => ({ value: item.name, label: item.name, url: item.url })));
      }

      if (response.result?.pipeline_steps?.length) {
        setPipelineStages(
          response.result.pipeline_steps.map((step: any, idx: number) => ({
            id: idx + 1,
            name: step.title,
            status: step.status === 'pass' ? 'success' : step.status === 'warn' ? 'warning' : step.status === 'fail' ? 'error' : 'pending',
            progress: step.status === 'pending' ? 0 : 100,
            message: step.body,
          }))
        );
      }

      if (response.result?.audit_log?.length) {
        setAuditLog(
          response.result.audit_log.map((entry: any, idx: number) => ({
            id: idx + 1,
            action: entry.stage,
            details: entry.message,
            status: entry.decision === 'pass' ? 'success' : entry.decision === 'warn' ? 'warning' : 'error',
          }))
        );
      } else {
        setAuditLog([]);
      }

      if (response.result) {
        setBackendResult(response.result);
      }

      setMessageType(response.ok ? 'success' : 'error');
      setMessage(response.message || (response.ok ? 'Analysis completed.' : 'Analysis failed.'));
    } catch (_error) {
      setMessageType('error');
      setMessage('Failed to contact backend. Ensure Flask server is running.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-success" />;
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-warning" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-destructive" />;
      case 'running':
        return <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />;
      default:
        return <div className="w-5 h-5 rounded-full border-2 border-muted" />;
    }
  };

  const getAuditStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-success/10 text-success';
      case 'warning':
        return 'bg-warning/10 text-warning';
      case 'error':
        return 'bg-destructive/10 text-destructive';
      default:
        return 'bg-muted/50 text-muted-foreground';
    }
  };

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'inference', label: 'Inference', icon: Shield },
    { id: 'training', label: 'Training', icon: TrendingUp },
    { id: 'monitoring', label: 'Monitoring', icon: BarChart3 },
    { id: 'logs', label: 'Logs', icon: FileCheck },
  ];

  const activeTrainingJob = activeJob || trainingJobs[0] || null;
  const trainingMetrics = activeTrainingJob?.metrics;
  const chartData = useMemo<MetricPoint[]>(() => {
    if (!trainingMetrics) {
      return [];
    }
    const maxLen = Math.max(
      trainingMetrics.train_loss?.length || 0,
      trainingMetrics.val_loss?.length || 0,
      trainingMetrics.train_accuracy?.length || 0,
      trainingMetrics.val_accuracy?.length || 0,
      trainingMetrics.precision?.length || 0,
      trainingMetrics.recall?.length || 0,
      trainingMetrics.f1?.length || 0,
      trainingMetrics.epoch_durations?.length || 0,
    );

    return Array.from({ length: maxLen }, (_, idx) => ({
      epoch: idx + 1,
      trainLoss: toNumber(trainingMetrics.train_loss?.[idx]),
      valLoss: toNumber(trainingMetrics.val_loss?.[idx]),
      trainAccuracy: toNumber(trainingMetrics.train_accuracy?.[idx]),
      valAccuracy: toNumber(trainingMetrics.val_accuracy?.[idx]),
      precision: toNumber(trainingMetrics.precision?.[idx]),
      recall: toNumber(trainingMetrics.recall?.[idx]),
      f1: toNumber(trainingMetrics.f1?.[idx]),
      epochDuration: toNumber(trainingMetrics.epoch_durations?.[idx]),
    }));
  }, [trainingMetrics]);

  const metricSummary = useMemo(() => {
    if (!chartData.length) {
      return null;
    }
    const latest = chartData[chartData.length - 1];
    const numeric = (values: Array<number | null | undefined>) =>
      values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    const bestValAcc = Math.max(...numeric(chartData.map((item) => item.valAccuracy)), 0);
    const bestF1 = Math.max(...numeric(chartData.map((item) => item.f1)), 0);
    return {
      latestEpoch: latest.epoch,
      latestTrainLoss: latest.trainLoss ?? 0,
      latestValLoss: latest.valLoss ?? 0,
      bestValAcc,
      bestF1,
      latestEpochDuration: latest.epochDuration ?? 0,
    };
  }, [chartData]);

  const chartConfig = {
    trainLoss: { label: 'Train Loss', color: 'hsl(336 78% 62%)' },
    valLoss: { label: 'Val Loss', color: 'hsl(280 75% 64%)' },
    trainAccuracy: { label: 'Train Acc', color: 'hsl(150 70% 45%)' },
    valAccuracy: { label: 'Val Acc', color: 'hsl(195 85% 52%)' },
    precision: { label: 'Precision', color: 'hsl(88 70% 50%)' },
    recall: { label: 'Recall', color: 'hsl(32 90% 55%)' },
    f1: { label: 'F1', color: 'hsl(210 80% 60%)' },
    epochDuration: { label: 'Epoch (s)', color: 'hsl(262 65% 60%)' },
    count: { label: 'Count', color: 'hsl(165 75% 45%)' },
  };

  const classDistributionData = useMemo(() => {
    if (!selectedDatasetId) {
      return [];
    }
    const dataset = datasets.find((item) => item.dataset_id === selectedDatasetId);
    const dist = dataset?.class_distribution || {};
    return Object.entries(dist).map(([label, count]) => ({ label, count }));
  }, [datasets, selectedDatasetId]);

  const classLabelSummary = useMemo(() => {
    const labels = backendResult?.class_names;
    if (!labels || !labels.length) {
      return 'ImageNet (1000 classes)';
    }
    if (labels.length <= 6) {
      return labels.join(', ');
    }
    return `${labels.slice(0, 6).join(', ')} (+${labels.length - 6} more)`;
  }, [backendResult]);

  const handleTrainingLogScroll = () => {
    const logEl = trainingLogRef.current;
    if (!logEl) {
      return;
    }
    const threshold = 24;
    const atBottom = logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight < threshold;
    setIsLogPinned(atBottom);
  };

  useEffect(() => {
    const logEl = trainingLogRef.current;
    if (!logEl || !isLogPinned) {
      return;
    }
    logEl.scrollTop = logEl.scrollHeight;
  }, [activeTrainingJob?.logs, isLogPinned]);

  const confusionMatrix = trainingMetrics?.confusion_matrix || [];
  const confusionLabels = trainingMetrics?.class_names || [];
  const confusionMax = useMemo(() => {
    if (!confusionMatrix.length) {
      return 0;
    }
    return confusionMatrix.flat().reduce((max, value) => Math.max(max, value), 0);
  }, [confusionMatrix]);

  const getConfusionColor = (value: number, isDiagonal: boolean) => {
    const max = confusionMax || 1;
    const intensity = Math.min(value / max, 1);
    const hue = isDiagonal ? 150 : 25;
    const saturation = isDiagonal ? 70 : 80;
    const lightness = isDiagonal ? 40 : 55;
    const alpha = 0.15 + intensity * 0.75;
    return `hsl(${hue} ${saturation}% ${lightness}% / ${alpha})`;
  };

  const MetricLineChart = ({
    lines,
    yLabel,
    yDomain,
    yTickFormatter,
  }: {
    lines: LineSeries[];
    yLabel: string;
    yDomain?: [number, number] | ['auto', 'auto'];
    yTickFormatter?: (value: number) => string;
  }) => (
    <ChartContainer config={chartConfig} className="h-56 w-full">
      <LineChart data={chartData} margin={{ left: 12, right: 12 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="epoch"
          tickLine={false}
          axisLine={false}
          label={{ value: 'Epoch', position: 'insideBottomRight', offset: -6 }}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          domain={yDomain}
          tickFormatter={yTickFormatter}
          label={{ value: yLabel, angle: -90, position: 'insideLeft' }}
        />
        <ChartTooltip
          cursor={false}
          content={<ChartTooltipContent />}
          labelFormatter={(value) => `Epoch ${value}`}
        />
        <Legend verticalAlign="top" height={24} iconType="circle" />
        {lines.map((line) => (
          <Line
            key={line.key}
            type="monotone"
            dataKey={line.key}
            name={line.name || chartConfig[line.key as keyof typeof chartConfig]?.label}
            stroke={`var(--color-${line.key})`}
            strokeWidth={2.5}
            dot={{ r: 3, strokeWidth: 1, fill: `var(--color-${line.key})` }}
            activeDot={{ r: 5 }}
            connectNulls
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Mobile Header */}
      <div className="lg:hidden flex items-center justify-between p-4 border-b border-border bg-card">
        <div className="flex items-center gap-2">
          <Shield className="w-6 h-6 text-accent" />
          <span className="font-mono">SecureMLOPS</span>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="p-2 rounded-lg hover:bg-muted"
          >
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 bg-background z-50 pt-16">
          <div className="p-4 space-y-2">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  setActiveSection(item.id as typeof activeSection);
                  setIsMobileMenuOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left ${
                  activeSection === item.id ? 'bg-muted' : 'hover:bg-muted'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </button>
            ))}
            <button
              onClick={() => {
                onNavigateToSettings();
                setIsMobileMenuOpen(false);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-muted transition-colors text-left"
            >
              <SettingsIcon className="w-5 h-5" />
              <span>Settings</span>
            </button>
            <button
              onClick={onLogout}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-muted text-destructive transition-colors text-left"
            >
              <LogOut className="w-5 h-5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      )}

      {/* Sidebar - Desktop */}
      <div className="hidden lg:flex lg:flex-col lg:w-64 border-r border-sidebar-border bg-sidebar p-4">
        <div className="flex items-center gap-2 mb-8">
          <Shield className="w-8 h-8 text-accent" />
          <span className="font-mono">SecureMLOPS</span>
        </div>

        <nav className="flex-1 space-y-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id as typeof activeSection)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left ${
                activeSection === item.id ? 'bg-sidebar-accent' : 'hover:bg-sidebar-accent'
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="border-t border-sidebar-border pt-4 space-y-2">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="font-mono">Theme</span>
            <ThemeToggle />
          </div>
          <button
            onClick={onNavigateToSettings}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-sidebar-accent transition-colors text-left"
          >
            <SettingsIcon className="w-5 h-5" />
            <span>Settings</span>
          </button>
          <button
            onClick={onLogout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-sidebar-accent text-destructive transition-colors text-left"
          >
            <LogOut className="w-5 h-5" />
            <span>Logout</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Input Panel */}
        {activeSection === 'inference' && (
          <div className={`input-panel bg-card border-b lg:border-b-0 lg:border-r border-border transition-all duration-300 ${isInputPanelOpen ? 'lg:w-96' : 'lg:w-0'} overflow-hidden`}>
            <div className="p-6 space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-foreground">Inference Input</h2>
                <button
                  id="toggleInputPanel"
                  onClick={() => setIsInputPanelOpen(!isInputPanelOpen)}
                  className="hidden lg:block p-1 hover:bg-muted rounded"
                >
                  {isInputPanelOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              </div>

              <p className="font-mono text-muted-foreground">Signed in as {username}</p>

              <form action="/analyze" method="post" encType="multipart/form-data" onSubmit={handleAnalyze} className="space-y-6">
                {/* File Upload */}
                <div>
                  <label className="block mb-2 text-foreground">Upload Image</label>
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-border rounded-lg p-6 text-center cursor-pointer hover:border-accent transition-colors bg-input-background"
                  >
                    <Upload className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                    <p className="text-muted-foreground mb-1">Click to upload</p>
                    <p className="font-mono text-muted-foreground">.jpg, .jpeg, .png</p>
                    {selectedFile && (
                      <p
                        id="filePreviewName"
                        className="mt-2 text-foreground font-mono truncate"
                        title={selectedFile.name}
                      >
                        {selectedFile.name}
                      </p>
                    )}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    id="fileInput"
                    name="image"
                    onChange={handleFileChange}
                    accept=".jpg,.jpeg,.png"
                    className="hidden"
                  />
                </div>

                {/* Sample Selection */}
                <div>
                  <label className="block mb-2 text-foreground">Or Select Sample</label>
                  <div className="space-y-2">
                    {samples.map((sample) => (
                      <label
                        key={sample.value}
                        className="flex items-center gap-3 p-3 border border-border rounded-lg cursor-pointer hover:bg-muted transition-colors"
                      >
                        <input
                          type="radio"
                          name="sample_image"
                          value={sample.value}
                          checked={selectedSample === sample.value}
                          onChange={() => handleSampleSelect(sample.value)}
                          className="w-4 h-4 text-accent focus:ring-accent"
                        />
                        {sample.url ? (
                          <img src={sample.url} alt={sample.label} className="w-8 h-8 rounded object-cover" />
                        ) : (
                          <ImageIcon className="w-4 h-4 text-muted-foreground" />
                        )}
                        <span className="flex-1 font-mono truncate" title={sample.label}>
                          {sample.label}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Optional Model Upload */}
                <div>
                  <label className="block mb-2 text-foreground">Optional Model Checkpoint</label>
                  <div
                    onClick={() => modelInputRef.current?.click()}
                    className="border-2 border-dashed border-border rounded-lg p-4 text-center cursor-pointer hover:border-accent transition-colors bg-input-background"
                  >
                    <Upload className="w-6 h-6 mx-auto mb-2 text-muted-foreground" />
                    <p className="text-muted-foreground mb-1">Upload .pt file</p>
                    <p className="font-mono text-muted-foreground">Max {maxModelUploadMb} MB</p>
                    {selectedModelFile && (
                      <p className="mt-2 text-foreground font-mono truncate" title={selectedModelFile.name}>
                        {selectedModelFile.name}
                      </p>
                    )}
                  </div>
                  <input
                    ref={modelInputRef}
                    type="file"
                    id="modelInput"
                    name="model"
                    onChange={handleModelChange}
                    accept=".pt,.pth"
                    className="hidden"
                  />
                </div>

                <button
                  id="openInputPanel"
                  type="submit"
                  disabled={isAnalyzing || (!selectedFile && !selectedSample)}
                  className="w-full bg-accent hover:bg-accent-600 disabled:bg-muted disabled:text-muted-foreground text-accent-foreground py-3 rounded-lg transition-colors"
                >
                  {isAnalyzing ? 'Analyzing...' : 'Run Analysis'}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {activeSection === 'dashboard' && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-muted-foreground">Datasets</span>
                    <Database className="w-5 h-5 text-accent" />
                  </div>
                  <div className="text-foreground">{datasets.length}</div>
                  <p className="font-mono text-muted-foreground mt-1">Validated corpora</p>
                </div>
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-muted-foreground">Training Jobs</span>
                    <PlayCircle className="w-5 h-5 text-accent" />
                  </div>
                  <div className="text-foreground">{trainingJobs.length}</div>
                  <p className="font-mono text-muted-foreground mt-1">
                    {trainingJobs.filter((job) => job.status === 'completed').length} completed
                  </p>
                </div>
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-muted-foreground">Trained Models</span>
                    <FileCheck className="w-5 h-5 text-success" />
                  </div>
                  <div className="text-foreground">{models.length}</div>
                  <p className="font-mono text-muted-foreground mt-1">Ready for inference</p>
                </div>
              </div>

              <div className="bg-card rounded-lg border border-border p-6">
                <h2 className="mb-4 text-foreground">Latest Inference Snapshot</h2>
                {backendResult ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono">
                    <div className="flex items-center gap-2 min-w-0">
                      <Database className="w-4 h-4 text-muted-foreground" />
                      <span className="text-muted-foreground truncate" title={backendResult.prediction || 'N/A'}>
                        Prediction: {backendResult.prediction || 'N/A'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 min-w-0">
                      <Lock className="w-4 h-4 text-muted-foreground" />
                      <span className="text-muted-foreground truncate" title={backendResult.risk_level}>
                        Risk Level: {backendResult.risk_level}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 min-w-0">
                      <Shield className="w-4 h-4 text-muted-foreground" />
                      <span className="text-muted-foreground truncate" title={backendResult.model_name || 'EfficientNet-B0'}>
                        Model: {backendResult.model_name || 'EfficientNet-B0'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 min-w-0">
                      <Activity className="w-4 h-4 text-muted-foreground" />
                      <span className="text-muted-foreground truncate" title={backendResult.status.replaceAll('_', ' ')}>
                        Status: {backendResult.status.replaceAll('_', ' ')}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="font-mono text-muted-foreground">Run an inference to populate dashboard telemetry.</p>
                )}
              </div>
            </>
          )}

          {activeSection === 'inference' && (
            <>
              {message && (
                <div className={`rounded-lg border px-4 py-3 ${messageType === 'error' ? 'border-destructive/30 bg-destructive/10 text-destructive' : 'border-success/30 bg-success/10 text-success'}`}>
                  {message}
                </div>
              )}

              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div className="xl:col-span-2 space-y-6">
                  <div className="pipeline-panel bg-card rounded-lg border border-border p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-foreground">Analysis Pipeline</h2>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Activity className="w-4 h-4" />
                        <span className="font-mono">{pipelineStages.filter((stage) => stage.status !== 'pending').length}/9 stages</span>
                      </div>
                    </div>
                    <div className="space-y-3">
                      {pipelineStages.map((stage) => (
                        <div key={stage.id} className="border border-border rounded-lg overflow-hidden">
                          <div
                            onClick={() => setExpandedStage(expandedStage === stage.id ? null : stage.id)}
                            className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                          >
                            <div className="flex items-center gap-3 flex-1">
                              {getStatusIcon(stage.status)}
                              <div className="flex-1">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="font-mono text-foreground">{stage.name}</span>
                                  {stage.duration && (
                                    <span className="font-mono text-muted-foreground ml-2">{stage.duration}</span>
                                  )}
                                </div>
                                {stage.status === 'running' && stage.progress !== undefined && (
                                  <div className="w-full bg-muted rounded-full h-1.5 mt-2">
                                    <div
                                      className="bg-accent h-1.5 rounded-full transition-all duration-300"
                                      style={{ width: `${stage.progress}%` }}
                                    />
                                  </div>
                                )}
                              </div>
                            </div>
                            {expandedStage === stage.id ? <ChevronUp className="w-4 h-4 ml-2" /> : <ChevronDown className="w-4 h-4 ml-2" />}
                          </div>
                          {expandedStage === stage.id && stage.message && (
                            <div className="px-4 pb-4 pt-2 border-t border-border bg-muted/30">
                              <p className="font-mono text-muted-foreground break-words">
                                {stage.message}
                              </p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="verdict-card bg-card rounded-lg border border-border p-6">
                    <h2 className="mb-4 text-foreground">Current Analysis</h2>
                    {backendResult ? (
                      <div className="p-6 bg-muted/40 border border-border rounded-lg space-y-3">
                        <h3 className="text-foreground mb-1">{backendResult.decision_reason}</h3>
                        <p className="font-mono text-muted-foreground truncate" title={backendResult.status.replaceAll('_', ' ')}>
                          Status: {backendResult.status.replaceAll('_', ' ')}
                        </p>
                        <div className="grid grid-cols-2 gap-3 font-mono">
                          <div className="flex items-center gap-2 min-w-0">
                            <Database className="w-4 h-4 text-muted-foreground" />
                            <span className="text-muted-foreground truncate" title={backendResult.prediction || 'N/A'}>
                              Prediction: {backendResult.prediction || 'N/A'}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 min-w-0">
                            <Lock className="w-4 h-4 text-muted-foreground" />
                            <span
                              className="text-muted-foreground truncate"
                              title={backendResult.confidence ? `${(backendResult.confidence * 100).toFixed(2)}%` : 'N/A'}
                            >
                              Confidence: {backendResult.confidence ? `${(backendResult.confidence * 100).toFixed(2)}%` : 'N/A'}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 min-w-0">
                            <Shield className="w-4 h-4 text-muted-foreground" />
                            <span className="text-muted-foreground truncate" title={backendResult.model_name || 'EfficientNet-B0'}>
                              Model: {backendResult.model_name || 'EfficientNet-B0'}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 min-w-0">
                            <Activity className="w-4 h-4 text-muted-foreground" />
                            <span className="text-muted-foreground truncate" title={backendResult.risk_level}>
                              Risk: {backendResult.risk_level}
                            </span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="p-6 bg-warning/10 border border-warning/20 rounded-lg">
                        <div className="flex items-start gap-4">
                          <div className="p-3 bg-warning/20 rounded-lg">
                            <Zap className="w-6 h-6 text-warning" />
                          </div>
                          <div className="flex-1">
                            <h3 className="text-foreground mb-1">Pipeline Ready</h3>
                            <p className="font-mono text-muted-foreground mb-3">Run analysis to inspect your 9-stage security pipeline output.</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-6">
                  <div className="bg-card rounded-lg border border-border p-6">
                    <h2 className="mb-4 text-foreground">Inference Model Information</h2>
                    {backendResult ? (
                      <div className="space-y-2 font-mono text-muted-foreground">
                        <div>Source: {(backendResult.model_source || 'default').toUpperCase()}</div>
                        <div>Architecture: {backendResult.model_type || 'EfficientNet-B0'}</div>
                        <div>Checkpoint: {backendResult.model_name || 'EfficientNet-B0'}</div>
                        <div>Status: {backendResult.checkpoint_loaded ? 'Loaded Successfully' : 'Unavailable'}</div>
                        <div>Classes: {classLabelSummary}</div>
                        <div>Num Classes: {backendResult.num_classes ?? 1000}</div>
                        <div>Created At: {backendResult.model_created_at || 'N/A'}</div>
                        <div>Reconstruction: {backendResult.reconstruction_status || 'default_loaded'}</div>
                      </div>
                    ) : (
                      <p className="font-mono text-muted-foreground">No inference data available yet.</p>
                    )}
                  </div>
                  <div className="bg-card rounded-lg border border-border p-6">
                    <h2 className="mb-4 text-foreground">Security Signals</h2>
                    {backendResult ? (
                      <div className="space-y-2 font-mono text-muted-foreground">
                        <div>Risk: {backendResult.risk_level}</div>
                        <div>Status: {backendResult.status.replaceAll('_', ' ')}</div>
                        <div>Anomaly: {backendResult.anomaly ? 'Detected' : 'Normal'}</div>
                        <div>Adversarial: {backendResult.adversarial ? 'Detected' : 'Normal'}</div>
                      </div>
                    ) : (
                      <p className="font-mono text-muted-foreground">Signals will appear after an inference run.</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="audit-list bg-card rounded-lg border border-border p-6">
                <h2 className="mb-4 text-foreground">Audit Log</h2>
                {auditLog.length ? (
                  <div className="space-y-2">
                    {auditLog.map((entry) => (
                      <div key={entry.id} className="p-3 border border-border rounded-lg hover:bg-muted/50 transition-colors">
                        <div className="flex items-start gap-3">
                          <span className={`px-2 py-1 rounded font-mono ${getAuditStatusColor(entry.status)}`}>
                            {entry.status.toUpperCase()}
                          </span>
                          <div className="flex-1">
                            <div className="flex items-start justify-between">
                              <span className="text-foreground">{entry.action}</span>
                              <span className="font-mono text-muted-foreground">{entry.timestamp}</span>
                            </div>
                            {entry.details && (
                              <p className="font-mono text-muted-foreground mt-1">{entry.details}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="font-mono text-muted-foreground">No audit entries yet.</p>
                )}
              </div>
            </>
          )}

          {activeSection === 'training' && (
            <>
              {(trainingError || trainingMessage) && (
                <div className={`rounded-lg border px-4 py-3 ${trainingError ? 'border-destructive/30 bg-destructive/10 text-destructive' : 'border-success/30 bg-success/10 text-success'}`}>
                  {trainingError || trainingMessage}
                </div>
              )}

              <div className="flex items-center justify-between">
                <h2 className="text-foreground">Training Workspace</h2>
                <button
                  onClick={() => void loadTrainingOverview()}
                  className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg hover:bg-muted transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span className="font-mono text-sm">Refresh</span>
                </button>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="bg-card rounded-lg border border-border p-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <Upload className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Dataset Upload</h3>
                  </div>
                  <form onSubmit={handleDatasetUpload} className="space-y-4">
                    <div
                      onClick={() => datasetInputRef.current?.click()}
                      className="border-2 border-dashed border-border rounded-lg p-4 text-center cursor-pointer hover:border-accent transition-colors bg-input-background"
                    >
                      <p className="text-muted-foreground mb-1">Upload dataset.zip</p>
                      <p className="font-mono text-muted-foreground">Max {maxDatasetUploadMb} MB</p>
                      {datasetFile && <p className="mt-2 font-mono text-foreground">{datasetFile.name}</p>}
                    </div>
                    <input
                      ref={datasetInputRef}
                      type="file"
                      accept=".zip"
                      className="hidden"
                      onChange={(event) => setDatasetFile(event.target.files?.[0] || null)}
                    />
                    <p className="font-mono text-muted-foreground">
                      Expected structure: dataset/ &gt; class folders and classes.json.
                    </p>
                    <button
                      type="submit"
                      disabled={isDatasetUploading}
                      className="w-full bg-accent hover:bg-accent-600 disabled:bg-muted disabled:text-muted-foreground text-accent-foreground py-2.5 rounded-lg transition-colors"
                    >
                      {isDatasetUploading ? 'Uploading...' : 'Upload & Validate'}
                    </button>
                  </form>
                  <div className="pt-2">
                    <h4 className="font-mono text-sm text-muted-foreground mb-2">Validated Datasets</h4>
                    {datasets.length ? (
                      <div className="space-y-2">
                        {datasets.slice(0, 4).map((dataset) => (
                          <div key={dataset.dataset_id} className="border border-border rounded-lg p-3">
                            <div className="text-foreground font-mono text-sm">{dataset.source_name || dataset.dataset_id}</div>
                            <div className="text-muted-foreground font-mono text-xs">{dataset.image_count} images · {dataset.class_names.join(', ')}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="font-mono text-muted-foreground">No datasets uploaded yet.</p>
                    )}
                  </div>
                </div>

                <div className="bg-card rounded-lg border border-border p-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <PlayCircle className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Training Configuration</h3>
                  </div>
                  <form onSubmit={handleTrainingStart} className="space-y-4">
                    <div>
                      <label className="block mb-2 text-foreground">Dataset</label>
                      <select
                        value={selectedDatasetId}
                        onChange={(event) => setSelectedDatasetId(event.target.value)}
                        className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
                      >
                        <option value="">Select dataset</option>
                        {datasets.map((dataset) => (
                          <option key={dataset.dataset_id} value={dataset.dataset_id}>
                            {dataset.source_name || dataset.dataset_id}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block mb-2 text-foreground">Model</label>
                      <select
                        value={trainingConfig.model_type}
                        onChange={(event) => setTrainingConfig((prev) => ({ ...prev, model_type: event.target.value }))}
                        className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
                      >
                        {supportedModels.map((model) => (
                          <option key={model.id} value={model.id}>
                            {model.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block mb-2 text-foreground">Epochs</label>
                        <input
                          type="number"
                          min={1}
                          max={50}
                          value={trainingConfig.epochs}
                          onChange={(event) => setTrainingConfig((prev) => ({ ...prev, epochs: Number(event.target.value) }))}
                          className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
                        />
                      </div>
                      <div>
                        <label className="block mb-2 text-foreground">Batch Size</label>
                        <input
                          type="number"
                          min={1}
                          max={256}
                          value={trainingConfig.batch_size}
                          onChange={(event) => setTrainingConfig((prev) => ({ ...prev, batch_size: Number(event.target.value) }))}
                          className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block mb-2 text-foreground">Learning Rate</label>
                      <input
                        type="number"
                        step="0.000001"
                        min={0}
                        max={0.1}
                        value={trainingConfig.learning_rate}
                        onChange={(event) => setTrainingConfig((prev) => ({ ...prev, learning_rate: Number(event.target.value) }))}
                        className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
                      />
                    </div>
                    <label className="flex items-center justify-between p-3 border border-border rounded-lg cursor-pointer hover:bg-muted transition-colors">
                      <span className="font-mono text-muted-foreground">Freeze backbone</span>
                      <input
                        type="checkbox"
                        checked={trainingConfig.freeze_backbone}
                        onChange={(event) => setTrainingConfig((prev) => ({ ...prev, freeze_backbone: event.target.checked }))}
                        className="w-5 h-5 rounded border-border text-accent focus:ring-accent"
                      />
                    </label>
                    <button
                      type="submit"
                      disabled={isTrainingStarting}
                      className="w-full bg-accent hover:bg-accent-600 disabled:bg-muted disabled:text-muted-foreground text-accent-foreground py-2.5 rounded-lg transition-colors"
                    >
                      {isTrainingStarting ? 'Starting...' : 'Start Training'}
                    </button>
                  </form>
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="bg-card rounded-lg border border-border p-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <Activity className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Training Progress</h3>
                  </div>
                  {activeTrainingJob ? (
                    <>
                      <div className="flex items-center justify-between font-mono text-muted-foreground">
                        <span>Status: {activeTrainingJob.status}</span>
                        <span>{activeTrainingJob.current_epoch || 0}/{activeTrainingJob.epochs || 0} epochs</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className="bg-accent h-2 rounded-full transition-all"
                          style={{ width: `${activeTrainingJob.progress || 0}%` }}
                        />
                      </div>
                      <div className="font-mono text-muted-foreground break-all">
                        Job ID: {activeTrainingJob.job_id}
                      </div>
                      <div className="grid grid-cols-2 gap-3 font-mono text-muted-foreground">
                        <div>Train Acc: {(trainingMetrics?.final_train_accuracy ?? 0).toFixed(3)}</div>
                        <div>Val Acc: {(trainingMetrics?.final_val_accuracy ?? 0).toFixed(3)}</div>
                        <div>Precision: {(trainingMetrics?.final_precision ?? 0).toFixed(3)}</div>
                        <div>Recall: {(trainingMetrics?.final_recall ?? 0).toFixed(3)}</div>
                        <div>F1: {(trainingMetrics?.final_f1 ?? 0).toFixed(3)}</div>
                        <div>Total Time: {(trainingMetrics?.total_duration_sec ?? 0).toFixed(1)}s</div>
                      </div>
                      {metricSummary ? (
                        <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                          <div className="mb-2 text-xs font-mono text-muted-foreground">Training Summary</div>
                          <div className="grid grid-cols-2 gap-2 text-xs font-mono text-muted-foreground">
                            <div>Latest Epoch: {metricSummary.latestEpoch}</div>
                            <div>Best Val Acc: {metricSummary.bestValAcc.toFixed(3)}</div>
                            <div>Latest Train Loss: {metricSummary.latestTrainLoss.toFixed(3)}</div>
                            <div>Latest Val Loss: {metricSummary.latestValLoss.toFixed(3)}</div>
                            <div>Best F1: {metricSummary.bestF1.toFixed(3)}</div>
                            <div>Epoch Time: {metricSummary.latestEpochDuration.toFixed(1)}s</div>
                          </div>
                        </div>
                      ) : null}
                      <div className="rounded-lg border border-border/60 bg-muted/20">
                        <div className="flex items-center justify-between px-3 py-2 text-xs font-mono text-muted-foreground">
                          <span>Live Logs</span>
                          <span>{isLogPinned ? 'Auto-follow' : 'Scroll paused'}</span>
                        </div>
                        <div
                          ref={trainingLogRef}
                          onScroll={handleTrainingLogScroll}
                          className="max-h-44 overflow-y-auto px-3 pb-3 text-xs font-mono text-muted-foreground"
                          style={{ scrollbarWidth: 'thin', scrollbarColor: 'hsl(var(--border)) transparent' }}
                        >
                          {(activeTrainingJob.logs || []).map((log) => (
                            <div key={log.timestamp} className="break-words py-0.5">
                              <span className="text-muted-foreground/70">{log.timestamp}</span>
                              <span className="mx-2 text-muted-foreground/40">•</span>
                              <span className="text-muted-foreground">{log.message}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  ) : (
                    <p className="font-mono text-muted-foreground">No active training jobs.</p>
                  )}
                </div>

                <div className="bg-card rounded-lg border border-border p-6 flex flex-col">
                  <div className="flex items-center gap-3 mb-4">
                    <BarChart3 className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Loss (Train vs Val)</h3>
                  </div>
                  {chartData.length ? (
                    <div className="flex-1 flex items-center justify-center">
                      <MetricLineChart
                        yLabel="Loss"
                        yDomain={['auto', 'auto']}
                        yTickFormatter={(value) => value.toFixed(2)}
                        lines={[
                          { key: 'trainLoss' },
                          { key: 'valLoss' },
                        ]}
                      />
                    </div>
                  ) : (
                    <p className="font-mono text-muted-foreground">Metrics will appear once training begins.</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="bg-card rounded-lg border border-border p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <BarChart3 className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Accuracy (Train vs Val)</h3>
                  </div>
                  {chartData.length ? (
                    <MetricLineChart
                      yLabel="Accuracy"
                      yDomain={[0, 1]}
                      yTickFormatter={(value) => value.toFixed(2)}
                      lines={[
                        { key: 'trainAccuracy' },
                        { key: 'valAccuracy' },
                      ]}
                    />
                  ) : (
                    <p className="font-mono text-muted-foreground">Metrics will appear once training begins.</p>
                  )}
                </div>

                <div className="bg-card rounded-lg border border-border p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <BarChart3 className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Precision / Recall / F1</h3>
                  </div>
                  {chartData.length ? (
                    <MetricLineChart
                      yLabel="Score"
                      yDomain={[0, 1]}
                      yTickFormatter={(value) => value.toFixed(2)}
                      lines={[
                        { key: 'precision' },
                        { key: 'recall' },
                        { key: 'f1' },
                      ]}
                    />
                  ) : (
                    <p className="font-mono text-muted-foreground">Metrics will appear once training begins.</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="bg-card rounded-lg border border-border p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <BarChart3 className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Epoch Duration</h3>
                  </div>
                  {chartData.length ? (
                    <ChartContainer config={chartConfig} className="h-56 w-full">
                      <BarChart data={chartData} margin={{ left: 12, right: 12 }}>
                        <CartesianGrid vertical={false} strokeDasharray="3 3" />
                        <XAxis dataKey="epoch" tickLine={false} axisLine={false} />
                        <YAxis tickLine={false} axisLine={false} tickFormatter={(value) => `${value.toFixed(1)}s`} />
                        <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                        <Bar dataKey="epochDuration" fill="var(--color-epochDuration)" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ChartContainer>
                  ) : (
                    <p className="font-mono text-muted-foreground">Timing metrics will appear once training begins.</p>
                  )}
                </div>

                <div className="bg-card rounded-lg border border-border p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <BarChart3 className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Dataset Class Distribution</h3>
                  </div>
                  {classDistributionData.length ? (
                    <ChartContainer config={chartConfig} className="h-56 w-full">
                      <BarChart data={classDistributionData} margin={{ left: 12, right: 12 }}>
                        <CartesianGrid vertical={false} strokeDasharray="3 3" />
                        <XAxis dataKey="label" tickLine={false} axisLine={false} />
                        <YAxis tickLine={false} axisLine={false} />
                        <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
                        <Bar dataKey="count" fill="var(--color-count)" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ChartContainer>
                  ) : (
                    <p className="font-mono text-muted-foreground">Upload a dataset to view class distribution.</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="bg-card rounded-lg border border-border p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <BarChart3 className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Confusion Matrix</h3>
                  </div>
                  {confusionMatrix.length ? (
                    <div className="space-y-3">
                      <p className="text-xs font-mono text-muted-foreground">
                        Higher values appear brighter. Diagonal cells highlight correct classifications.
                      </p>
                      <div className="overflow-auto">
                        <div
                          className="min-w-[520px] grid gap-1 text-xs font-mono text-muted-foreground"
                          style={{
                            gridTemplateColumns: `140px repeat(${confusionMatrix.length}, minmax(48px, 1fr))`,
                          }}
                        >
                          <div className="p-2 text-left text-foreground">True \ Pred</div>
                          {confusionMatrix.map((_, idx) => (
                            <div key={`col-${idx}`} className="p-2 text-center text-foreground">
                              {confusionLabels[idx] || `Class ${idx + 1}`}
                            </div>
                          ))}
                          {confusionMatrix.map((row, rowIdx) => (
                            <Fragment key={`row-${rowIdx}`}>
                              <div className="p-2 text-left text-foreground">
                                {confusionLabels[rowIdx] || `Class ${rowIdx + 1}`}
                              </div>
                              {row.map((value, colIdx) => {
                                const isDiagonal = rowIdx === colIdx;
                                return (
                                  <div
                                    key={`cell-${rowIdx}-${colIdx}`}
                                    className={`rounded-md border border-border/60 p-2 text-center ${
                                      isDiagonal ? 'font-semibold text-foreground' : 'text-muted-foreground'
                                    }`}
                                    style={{ background: getConfusionColor(value, isDiagonal) }}
                                  >
                                    {value}
                                  </div>
                                );
                              })}
                            </Fragment>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="font-mono text-muted-foreground">Confusion matrix will appear after validation epochs.</p>
                  )}
                </div>

                <div className="bg-card rounded-lg border border-border p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <BarChart3 className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Per-class Accuracy</h3>
                  </div>
                  {trainingMetrics?.per_class_accuracy && Object.keys(trainingMetrics.per_class_accuracy).length ? (
                    <div className="space-y-2">
                      {Object.entries(trainingMetrics.per_class_accuracy).map(([label, value]) => (
                        <div key={label} className="flex items-center justify-between font-mono text-muted-foreground min-w-0">
                          <span className="truncate" title={label}>{label}</span>
                          <span>{value.toFixed(3)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="font-mono text-muted-foreground">Per-class accuracy will appear after validation.</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="bg-card rounded-lg border border-border p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <History className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Training History</h3>
                  </div>
                  {trainingJobs.length ? (
                    <div className="space-y-3">
                      {trainingJobs.slice(0, 5).map((job) => (
                        <div key={job.job_id} className="border border-border rounded-lg p-3">
                          <div className="flex items-center justify-between gap-3 font-mono text-foreground min-w-0">
                            <span className="truncate" title={job.job_id}>{job.job_id}</span>
                            <span className="text-muted-foreground capitalize">{job.status}</span>
                          </div>
                          <div className="font-mono text-xs text-muted-foreground truncate" title={`Dataset: ${job.dataset_id}`}>
                            Epochs: {job.epochs ?? '-'} · Dataset: {job.dataset_id}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="font-mono text-muted-foreground">No training history yet.</p>
                  )}
                </div>

                <div className="bg-card rounded-lg border border-border p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <Download className="w-5 h-5 text-accent" />
                    <h3 className="text-foreground">Model Registry</h3>
                  </div>
                  {models.length ? (
                    <div className="space-y-3">
                      {models.slice(0, 5).map((model) => (
                        <div key={model.model_id} className="border border-border rounded-lg p-3 flex items-center justify-between gap-4">
                          <div className="min-w-0">
                            <div className="font-mono text-foreground truncate" title={model.model_label || model.model_type}>
                              {model.model_label || model.model_type}
                            </div>
                            <div className="font-mono text-xs text-muted-foreground truncate" title={model.class_names.join(', ')}>
                              Classes: {model.class_names.join(', ')}
                            </div>
                            <div className="font-mono text-xs text-muted-foreground truncate" title={model.model_id}>
                              ID: {model.model_id}
                            </div>
                          </div>
                          <a
                            href={`/api/training/models/${model.model_id}/download`}
                            className="shrink-0 px-3 py-2 border border-border rounded-lg hover:bg-muted transition-colors text-sm font-mono"
                          >
                            Download
                          </a>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="font-mono text-muted-foreground">No trained models available.</p>
                  )}
                </div>
              </div>
            </>
          )}

          {activeSection === 'monitoring' && (
            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center gap-3 mb-3">
                <BarChart3 className="w-5 h-5 text-accent" />
                <h2 className="text-foreground">Monitoring</h2>
              </div>
              <p className="font-mono text-muted-foreground">No monitoring telemetry available yet.</p>
            </div>
          )}

          {activeSection === 'logs' && (
            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center gap-3 mb-3">
                <FileCheck className="w-5 h-5 text-accent" />
                <h2 className="text-foreground">Security Logs</h2>
              </div>
              <p className="font-mono text-muted-foreground">No security events recorded.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
