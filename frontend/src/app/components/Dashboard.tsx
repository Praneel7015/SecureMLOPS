import { useEffect, useState, useRef } from 'react';
import { Upload, Image as ImageIcon, CheckCircle2, XCircle, AlertCircle, ChevronDown, ChevronUp, Shield, Settings as SettingsIcon, LogOut, Menu, X, TrendingUp, FileCheck, AlertTriangle, Clock, Activity, Zap, Database, Lock } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { apiAnalyze, AnalysisResult, SampleImage } from '../api';

interface DashboardProps {
  username: string;
  sampleImages: SampleImage[];
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

type RecentScan = {
  id: number;
  filename: string;
  timestamp: string;
  verdict: 'safe' | 'suspicious' | 'malicious';
  score: number;
};

export function Dashboard({ username, sampleImages, onLogout, onNavigateToSettings }: DashboardProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedSample, setSelectedSample] = useState<string>('');
  const [isInputPanelOpen, setIsInputPanelOpen] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [expandedStage, setExpandedStage] = useState<number | null>(null);
  const [backendResult, setBackendResult] = useState<AnalysisResult | null>(null);
  const [message, setMessage] = useState<string>('');
  const [messageType, setMessageType] = useState<'success' | 'error' | ''>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const [auditLog, setAuditLog] = useState<AuditEntry[]>([
    { id: 1, timestamp: '2026-04-26 14:32:15', action: 'System initialized', status: 'info' },
    { id: 2, timestamp: '2026-04-26 14:32:18', action: 'User authenticated', status: 'success', details: 'Session established' },
    { id: 3, timestamp: '2026-04-26 14:33:01', action: 'Model upload started', status: 'info', details: 'resnet50_v2.pt (87.5 MB)' },
    { id: 4, timestamp: '2026-04-26 14:33:05', action: 'Analysis pipeline initiated', status: 'success' },
  ]);

  const [samples, setSamples] = useState(
    sampleImages.map((item) => ({ value: item.name, label: item.name, url: item.url }))
  );

  useEffect(() => {
    setSamples(sampleImages.map((item) => ({ value: item.name, label: item.name, url: item.url })));
  }, [sampleImages]);

  const [recentScans] = useState<RecentScan[]>([
    { id: 1, filename: 'vgg16_trained.h5', timestamp: '2 hours ago', verdict: 'safe', score: 98 },
    { id: 2, filename: 'suspicious_lstm.pkl', timestamp: '5 hours ago', verdict: 'suspicious', score: 45 },
    { id: 3, filename: 'bert_fine_tuned.pt', timestamp: '1 day ago', verdict: 'safe', score: 95 },
  ]);

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

      const response = await apiAnalyze(formData);

      if (response.sample_images?.length) {
        setSamples(response.sample_images.map((item) => ({ value: item.name, label: item.name, url: item.url })));
      }

