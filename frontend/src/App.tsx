/**
 * Main App component with tab-based navigation
 */

import { useState, useMemo } from 'react';
import { HashRouter, Routes, Route, useParams, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Layout, type DomainTab } from './components/Layout';
import { Playbooks } from './pages/Playbooks';
import { Designer } from './pages/Designer';
import { Executions } from './pages/Executions';
import { ExecutionDetail } from './pages/ExecutionDetail';
import { Settings } from './pages/Settings';
import { APIExplorer } from './pages/APIExplorer';
import { StackBuilder } from './pages/StackBuilder';
import { FloatingChatButton } from './components/chat/FloatingChatButton';
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
  const renderContent = () => {
    switch (activeTab) {
      case 'gateway':
        return <Playbooks domainFilter="gateway" />;
      case 'designer':
        return <Designer />;
      case 'perspective':
        return <Playbooks domainFilter="perspective" />;
      case 'executions':
        return <Executions />;
      case 'api':
        return <APIExplorer />;
      case 'stackbuilder':
        return <StackBuilder />;
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
        <ExecutionDetail />
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
