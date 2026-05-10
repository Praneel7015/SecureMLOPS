import { useState, useEffect } from 'react';
import { Login } from './components/Login';
import { Dashboard } from './components/Dashboard';
import { Settings } from './components/Settings';
import { apiBootstrap, apiLogin, apiLogout, SampleImage, SupportedModel } from './api';

type View = 'loading' | 'login' | 'dashboard' | 'settings';

export default function App() {
  const [currentView, setCurrentView] = useState<View>('loading');
  const [username, setUsername] = useState<string | null>(null);
  const [sampleImages, setSampleImages] = useState<SampleImage[]>([]);
  const [supportedModels, setSupportedModels] = useState<SupportedModel[]>([]);
  const [maxDatasetUploadMb, setMaxDatasetUploadMb] = useState(600);
  const [maxModelUploadMb, setMaxModelUploadMb] = useState(200);
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
  setSupportedModels(boot.supported_models || []);
  setMaxDatasetUploadMb(boot.max_dataset_upload_mb || 600);
  setMaxModelUploadMb(boot.max_model_upload_mb || 200);
      setCurrentView(boot.authenticated ? 'dashboard' : 'login');
      setAppError('');
    } catch (_error) {
      setCurrentView('login');
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
    setCurrentView('login');
  };

  const handleNavigateToSettings = () => {
    setCurrentView('settings');
  };

  const handleBackToDashboard = () => {
    setCurrentView('dashboard');
  };

  if (currentView === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        Loading SecureMLOPS UI...
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

      {currentView === 'login' && <Login onLogin={handleLogin} />}
      {currentView === 'dashboard' && (
        <Dashboard
          username={username || 'user'}
          sampleImages={sampleImages}
          supportedModels={supportedModels}
          maxDatasetUploadMb={maxDatasetUploadMb}
          maxModelUploadMb={maxModelUploadMb}
          onLogout={handleLogout}
          onNavigateToSettings={handleNavigateToSettings}
        />
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