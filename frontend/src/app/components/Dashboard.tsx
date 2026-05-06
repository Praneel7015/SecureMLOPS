import { useEffect, useState, useRef } from 'react';
import { Upload, Image as ImageIcon, CheckCircle2, XCircle, AlertCircle, ChevronDown, ChevronUp, Shield, Settings as SettingsIcon, LogOut, Menu, X, TrendingUp, FileCheck, AlertTriangle, Clock, Activity, Zap, Database, Lock } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { apiAnalyze, AnalysisResult, SampleImage } from '../api';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';
import { Label } from './ui/label';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from './ui/resizable';
import { ScrollArea } from './ui/scroll-area';
import { cn } from './ui/utils';

interface DashboardProps {
  username: string;
  sampleImages: SampleImage[];
  onLogout: () => void | Promise<void>;
  onNavigateToSettings: () => void;
  onNavigateToInput: () => void;
  onNavigateToActivity: () => void;
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

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setSelectedSample('');
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

  const getAuditBadgeVariant = (status: string) => {
    switch (status) {
      case 'success':
        return 'default';
      case 'warning':
        return 'secondary';
      case 'error':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getVerdictBadgeVariant = (verdict: string) => {
    switch (verdict) {
      case 'safe':
        return 'default';
      case 'suspicious':
        return 'secondary';
      case 'malicious':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-background text-foreground">
      {/* Mobile Header */}
      <div className="lg:hidden flex items-center justify-between p-4 border-b border-border bg-card">
        <div className="flex items-center gap-2">
          <Shield className="w-6 h-6 text-accent" />
          <span className="font-mono text-lg font-bold">Axion</span>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon">
                <Menu className="w-5 h-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[280px] sm:w-[350px] p-0 flex flex-col">
              <SheetHeader className="p-4 border-b border-border text-left">
                <SheetTitle className="flex items-center gap-2 font-mono text-xl">
                  <Shield className="w-6 h-6 text-accent" />
                  Axion
                </SheetTitle>
              </SheetHeader>
              <nav className="flex-1 overflow-y-auto p-4 space-y-2">
                <Button
                  variant="ghost"
                  className="w-full justify-start gap-3"
                  onClick={() => {
                    onNavigateToSettings();
                    setIsMobileMenuOpen(false);
                  }}
                >
                  <SettingsIcon className="w-5 h-5" />
                  Settings
                </Button>
              </nav>
              <div className="p-4 border-t border-border">
                <Button
                  variant="ghost"
                  className="w-full justify-start gap-3 text-destructive hover:bg-destructive/10 hover:text-destructive"
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    onLogout();
                  }}
                >
                  <LogOut className="w-5 h-5" />
                  Logout
                </Button>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {/* Sidebar - Desktop */}
      <div className="hidden lg:flex lg:flex-col lg:w-64 border-r border-sidebar-border bg-sidebar p-4">
        <div className="flex items-center gap-2 mb-8">
          <Shield className="w-8 h-8 text-accent" />
          <span className="font-mono">Axion</span>
        </div>

        <nav className="flex-1 space-y-2">
            <Button
              variant="ghost"
              className="w-full justify-start gap-3"
              onClick={() => { onNavigateToInput(); }}
            >
              <Upload className="w-5 h-5" />
              Input
            </Button>
            <Button
              variant="ghost"
              className="w-full justify-start gap-3"
              onClick={() => { onNavigateToActivity(); }}
            >
              <Activity className="w-5 h-5" />
              Activity
            </Button>
          <Button
            variant="ghost"
            className="w-full justify-start gap-3"
            onClick={onNavigateToSettings}
          >
            <SettingsIcon className="w-5 h-5" />
            Settings
          </Button>
        </nav>

        <div className="border-t border-sidebar-border pt-4 space-y-2">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="font-mono">Theme</span>
            <ThemeToggle />
          </div>
          <Button
            variant="ghost"
            className="w-full justify-start gap-3 text-destructive hover:bg-destructive/10"
            onClick={onLogout}
          >
            <LogOut className="w-5 h-5" />
            Logout
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Responsive Content Container */}
        <ResizablePanelGroup direction="horizontal" className="hidden lg:flex w-full h-full">
          {/* Input Panel Desktop */}
          {isInputPanelOpen && (
            <>
              <ResizablePanel defaultSize={35} minSize={25} maxSize={50} className="bg-card">
                <ScrollArea className="h-full">
                  <div className="p-6 space-y-6">
                    <div className="flex items-center justify-end gap-2">
                      <Button size="sm" variant="outline" onClick={() => onNavigateToInput()}>
                        Open Input Page
                      </Button>
                      <Button size="sm" onClick={() => onNavigateToActivity()}>
                        Open Activity
                      </Button>
                    </div>
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Analysis Input</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsInputPanelOpen(!isInputPanelOpen)}
                className="hidden lg:flex"
              >
                {isInputPanelOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
              </Button>
            </div>

            <p className="font-mono text-sm text-muted-foreground">Signed in as {username}</p>

            <form action="/analyze" method="post" encType="multipart/form-data" onSubmit={handleAnalyze} className="space-y-6">
              {/* File Upload */}
              <div className="space-y-2">
                <Label>Upload Image</Label>
                <Card
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  className="border-dashed cursor-pointer hover:border-accent transition-colors bg-muted/30 group relative"
                >
                  <CardContent className="p-6 flex flex-col items-center text-center">
                    {selectedFile ? (
                      <div className="relative w-full">
                        <img
                          src={URL.createObjectURL(selectedFile)}
                          alt="Preview"
                          className="mx-auto max-h-48 object-contain rounded-md"
                        />
                        <div className="absolute inset-0 bg-background/80 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity rounded-md">
                          <Upload className="w-8 h-8 mb-2 text-accent" />
                          <span className="font-medium">Change Image</span>
                        </div>
                        <p className="mt-4 font-mono text-sm truncate">{selectedFile.name}</p>
                      </div>
                    ) : selectedSample ? (
                      <div className="relative w-full">
                        <img
                          src={samples.find(s => s.value === selectedSample)?.url || ''}
                          alt="Sample Preview"
                          className="mx-auto max-h-48 object-contain rounded-md"
                        />
                        <div className="absolute inset-0 bg-background/80 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity rounded-md">
                          <Upload className="w-8 h-8 mb-2 text-accent" />
                          <span className="font-medium">Upload Instead</span>
                        </div>
                        <p className="mt-4 font-mono text-sm truncate">{selectedSample}</p>
                      </div>
                    ) : (
                      <>
                        <Upload className="w-8 h-8 mb-2 text-muted-foreground group-hover:scale-110 transition-transform" />
                        <p className="text-sm text-muted-foreground mb-1">Click or drag & drop</p>
                        <p className="font-mono text-xs text-muted-foreground">.jpg, .jpeg, .png</p>
                      </>
                    )}
                  </CardContent>
                </Card>
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
              <div className="space-y-2">
                <Label>Or Select Sample</Label>
                <div className="grid gap-2">
                  {samples.map((sample) => (
                    <Label
                      key={sample.value}
                      className={cn(
                        "flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-muted transition-colors",
                        selectedSample === sample.value ? "border-accent bg-accent/10" : ""
                      )}
                    >
                      <input
                        type="radio"
                        name="sample_image"
                        value={sample.value}
                        checked={selectedSample === sample.value}
                        onChange={() => handleSampleSelect(sample.value)}
                        className="w-4 h-4 text-accent focus:ring-accent hidden"
                      />
                      {sample.url ? (
                        <img src={sample.url} alt={sample.label} className="w-8 h-8 rounded object-cover" />
                      ) : (
                        <ImageIcon className="w-4 h-4 text-muted-foreground" />
                      )}
                      <span className="flex-1 font-mono text-sm">{sample.label}</span>
                    </Label>
                  ))}
                </div>
              </div>

              <Button
                type="submit"
                disabled={isAnalyzing || (!selectedFile && !selectedSample)}
                className="w-full"
              >
                {isAnalyzing ? 'Analyzing...' : 'Run Analysis'}
              </Button>
            </form>
                  </div>
                </ScrollArea>
              </ResizablePanel>
              <ResizableHandle withHandle />
            </>
          )}

          {/* Main Content Area Desktop */}
          <ResizablePanel defaultSize={isInputPanelOpen ? 65 : 100} className="bg-background">
            <ScrollArea className="h-full">
              <div className="p-6 space-y-6">
          {message && (
            <Alert variant={messageType === 'error' ? 'destructive' : 'default'} className={messageType === 'success' ? 'border-success text-success bg-success/10' : ''}>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>{messageType === 'error' ? 'Error' : 'Success'}</AlertTitle>
              <AlertDescription>{message}</AlertDescription>
            </Alert>
          )}

          {/* Removed stats cards per request - kept dashboard focused on pipeline and analysis */}

          {/* Top Row: Recent Scans, Quick Actions, Audit Log */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Recent Scans</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {recentScans.map((scan) => (
                  <div key={scan.id} className="p-3 border rounded-lg bg-card">
                    <div className="flex items-start justify-between mb-2">
                      <span className="font-mono text-sm truncate pr-2">{scan.filename}</span>
                      <Badge variant={getVerdictBadgeVariant(scan.verdict as any)} className="capitalize font-mono">
                        {scan.verdict}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
                      <span>{scan.timestamp}</span>
                      <span>Score: {scan.score}</span>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button variant="outline" className="w-full justify-start gap-3">
                  <Upload className="w-4 h-4 text-accent" />
                  Upload Model
                </Button>
                <Button variant="outline" className="w-full justify-start gap-3">
                  <FileCheck className="w-4 h-4 text-success" />
                  View Reports
                </Button>
                <Button variant="outline" className="w-full justify-start gap-3">
                  <Activity className="w-4 h-4 text-accent" />
                  System Status
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Audit Log</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {auditLog.map((entry) => (
                  <div key={entry.id} className="p-3 border rounded-lg hover:bg-muted/50 transition-colors">
                    <div className="flex items-start gap-3">
                      <Badge variant={getAuditBadgeVariant(entry.status)} className="font-mono uppercase text-[10px]">
                        {entry.status}
                      </Badge>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-1">
                          <span className="text-sm font-medium">{entry.action}</span>
                          <span className="font-mono text-xs text-muted-foreground whitespace-nowrap">{entry.timestamp}</span>
                        </div>
                        {entry.details && (
                          <p className="font-mono text-xs text-muted-foreground mt-1 truncate">{entry.details}</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Pipeline & Current Analysis */}
          <div className="mt-6 space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Analysis Pipeline</CardTitle>
                <Badge variant="secondary" className="font-mono">
                  <Activity className="w-3 h-3 mr-1 inline-block" />
                  {pipelineStages.filter((stage) => stage.status !== 'pending').length}/9 stages
                </Badge>
              </CardHeader>
              <CardContent className="space-y-3">
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
                            <span className="font-mono text-sm">{stage.name}</span>
                            {stage.duration && (
                              <span className="font-mono text-xs text-muted-foreground ml-2">{stage.duration}</span>
                            )}
                          </div>
                          {stage.status === 'running' && stage.progress !== undefined && (
                            <Progress value={stage.progress} className="h-1.5 mt-2" />
                          )}
                        </div>
                      </div>
                      {expandedStage === stage.id ? <ChevronUp className="w-4 h-4 ml-2" /> : <ChevronDown className="w-4 h-4 ml-2" />}
                    </div>
                    {expandedStage === stage.id && stage.message && (
                      <div className="px-4 pb-4 pt-2 border-t border-border bg-muted/30">
                        <p className="font-mono text-sm text-muted-foreground">
                          {stage.message}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Current Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                {backendResult ? (
                  <Alert>
                    <AlertTitle className="text-lg font-semibold">{backendResult.decision_reason}</AlertTitle>
                    <AlertDescription>
                      <p className="font-mono text-sm mt-2 mb-4">Status: <Badge variant="outline">{backendResult.status.replaceAll('_', ' ')}</Badge></p>
                      <div className="grid grid-cols-2 gap-3 font-mono text-sm">
                        <div className="flex items-center gap-2">
                          <Database className="w-4 h-4 text-muted-foreground" />
                          <span>Prediction: {backendResult.prediction || 'N/A'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Lock className="w-4 h-4 text-muted-foreground" />
                          <span>Confidence: {backendResult.confidence ? `${(backendResult.confidence * 100).toFixed(2)}%` : 'N/A'}</span>
                        </div>
                      </div>
                    </AlertDescription>
                  </Alert>
                ) : (
                  <Alert className="bg-warning/10 border-warning/20 text-warning-foreground">
                    <Zap className="h-4 w-4" />
                    <AlertTitle>Pipeline Ready</AlertTitle>
                    <AlertDescription className="font-mono text-sm mt-1">
                      Run analysis to inspect your 9-stage security pipeline output.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </div>
              </div>
            </ScrollArea>
          </ResizablePanel>
        </ResizablePanelGroup>

        {/* Mobile View - Fallback to standard flex flow for narrow screens */}
        <div className="flex-1 flex flex-col lg:hidden overflow-auto p-6 space-y-6">
           <Alert className="bg-muted text-muted-foreground border-border">
             <AlertCircle className="h-4 w-4" />
             <AlertTitle>Notice</AlertTitle>
             <AlertDescription>
               Please use a desktop browser to access the full analysis dashboard interface with input controls.
             </AlertDescription>
           </Alert>
        </div>

      </div>
    </div>
  );
}
