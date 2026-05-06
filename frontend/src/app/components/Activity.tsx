import { Activity, Upload, FileCheck } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';

interface ActivityProps {
  recentScans: any[];
  auditLog: any[];
  onBack?: () => void;
}

export function ActivityPage({ recentScans, auditLog }: ActivityProps) {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto space-y-6">
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
                    <Badge className="capitalize font-mono">{scan.verdict}</Badge>
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
                  <div className="flex flex-col">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{entry.action}</span>
                      <span className="font-mono text-xs text-muted-foreground">{entry.timestamp}</span>
                    </div>
                    {entry.details && <div className="font-mono text-xs text-muted-foreground mt-1">{entry.details}</div>}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
