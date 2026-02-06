/**
 * Main App component with tab-based navigation
 *
 * Uses React.lazy for code splitting - heavier pages are loaded on-demand
 * to improve initial bundle size and load performance.
 */

import { useState, useMemo, Suspense, lazy } from 'react';
import { HashRouter, Routes, Route, useParams, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CssBaseline, ThemeProvider, createTheme, CircularProgress, Box } from '@mui/material';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Layout, type DomainTab } from './components/Layout';
import { Playbooks } from './pages/Playbooks';
import { Executions } from './pages/Executions';
import { Settings } from './pages/Settings';
import { FloatingChatButton } from './components/chat/FloatingChatButton';
import { WelcomeDialog } from './components/WelcomeDialog';
import { useWebSocket } from './hooks/useWebSocket';
import { useStore } from './store';

// Lazy-loaded pages for code splitting (reduces initial bundle size)
const Designer = lazy(() => import('./pages/Designer').then(m => ({ default: m.Designer })));
const ExecutionDetail = lazy(() => import('./pages/ExecutionDetail').then(m => ({ default: m.ExecutionDetail })));
const APIExplorer = lazy(() => import('./pages/APIExplorer').then(m => ({ default: m.APIExplorer })));
const StackBuilder = lazy(() => import('./pages/StackBuilder').then(m => ({ default: m.StackBuilder })));

// Loading fallback for lazy-loaded components
function PageLoader() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
      <CircularProgress />
    </Box>
  );
}

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Dark Navy Blue Color Palette (matching CW Dashboard)
const themeColors = {
  dark: {
    background: '#0F172A',      // Navy blue background
    surface: '#1E293B',         // Lighter panel surface
    surfaceVariant: '#1E293B',
    border: '#334155',          // Slate border
    primary: '#3B82F6',         // Blue 500
    secondary: '#1D4ED8',       // Blue 700
    success: '#22C55E',         // Green 500
    warning: '#F59E0B',         // Amber 500
    error: '#EF4444',           // Red 500
    text: '#F8FAFC',            // Slate 50
    textSecondary: '#94A3B8',   // Slate 400
  },
  light: {
    background: '#ffffff',
    surface: '#f6f8fa',
    surfaceVariant: '#f0f3f6',
    border: '#d0d7de',
    primary: '#0969da',
    secondary: '#0550ae',
    success: '#1a7f37',
    warning: '#9a6700',
    error: '#cf222e',
    text: '#24292f',
    textSecondary: '#57606a',
  },
};

function AppContent() {
  const [activeTab, setActiveTab] = useState<DomainTab>('gateway');
  const setExecutionUpdate = useStore((state) => state.setExecutionUpdate);
  const setScreenshotFrame = useStore((state) => state.setScreenshotFrame);
  const themeMode = useStore((state) => state.theme);

  // Create theme based on current mode from store
  const theme = useMemo(() => {
    const colors = themeColors[themeMode];

    return createTheme({
      palette: {
        mode: themeMode,
        primary: {
          main: colors.primary,
          light: themeMode === 'dark' ? '#79c0ff' : '#54aeff',
          dark: colors.secondary,
        },
        secondary: {
          main: colors.secondary,
        },
        success: {
          main: colors.success,
        },
        warning: {
          main: colors.warning,
        },
        error: {
          main: colors.error,
        },
        background: {
          default: colors.background,
          paper: colors.surface,
        },
        text: {
          primary: colors.text,
          secondary: colors.textSecondary,
        },
        divider: colors.border,
      },
      components: {
        MuiCard: {
          styleOverrides: {
            root: {
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          },
        },
      },
    });
  }, [themeMode]);

  // Connect to WebSocket for real-time updates (silent - no UI indicators)
  useWebSocket({
    onExecutionUpdate: (update) => setExecutionUpdate(update.execution_id, update),
    onScreenshotFrame: (frame) => setScreenshotFrame(frame.executionId, frame),
  });

  // Render content based on active tab
  // Lazy-loaded components are wrapped in Suspense with a loading fallback
  const renderContent = () => {
    switch (activeTab) {
      case 'gateway':
        return <Playbooks domainFilter="gateway" />;
      case 'designer':
        return (
          <Suspense fallback={<PageLoader />}>
            <Designer />
          </Suspense>
        );
      case 'perspective':
        return <Playbooks domainFilter="perspective" />;
      case 'executions':
        return <Executions />;
      case 'api':
        return (
          <Suspense fallback={<PageLoader />}>
            <APIExplorer />
          </Suspense>
        );
      case 'stackbuilder':
        return (
          <Suspense fallback={<PageLoader />}>
            <StackBuilder />
          </Suspense>
        );
      case 'settings':
        return <Settings />;
      default:
        return <Playbooks domainFilter="gateway" />;
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Layout activeTab={activeTab} onTabChange={setActiveTab}>
        {renderContent()}
      </Layout>
      {/* Floating chat button */}
      <FloatingChatButton />
      {/* Welcome dialog for first-time users */}
      <WelcomeDialog />
    </ThemeProvider>
  );
}

// Wrapper for execution detail that handles routing
function ExecutionDetailWrapper() {
  const { executionId } = useParams<{ executionId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<DomainTab>('gateway');
  const setExecutionUpdate = useStore((state) => state.setExecutionUpdate);
  const setScreenshotFrame = useStore((state) => state.setScreenshotFrame);
  const themeMode = useStore((state) => state.theme);

  // WebSocket for real-time updates
  useWebSocket({
    onExecutionUpdate: (update) => setExecutionUpdate(update.execution_id, update),
    onScreenshotFrame: (frame) => setScreenshotFrame(frame.executionId, frame),
  });

  // Create theme
  const theme = useMemo(() => {
    const colors = themeColors[themeMode];
    return createTheme({
      palette: {
        mode: themeMode,
        primary: { main: colors.primary, light: themeMode === 'dark' ? '#79c0ff' : '#54aeff', dark: colors.secondary },
        secondary: { main: colors.secondary },
        success: { main: colors.success },
        warning: { main: colors.warning },
        error: { main: colors.error },
        background: { default: colors.background, paper: colors.surface },
        text: { primary: colors.text, secondary: colors.textSecondary },
        divider: colors.border,
      },
    });
  }, [themeMode]);

  // Handle tab change - navigate back to main app
  const handleTabChange = (tab: DomainTab) => {
    setActiveTab(tab);
    navigate('/');
  };

  if (!executionId) {
    navigate('/');
    return null;
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Layout activeTab={activeTab} onTabChange={handleTabChange}>
        <Suspense fallback={<PageLoader />}>
          <ExecutionDetail />
        </Suspense>
      </Layout>
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <HashRouter>
          <Routes>
            <Route path="/" element={<AppContent />} />
            <Route path="/executions/:executionId" element={<ExecutionDetailWrapper />} />
          </Routes>
        </HashRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