      if (response.result?.pipeline_steps?.length) {
        setPipelineStages(
          response.result.pipeline_steps.map((step, idx) => ({
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
          response.result.audit_log.map((entry, idx) => ({
            id: idx + 1,
            action: entry.stage,
            details: entry.message,
            status: entry.decision === 'pass' ? 'success' : entry.decision === 'warn' ? 'warning' : 'error',
          }))
        );
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

  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case 'safe':
        return 'text-success';
      case 'suspicious':
        return 'text-warning';
      case 'malicious':
        return 'text-destructive';
      default:
        return 'text-muted-foreground';
    }
  };

  const getVerdictBg = (verdict: string) => {
    switch (verdict) {
      case 'safe':
        return 'bg-success/10 border-success/20';
      case 'suspicious':
        return 'bg-warning/10 border-warning/20';
      case 'malicious':
        return 'bg-destructive/10 border-destructive/20';
      default:
        return 'bg-muted';
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
          <button
            onClick={onNavigateToSettings}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-sidebar-accent transition-colors text-left"
          >
            <SettingsIcon className="w-5 h-5" />
            <span>Settings</span>
          </button>
        </nav>

        <div className="border-t border-sidebar-border pt-4 space-y-2">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="font-mono">Theme</span>
            <ThemeToggle />
          </div>
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
        <div className={`input-panel bg-card border-b lg:border-b-0 lg:border-r border-border transition-all duration-300 ${isInputPanelOpen ? 'lg:w-96' : 'lg:w-0'} overflow-hidden`}>
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-foreground">Analysis Input</h2>
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
                    <p id="filePreviewName" className="mt-2 text-foreground font-mono">{selectedFile.name}</p>
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
                      <span className="flex-1 font-mono">{sample.label}</span>
                    </label>
                  ))}
                </div>
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

        {/* Main Content Area */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {message && (
            <div className={`rounded-lg border px-4 py-3 ${messageType === 'error' ? 'border-destructive/30 bg-destructive/10 text-destructive' : 'border-success/30 bg-success/10 text-success'}`}>
              {message}
            </div>
          )}

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-card rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted-foreground">Total Scans</span>
                <TrendingUp className="w-5 h-5 text-accent" />
              </div>
              <div className="text-foreground">247</div>
              <p className="font-mono text-muted-foreground mt-1">+12 this week</p>
            </div>

            <div className="bg-card rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted-foreground">Safe Models</span>
                <FileCheck className="w-5 h-5 text-success" />
              </div>
              <div className="text-foreground">189</div>
              <p className="font-mono text-success mt-1">76.5% pass rate</p>
            </div>

            <div className="bg-card rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted-foreground">Threats Detected</span>
                <AlertTriangle className="w-5 h-5 text-destructive" />
              </div>
              <div className="text-foreground">14</div>
              <p className="font-mono text-destructive mt-1">5.7% threat rate</p>
            </div>

            <div className="bg-card rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted-foreground">Avg Analysis Time</span>
                <Clock className="w-5 h-5 text-accent" />
              </div>
              <div className="text-foreground">3.2s</div>
              <p className="font-mono text-muted-foreground mt-1">-0.5s improvement</p>
            </div>
          </div>

          {/* Two Column Layout */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Pipeline Panel - Takes 2 columns */}
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
                          <p className="font-mono text-muted-foreground">
                            {stage.message}
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Verdict Card */}
              <div className="verdict-card bg-card rounded-lg border border-border p-6">
                <h2 className="mb-4 text-foreground">Current Analysis</h2>
                {backendResult ? (
                  <div className="p-6 bg-muted/40 border border-border rounded-lg space-y-3">
                    <h3 className="text-foreground mb-1">{backendResult.decision_reason}</h3>
                    <p className="font-mono text-muted-foreground">Status: {backendResult.status.replaceAll('_', ' ')}</p>
                    <div className="grid grid-cols-2 gap-3 font-mono">
                      <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-muted-foreground" />
                        <span className="text-muted-foreground">Prediction: {backendResult.prediction || 'N/A'}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Lock className="w-4 h-4 text-muted-foreground" />
                        <span className="text-muted-foreground">Confidence: {backendResult.confidence ? `${(backendResult.confidence * 100).toFixed(2)}%` : 'N/A'}</span>
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

            {/* Right Sidebar - Recent Scans */}
            <div className="space-y-6">
              {/* Recent Scans */}
              <div className="bg-card rounded-lg border border-border p-6">
                <h2 className="mb-4 text-foreground">Recent Scans</h2>
                <div className="space-y-3">
                  {recentScans.map((scan) => (
                    <div key={scan.id} className={`p-3 border rounded-lg ${getVerdictBg(scan.verdict)}`}>
                      <div className="flex items-start justify-between mb-2">
                        <span className="font-mono text-foreground">{scan.filename}</span>
                        <span className={`font-mono ${getVerdictColor(scan.verdict)} capitalize`}>
                          {scan.verdict}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-muted-foreground">{scan.timestamp}</span>
                        <span className="font-mono text-muted-foreground">Score: {scan.score}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="bg-card rounded-lg border border-border p-6">
                <h2 className="mb-4 text-foreground">Quick Actions</h2>
                <div className="space-y-2">
                  <button className="w-full flex items-center gap-3 px-4 py-3 border border-border rounded-lg hover:bg-muted transition-colors text-left">
                    <Upload className="w-4 h-4 text-accent" />
                    <span className="font-mono">Upload Model</span>
                  </button>
                  <button className="w-full flex items-center gap-3 px-4 py-3 border border-border rounded-lg hover:bg-muted transition-colors text-left">
                    <FileCheck className="w-4 h-4 text-success" />
                    <span className="font-mono">View Reports</span>
                  </button>
                  <button className="w-full flex items-center gap-3 px-4 py-3 border border-border rounded-lg hover:bg-muted transition-colors text-left">
                    <Activity className="w-4 h-4 text-accent" />
                    <span className="font-mono">System Status</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Audit Log - Full Width */}
          <div className="audit-list bg-card rounded-lg border border-border p-6">
            <h2 className="mb-4 text-foreground">Audit Log</h2>
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
          </div>
        </div>
      </div>
    </div>
  );
}
