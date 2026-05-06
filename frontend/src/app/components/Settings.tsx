import { Shield, ArrowLeft, Save, Bell, Database, Lock, Zap, AlertTriangle, Clock, Server } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { ThemeToggle } from './ThemeToggle';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

interface SettingsProps {
  username: string;
  onLogout: () => void | Promise<void>;
  onBack: () => void;
}

export function SettingsComponent({ username, onLogout, onBack }: SettingsProps) {
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
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={onBack}
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2">
              <Shield className="w-6 h-6 text-accent" />
              <span className="font-mono font-medium">Axion Settings · {username}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Button
              variant="outline"
              onClick={() => void onLogout()}
            >
              Sign out
            </Button>
          </div>
        </div>
      </div>

      {/* Settings Form */}
      <div className="max-w-6xl mx-auto w-full px-6 py-8 flex-1">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Grid Layout for Settings Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* General Settings */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-accent/10 rounded-lg">
                    <Server className="w-5 h-5 text-accent" />
                  </div>
                  <CardTitle>General Settings</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="scanDepth">Scan Depth</Label>
                  <Select value={scanDepth} onValueChange={setScanDepth}>
                    <SelectTrigger id="scanDepth">
                      <SelectValue placeholder="Select scan depth" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="quick">Quick Scan</SelectItem>
                      <SelectItem value="medium">Medium Scan</SelectItem>
                      <SelectItem value="deep">Deep Scan</SelectItem>
                      <SelectItem value="thorough">Thorough Scan</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="font-mono text-sm text-muted-foreground">Controls the depth of model analysis</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="maxFileSize">Max File Size (MB)</Label>
                  <Input
                    type="number"
                    id="maxFileSize"
                    value={maxFileSize}
                    onChange={(e) => setMaxFileSize(e.target.value)}
                    min="1"
                    max="1000"
                  />
                  <p className="font-mono text-sm text-muted-foreground">Maximum allowed image file size</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="retentionDays">Log Retention (Days)</Label>
                  <Input
                    type="number"
                    id="retentionDays"
                    value={retentionDays}
                    onChange={(e) => setRetentionDays(e.target.value)}
                    min="7"
                    max="365"
                  />
                  <p className="font-mono text-sm text-muted-foreground">How long to keep analysis logs</p>
                </div>
              </CardContent>
            </Card>

            {/* Security Settings */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-destructive/10 rounded-lg">
                    <Lock className="w-5 h-5 text-destructive" />
                  </div>
                  <CardTitle>Security Settings</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="threatThreshold">Threat Threshold</Label>
                  <Select value={threatThreshold} onValueChange={setThreatThreshold}>
                    <SelectTrigger id="threatThreshold">
                      <SelectValue placeholder="Select threat threshold" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low (More Alerts)</SelectItem>
                      <SelectItem value="medium">Medium (Balanced)</SelectItem>
                      <SelectItem value="high">High (Critical Only)</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="font-mono text-sm text-muted-foreground">Minimum threat level to flag</p>
                </div>

                <div className="p-4 bg-warning/10 border border-warning/20 rounded-lg flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-warning mt-0.5" />
                  <div>
                    <h4 className="text-foreground font-medium mb-1">Automatic Quarantine</h4>
                    <p className="font-mono text-sm text-muted-foreground">High-risk models are automatically isolated</p>
                  </div>
                </div>

                <div className="p-4 bg-success/10 border border-success/20 rounded-lg flex items-start gap-3">
                  <Zap className="w-5 h-5 text-success mt-0.5" />
                  <div>
                    <h4 className="text-foreground font-medium mb-1">Real-time Protection</h4>
                    <p className="font-mono text-sm text-muted-foreground">Continuous monitoring enabled</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Analysis Features */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-accent/10 rounded-lg">
                  <Zap className="w-5 h-5 text-accent" />
                </div>
                <CardTitle>Analysis Features</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                  <div className="flex items-start gap-3">
                    <Database className="w-5 h-5 text-accent mt-0.5" />
                    <div>
                      <Label htmlFor="enableBehavioralAnalysis" className="text-base">Behavioral Analysis</Label>
                      <p className="font-mono text-sm text-muted-foreground mt-1">Analyze model runtime behavior</p>
                    </div>
                  </div>
                  <Switch
                    id="enableBehavioralAnalysis"
                    checked={enableBehavioralAnalysis}
                    onCheckedChange={setEnableBehavioralAnalysis}
                  />
                </div>

                <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                  <div className="flex items-start gap-3">
                    <Shield className="w-5 h-5 text-success mt-0.5" />
                    <div>
                      <Label htmlFor="enableSignatureScanning" className="text-base">Signature Scanning</Label>
                      <p className="font-mono text-sm text-muted-foreground mt-1">Check against known malicious patterns</p>
                    </div>
                  </div>
                  <Switch
                    id="enableSignatureScanning"
                    checked={enableSignatureScanning}
                    onCheckedChange={setEnableSignatureScanning}
                  />
                </div>

                <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-warning mt-0.5" />
                    <div>
                      <Label htmlFor="enableAnomalyDetection" className="text-base">Anomaly Detection</Label>
                      <p className="font-mono text-sm text-muted-foreground mt-1">Detect unusual patterns and behaviors</p>
                    </div>
                  </div>
                  <Switch
                    id="enableAnomalyDetection"
                    checked={enableAnomalyDetection}
                    onCheckedChange={setEnableAnomalyDetection}
                  />
                </div>

                <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                  <div className="flex items-start gap-3">
                    <Clock className="w-5 h-5 text-accent mt-0.5" />
                    <div>
                      <Label htmlFor="enableRealtimeMonitoring" className="text-base">Real-time Monitoring</Label>
                      <p className="font-mono text-sm text-muted-foreground mt-1">Continuous background scanning</p>
                    </div>
                  </div>
                  <Switch
                    id="enableRealtimeMonitoring"
                    checked={enableRealtimeMonitoring}
                    onCheckedChange={setEnableRealtimeMonitoring}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Notifications */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-accent/10 rounded-lg">
                  <Bell className="w-5 h-5 text-accent" />
                </div>
                <CardTitle>Notifications</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                  <div>
                    <Label htmlFor="emailNotifications" className="text-base">Email Notifications</Label>
                    <p className="font-mono text-sm text-muted-foreground mt-1">Receive alerts via email</p>
                  </div>
                  <Switch
                    id="emailNotifications"
                    checked={emailNotifications}
                    onCheckedChange={setEmailNotifications}
                  />
                </div>

                <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                  <div>
                    <Label htmlFor="slackNotifications" className="text-base">Slack Integration</Label>
                    <p className="font-mono text-sm text-muted-foreground mt-1">Post alerts to Slack channel</p>
                  </div>
                  <Switch
                    id="slackNotifications"
                    checked={slackNotifications}
                    onCheckedChange={setSlackNotifications}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Save Button */}
          <div className="flex justify-end gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={onBack}
            >
              Cancel
            </Button>
            <Button type="submit" className="gap-2">
              <Save className="w-5 h-5" />
              Save Settings
            </Button>
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

