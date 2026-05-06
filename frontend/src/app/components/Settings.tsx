import { Shield, ArrowLeft, Save, Bell, Database, Lock, Zap, AlertTriangle, Clock, Server } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { ThemeToggle } from './ThemeToggle';

interface SettingsProps {
  username: string;
  onLogout: () => void | Promise<void>;
  onBack: () => void;
}

export function Settings({ username, onLogout, onBack }: SettingsProps) {
  const [scanDepth, setScanDepth] = useState('medium');
  const [enableBehavioralAnalysis, setEnableBehavioralAnalysis] = useState(true);
  const [enableSignatureScanning, setEnableSignatureScanning] = useState(true);
  const [enableAnomalyDetection, setEnableAnomalyDetection] = useState(true);
  const [enableRealtimeMonitoring, setEnableRealtimeMonitoring] = useState(false);
  const [maxFileSize, setMaxFileSize] = useState('100');
  const [retentionDays, setRetentionDays] = useState('30');
  const [threatThreshold, setThreatThreshold] = useState('medium');
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [slackNotifications, setSlackNotifications] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setSaveMessage('Settings saved locally (dummy persistence). You can wire this to your real endpoint later.');
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <Shield className="w-6 h-6 text-accent" />
              <span className="font-mono">SecureMLOPS Settings · {username}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <button
              type="button"
              onClick={() => void onLogout()}
              className="px-3 py-2 border border-border rounded-lg hover:bg-muted transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>

      {/* Settings Form */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Grid Layout for Settings Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* General Settings */}
            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-accent/10 rounded-lg">
                  <Server className="w-5 h-5 text-accent" />
                </div>
                <h2 className="text-foreground">General Settings</h2>
              </div>

              <div className="space-y-4">
                <div>
                  <label htmlFor="scanDepth" className="block mb-2 text-foreground">
                    Scan Depth
                  </label>
                  <select
                    id="scanDepth"
                    name="scanDepth"
                    value={scanDepth}
                    onChange={(e) => setScanDepth(e.target.value)}
                    className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
                  >
                    <option value="quick">Quick Scan</option>
                    <option value="medium">Medium Scan</option>
                    <option value="deep">Deep Scan</option>
                    <option value="thorough">Thorough Scan</option>
                  </select>
                  <p className="mt-1 font-mono text-muted-foreground">
                    Controls the depth of model analysis
                  </p>
                </div>

                <div>
                  <label htmlFor="maxFileSize" className="block mb-2 text-foreground">
                    Max File Size (MB)
                  </label>
                  <input
                    type="number"
                    id="maxFileSize"
                    name="maxFileSize"
                    value={maxFileSize}
                    onChange={(e) => setMaxFileSize(e.target.value)}
                    min="1"
                    max="1000"
                    className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
                  />
                  <p className="mt-1 font-mono text-muted-foreground">
                    Maximum allowed image file size
                  </p>
                </div>

                <div>
                  <label htmlFor="retentionDays" className="block mb-2 text-foreground">
                    Log Retention (Days)
                  </label>
                  <input
                    type="number"
                    id="retentionDays"
                    name="retentionDays"
                    value={retentionDays}
                    onChange={(e) => setRetentionDays(e.target.value)}
                    min="7"
                    max="365"
                    className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
                  />
                  <p className="mt-1 font-mono text-muted-foreground">
                    How long to keep analysis logs
                  </p>
                </div>
              </div>
            </div>

            {/* Security Settings */}
            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-destructive/10 rounded-lg">
                  <Lock className="w-5 h-5 text-destructive" />
                </div>
                <h2 className="text-foreground">Security Settings</h2>
              </div>

              <div className="space-y-4">
                <div>
                  <label htmlFor="threatThreshold" className="block mb-2 text-foreground">
                    Threat Threshold
                  </label>
                  <select
                    id="threatThreshold"
                    name="threatThreshold"
                    value={threatThreshold}
                    onChange={(e) => setThreatThreshold(e.target.value)}
                    className="w-full px-4 py-2.5 bg-input-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring text-foreground"
                  >
                    <option value="low">Low (More Alerts)</option>
                    <option value="medium">Medium (Balanced)</option>
                    <option value="high">High (Critical Only)</option>
                  </select>
                  <p className="mt-1 font-mono text-muted-foreground">
                    Minimum threat level to flag
                  </p>
                </div>

                <div className="p-4 bg-warning/10 border border-warning/20 rounded-lg">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-warning mt-0.5" />
                    <div>
                      <h4 className="text-foreground mb-1">Automatic Quarantine</h4>
                      <p className="font-mono text-muted-foreground">
                        High-risk models are automatically isolated
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-success/10 border border-success/20 rounded-lg">
                  <div className="flex items-start gap-3">
                    <Zap className="w-5 h-5 text-success mt-0.5" />
                    <div>
                      <h4 className="text-foreground mb-1">Real-time Protection</h4>
                      <p className="font-mono text-muted-foreground">
                        Continuous monitoring enabled
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Analysis Features - Full Width */}
          <div className="bg-card rounded-lg border border-border p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-accent/10 rounded-lg">
                <Zap className="w-5 h-5 text-accent" />
              </div>
              <h2 className="text-foreground">Analysis Features</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="flex items-center justify-between p-4 border border-border rounded-lg cursor-pointer hover:bg-muted transition-colors">
                <div className="flex items-start gap-3">
                  <Database className="w-5 h-5 text-accent mt-0.5" />
                  <div>
                    <div className="text-foreground">Behavioral Analysis</div>
                    <p className="font-mono text-muted-foreground mt-1">
                      Analyze model runtime behavior
                    </p>
                  </div>
                </div>
                <input
                  type="checkbox"
                  name="enableBehavioralAnalysis"
                  checked={enableBehavioralAnalysis}
                  onChange={(e) => setEnableBehavioralAnalysis(e.target.checked)}
                  className="w-5 h-5 rounded border-border text-accent focus:ring-accent"
                />
              </label>

              <label className="flex items-center justify-between p-4 border border-border rounded-lg cursor-pointer hover:bg-muted transition-colors">
                <div className="flex items-start gap-3">
                  <Shield className="w-5 h-5 text-success mt-0.5" />
                  <div>
                    <div className="text-foreground">Signature Scanning</div>
                    <p className="font-mono text-muted-foreground mt-1">
                      Check against known malicious patterns
                    </p>
                  </div>
                </div>
                <input
                  type="checkbox"
                  name="enableSignatureScanning"
                  checked={enableSignatureScanning}
                  onChange={(e) => setEnableSignatureScanning(e.target.checked)}
                  className="w-5 h-5 rounded border-border text-accent focus:ring-accent"
                />
              </label>

              <label className="flex items-center justify-between p-4 border border-border rounded-lg cursor-pointer hover:bg-muted transition-colors">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-warning mt-0.5" />
                  <div>
                    <div className="text-foreground">Anomaly Detection</div>
                    <p className="font-mono text-muted-foreground mt-1">
                      Detect unusual patterns and behaviors
                    </p>
                  </div>
                </div>
                <input
                  type="checkbox"
                  name="enableAnomalyDetection"
                  checked={enableAnomalyDetection}
                  onChange={(e) => setEnableAnomalyDetection(e.target.checked)}
                  className="w-5 h-5 rounded border-border text-accent focus:ring-accent"
                />
              </label>

              <label className="flex items-center justify-between p-4 border border-border rounded-lg cursor-pointer hover:bg-muted transition-colors">
                <div className="flex items-start gap-3">
                  <Clock className="w-5 h-5 text-accent mt-0.5" />
                  <div>
                    <div className="text-foreground">Real-time Monitoring</div>
                    <p className="font-mono text-muted-foreground mt-1">
                      Continuous background scanning
                    </p>
                  </div>
                </div>
                <input
                  type="checkbox"
                  name="enableRealtimeMonitoring"
                  checked={enableRealtimeMonitoring}
                  onChange={(e) => setEnableRealtimeMonitoring(e.target.checked)}
                  className="w-5 h-5 rounded border-border text-accent focus:ring-accent"
                />
              </label>
            </div>
          </div>

          {/* Notifications */}
          <div className="bg-card rounded-lg border border-border p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-accent/10 rounded-lg">
                <Bell className="w-5 h-5 text-accent" />
              </div>
              <h2 className="text-foreground">Notifications</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="flex items-center justify-between p-4 border border-border rounded-lg cursor-pointer hover:bg-muted transition-colors">
                <div>
                  <div className="text-foreground">Email Notifications</div>
                  <p className="font-mono text-muted-foreground mt-1">
                    Receive alerts via email
                  </p>
                </div>
                <input
                  type="checkbox"
                  name="emailNotifications"
                  checked={emailNotifications}
                  onChange={(e) => setEmailNotifications(e.target.checked)}
                  className="w-5 h-5 rounded border-border text-accent focus:ring-accent"
                />
              </label>

              <label className="flex items-center justify-between p-4 border border-border rounded-lg cursor-pointer hover:bg-muted transition-colors">
                <div>
                  <div className="text-foreground">Slack Integration</div>
                  <p className="font-mono text-muted-foreground mt-1">
                    Post alerts to Slack channel
                  </p>
                </div>
                <input
                  type="checkbox"
                  name="slackNotifications"
                  checked={slackNotifications}
                  onChange={(e) => setSlackNotifications(e.target.checked)}
                  className="w-5 h-5 rounded border-border text-accent focus:ring-accent"
                />
              </label>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end gap-4">
            <button
              type="button"
              onClick={onBack}
              className="px-6 py-3 border border-border rounded-lg hover:bg-muted transition-colors text-foreground"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-2 px-6 py-3 bg-accent hover:bg-accent-600 text-accent-foreground rounded-lg transition-colors"
            >
              <Save className="w-5 h-5" />
              <span>Save Settings</span>
            </button>
          </div>

          {saveMessage && (
            <div className="rounded-lg border border-success/30 bg-success/10 px-4 py-3 text-success">
              {saveMessage}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
