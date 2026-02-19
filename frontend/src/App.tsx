/**
 * Main App component with two-level tab navigation
 *
 * Uses React.lazy for code splitting - heavier pages are loaded on-demand
 * to improve initial bundle size and load performance.
 *
 * Tab state is managed in Zustand (persisted to localStorage).
 * No client-side routing — all navigation is tab-based.
 */

import { useMemo, Suspense, lazy } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CssBaseline, ThemeProvider, createTheme, CircularProgress, Box, Typography } from '@mui/material';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Layout } from './components/Layout';
import { Playbooks } from './pages/Playbooks';
import { Executions } from './pages/Executions';
import { Settings } from './pages/Settings';

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

/**
 * Create MUI theme from the current theme mode.
 */
function createAppTheme(themeMode: 'dark' | 'light') {
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
}

function AppContent() {
  const mainTab = useStore((state) => state.mainTab);
  const playbookSubTab = useStore((state) => state.playbookSubTab);
  const activeExecutionId = useStore((state) => state.activeExecutionId);
  const setExecutionUpdate = useStore((state) => state.setExecutionUpdate);
  const setScreenshotFrame = useStore((state) => state.setScreenshotFrame);
  const themeMode = useStore((state) => state.theme);

  // Create theme based on current mode from store
  const theme = useMemo(() => createAppTheme(themeMode), [themeMode]);

  // Connect to WebSocket for real-time updates (silent - no UI indicators)
  useWebSocket({
    onExecutionUpdate: (update) => setExecutionUpdate(update.execution_id, update),
    onScreenshotFrame: (frame) => setScreenshotFrame(frame.executionId, frame),
  });

  // Render content based on main tab and sub-tab
  const renderContent = () => {
    switch (mainTab) {
      case 'playbooks':
        switch (playbookSubTab) {
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
          case 'active-execution':
            if (!activeExecutionId) {
              return (
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', opacity: 0.5 }}>
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    No Active Execution
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Run a playbook to see execution progress here
                  </Typography>
                </Box>
              );
            }
            return (
              <Suspense fallback={<PageLoader />}>
                <ExecutionDetail executionId={activeExecutionId} />
              </Suspense>
            );
          case 'past-executions':
            return <Executions />;
          default:
            return <Playbooks domainFilter="gateway" />;
        }
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
      case 'udtbuilder':
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', opacity: 0.5 }}>
            <Typography variant="h5" color="text.secondary">UDT Builder — Coming Soon</Typography>
          </Box>
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
      <Layout>
        {renderContent()}
      </Layout>
      {/* Welcome dialog for first-time users */}
      <WelcomeDialog />
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppContent />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
