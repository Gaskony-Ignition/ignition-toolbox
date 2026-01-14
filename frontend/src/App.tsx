/**
 * Main App component with routing and providers
 */

import { useMemo, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Layout } from './components/Layout';
import { Playbooks } from './pages/Playbooks';
import { Executions } from './pages/Executions';
import { ExecutionDetail } from './pages/ExecutionDetail';
import { Credentials } from './pages/Credentials';
import { About } from './pages/About';
import { useWebSocket } from './hooks/useWebSocket';
import { useStore } from './store';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Warp Terminal Color Palette
const warpColors = {
  dark: {
    background: '#01050d',
    surface: '#161b22',
    surfaceVariant: '#0d1117',
    border: '#30363d',
    primary: '#58a6ff',
    secondary: '#1f6feb',
    success: '#3fb950',
    warning: '#d29922',
    error: '#f85149',
    text: '#c9d1d9',
    textSecondary: '#8b949e',
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
  const setWSConnected = useStore((state) => state.setWSConnected);
  const setWSConnectionStatus = useStore((state) => state.setWSConnectionStatus);
  const setExecutionUpdate = useStore((state) => state.setExecutionUpdate);
  const setScreenshotFrame = useStore((state) => state.setScreenshotFrame);
  const themeMode = useStore((state) => state.theme);

  // Create theme based on current mode from store
  const theme = useMemo(() => {
    const colors = warpColors[themeMode];

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
        MuiAppBar: {
          styleOverrides: {
            root: {
              backgroundColor: colors.surface,
              borderBottom: `1px solid ${colors.border}`,
            },
          },
        },
        MuiDrawer: {
          styleOverrides: {
            paper: {
              backgroundColor: colors.surfaceVariant,
              borderRight: `1px solid ${colors.border}`,
            },
          },
        },
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

  // Connect to WebSocket for real-time updates
  const { connectionStatus } = useWebSocket({
    onOpen: () => {
      setWSConnected(true);
      setWSConnectionStatus('connected');
    },
    onClose: () => {
      setWSConnected(false);
      setWSConnectionStatus('disconnected');
    },
    onExecutionUpdate: (update) => setExecutionUpdate(update.execution_id, update),
    onScreenshotFrame: (frame) => setScreenshotFrame(frame.executionId, frame),
  });

  // Sync WebSocket connection status to store
  // This ensures status updates even when onOpen/onClose aren't called (during reconnects)
  useEffect(() => {
    setWSConnectionStatus(connectionStatus);
  }, [connectionStatus, setWSConnectionStatus]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Playbooks />} />
          <Route path="executions" element={<Executions />} />
          <Route path="executions/:executionId" element={<ExecutionDetail />} />
          <Route path="credentials" element={<Credentials />} />
          <Route path="about" element={<About />} />
        </Route>
      </Routes>
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
