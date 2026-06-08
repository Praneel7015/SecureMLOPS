import { useState, useEffect } from 'react';
import { LandingPage } from './components/LandingPage';
import { Login } from './components/Login';
import { Signup } from './components/Signup';
import { Dashboard } from './components/Dashboard';
import { Settings } from './components/Settings';
import {
  apiBootstrap,
  apiLogin,
  apiLogout,
  apiRegister,
  SampleImage,
  SupportedModel,
} from './api';

type View = 'loading' | 'landing' | 'login' | 'signup' | 'dashboard' | 'settings';

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
      setCurrentView((prev) =>
        boot.authenticated ? 'dashboard' : prev === 'loading' ? 'landing' : prev,
      );
      setAppError('');
      return boot.authenticated;
    } catch (_error) {
      setCurrentView((prev) => (prev === 'loading' ? 'landing' : prev));
      setAppError('Could not reach the Echelon backend. Ensure Flask is running on port 5000.');
      return false;
    }
  };

  const handleLogin = async (identifier: string, password: string) => {
    const result = await apiLogin(identifier, password);
    if (!result.success) {
      return { success: false, message: result.message || 'Invalid credentials.' };
    }

    setUsername(result.username || identifier);
    await loadBootstrap();
    setCurrentView('dashboard');
    return { success: true, message: result.message || 'Login successful.' };
  };

  const handleSignup = async (payload: {
    name: string;
    email: string;
    password: string;
  }) => {
    const result = await apiRegister(payload);
    if (!result.success) {
      return { success: false, message: result.message || 'Could not create your account.' };
    }

    // Backend signs the user in on successful registration.
    setUsername(result.username || payload.email);
    await loadBootstrap();
    setCurrentView('dashboard');
    return { success: true, message: result.message || 'Welcome to Echelon.' };
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

  const handleNavigateToSettings = () => setCurrentView('settings');
  const handleBackToDashboard = () => setCurrentView('dashboard');

  if (currentView === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <span className="eyebrow text-muted-foreground animate-pulse">Initializing Echelon…</span>
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

      {currentView === 'landing' && (
        <LandingPage
          onNavigateLogin={() => setCurrentView('login')}
          onNavigateSignup={() => setCurrentView('signup')}
        />
      )}
      {currentView === 'login' && (
        <Login
          onLogin={handleLogin}
          onNavigateSignup={() => setCurrentView('signup')}
          onNavigateHome={() => setCurrentView('landing')}
        />
      )}
      {currentView === 'signup' && (
        <Signup
          onSignup={handleSignup}
          onNavigateLogin={() => setCurrentView('login')}
          onNavigateHome={() => setCurrentView('landing')}
        />
      )}
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
