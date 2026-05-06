import { useState, useEffect } from 'react';
import { LandingPage } from './components/LandingPage';
import { Login } from './components/Login';
import { Dashboard } from './components/Dashboard';
import { SettingsComponent as Settings } from './components/Settings';
import { ActivityPage } from './components/Activity';
import { InputPage } from './components/InputPage';
import { apiBootstrap, apiLogin, apiLogout, SampleImage } from './api';

type View = 'loading' | 'login' | 'landing' | 'dashboard' | 'settings' | 'activity' | 'input';

export default function App() {
  const [currentView, setCurrentView] = useState<View>('loading');
  const [username, setUsername] = useState<string | null>(null);
  const [sampleImages, setSampleImages] = useState<SampleImage[]>([]);
  const [appError, setAppError] = useState<string>('');

  useEffect(() => {
    const theme = localStorage.getItem('sml-theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    }

    void loadBootstrap();
  }, []);

  const loadBootstrap = async () => {
    try {
      const boot = await apiBootstrap();
      setSampleImages(boot.sample_images || []);
      setUsername(boot.username);
      setCurrentView(boot.authenticated ? 'dashboard' : 'landing');
      setAppError('');
    } catch (_error) {
      setCurrentView('landing');
      setAppError('Could not reach backend bootstrap API. Ensure Flask is running on port 5000.');
    }
  };

  const handleLogin = async (nextUsername: string, password: string) => {
    const result = await apiLogin(nextUsername, password);
    if (!result.success) {
      return { success: false, message: result.message || 'Invalid credentials.' };
    }

    setUsername(result.username || nextUsername);
    await loadBootstrap();
    setCurrentView('dashboard');
    return { success: true, message: result.message || 'Login successful.' };
  };

  const handleLogout = async () => {
    try {
      await apiLogout();
    } catch (_error) {
      // ignore logout transport errors and reset local state anyway
    }
    setUsername(null);
    setCurrentView('landing');
  };

  const handleNavigateToSettings = () => {
    setCurrentView('settings');
  };

  const handleNavigateToActivity = () => {
    setCurrentView('activity');
  };

  const handleNavigateToInput = () => {
    setCurrentView('input');
  };

  const handleBackToDashboard = () => {
    setCurrentView('dashboard');
  };

    if (currentView === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        Loading Axion...
      </div>
    );
  }

  return (
    <div className="size-full">
      {appError && (
        <div className="mx-4 mt-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-destructive">
          {appError}
        </div>
      )}

      {currentView === 'landing' && <LandingPage onNavigateLogin={() => setCurrentView('login')} />}
      {currentView === 'login' && <Login onLogin={handleLogin} onBack={() => setCurrentView('landing')} />}
      {currentView === 'dashboard' && (
        <Dashboard
          username={username || 'user'}
          sampleImages={sampleImages}
          onLogout={handleLogout}
          onNavigateToSettings={handleNavigateToSettings}
          onNavigateToInput={handleNavigateToInput}
          onNavigateToActivity={handleNavigateToActivity}
        />
      )}
      {currentView === 'activity' && (
        <ActivityPage recentScans={[]} auditLog={[]} />
      )}
      {currentView === 'input' && (
        <InputPage samples={sampleImages.map((i) => ({ value: i.name, label: i.name, url: i.url }))} />
      )}
      {currentView === 'settings' && (
        <Settings
          onBack={handleBackToDashboard}
          username={username || 'user'}
          onLogout={handleLogout}
        />
      )}
    </div>
  );
}
