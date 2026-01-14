/**
 * Error Fallback UI - Displayed when an error is caught by ErrorBoundary
 */

import { Box, Button, Typography, Alert, Paper } from '@mui/material';
import { ErrorOutline as ErrorIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import type { ErrorInfo } from 'react';

interface ErrorFallbackProps {
  error: Error | null;
  errorInfo: ErrorInfo | null;
  onReset: () => void;
}

export function ErrorFallback({ error, errorInfo, onReset }: ErrorFallbackProps) {
  const handleReload = () => {
    window.location.reload();
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        p: 3,
        bgcolor: 'background.default',
      }}
    >
      <Paper
        elevation={3}
        sx={{
          p: 4,
          maxWidth: 600,
          width: '100%',
          textAlign: 'center',
        }}
      >
        <ErrorIcon
          sx={{
            fontSize: 64,
            color: 'error.main',
            mb: 2,
          }}
        />

        <Typography variant="h4" gutterBottom>
          Something went wrong
        </Typography>

        <Typography variant="body1" color="text.secondary" paragraph>
          The application encountered an unexpected error. You can try reloading the page or going back to start over.
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mt: 2, mb: 2, textAlign: 'left' }}>
            <Typography variant="subtitle2" gutterBottom>
              Error: {error.message}
            </Typography>
            {errorInfo && (
              <Typography variant="caption" component="pre" sx={{ mt: 1, overflow: 'auto' }}>
                {errorInfo.componentStack}
              </Typography>
            )}
          </Alert>
        )}

        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mt: 3 }}>
          <Button
            variant="outlined"
            onClick={onReset}
            startIcon={<RefreshIcon />}
          >
            Try Again
          </Button>

          <Button
            variant="contained"
            onClick={handleReload}
            startIcon={<RefreshIcon />}
          >
            Reload Page
          </Button>
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ mt: 3, display: 'block' }}>
          If this problem persists, please contact support or check the browser console for more details.
        </Typography>
      </Paper>
    </Box>
  );
}
