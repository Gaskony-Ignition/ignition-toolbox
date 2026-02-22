/**
 * LiveBrowserView - Display live browser screenshots from WebSocket stream
 *
 * Shows browser automation in real-time at 2 FPS with click detection
 */

import { useState, useRef } from 'react';
import { Box, Paper, Typography, Chip, Tooltip, Snackbar, Alert } from '@mui/material';
import { Computer as BrowserIcon, Pause as PausedIcon, TouchApp as ClickIcon } from '@mui/icons-material';
import { useStore } from '../store';
import { api } from '../api/client';
import { createLogger } from '../utils/logger';
import { TIMING } from '../config/timing';

const logger = createLogger('LiveBrowserView');

interface LiveBrowserViewProps {
  executionId: string;
}

interface ClickCoordinate {
  x: number;
  y: number;
  timestamp: Date;
}

export function LiveBrowserView({ executionId }: LiveBrowserViewProps) {
  const currentScreenshots = useStore((state) => state.currentScreenshots);
  const screenshot = currentScreenshots.get(executionId);
  const [lastScreenshot, setLastScreenshot] = useState<string | null>(null);
  const [clickCoords, setClickCoords] = useState<ClickCoordinate | null>(null);
  const [showClickIndicator, setShowClickIndicator] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });
  const imgRef = useRef<HTMLImageElement>(null);

  // Persist the last screenshot so it remains visible after execution completes
  if (screenshot && screenshot.screenshot !== lastScreenshot) {
    setLastScreenshot(screenshot.screenshot);
  }

  // Use current screenshot if available, otherwise use last persisted screenshot
  const displayScreenshot = screenshot?.screenshot || lastScreenshot;

  const handleImageClick = async (event: React.MouseEvent<HTMLImageElement>) => {
    if (!imgRef.current) return;

    const rect = imgRef.current.getBoundingClientRect();
    const x = Math.round(event.clientX - rect.left);
    const y = Math.round(event.clientY - rect.top);

    // Calculate relative coordinates (0-1 scale for responsive sizing)
    const relativeX = x / rect.width;
    const relativeY = y / rect.height;

    // Get actual browser coordinates (based on original image size)
    const naturalX = Math.round(relativeX * imgRef.current.naturalWidth);
    const naturalY = Math.round(relativeY * imgRef.current.naturalHeight);

    setClickCoords({
      x: naturalX,
      y: naturalY,
      timestamp: new Date(),
    });

    // Show click indicator animation
    setShowClickIndicator(true);
    setTimeout(() => setShowClickIndicator(false), 1000);

    // Send click to backend to execute in actual browser
    try {
      await api.executions.clickAtCoordinates(executionId, naturalX, naturalY);
      logger.debug(`Browser click executed: (${naturalX}, ${naturalY})`);
      setSnackbar({
        open: true,
        message: `Clicked at (${naturalX}, ${naturalY})`,
        severity: 'success',
      });
    } catch (error) {
      logger.error('Failed to click in browser:', error);
      setSnackbar({
        open: true,
        message: `Failed to click: ${error instanceof Error ? error.message : 'Unknown error'}`,
        severity: 'error',
      });
    }
  };

  return (
    <Paper
      elevation={2}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        bgcolor: 'background.default',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <BrowserIcon color="primary" />
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Live Browser View
        </Typography>
        {clickCoords && (
          <Tooltip title="Last click coordinates">
            <Chip
              icon={<ClickIcon />}
              label={`(${clickCoords.x}, ${clickCoords.y})`}
              size="small"
              color="primary"
              variant="outlined"
            />
          </Tooltip>
        )}
        <Tooltip title="Click on browser to get coordinates">
          <Chip
            label="Interactive"
            size="small"
            color="info"
            variant="outlined"
          />
        </Tooltip>
        <Chip
          label="2 FPS"
          size="small"
          color="success"
          variant="outlined"
        />
      </Box>

      {/* Screenshot Display */}
      <Box
        sx={{
          flexGrow: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          p: 2,
          bgcolor: 'grey.900',
          position: 'relative',
        }}
      >
        {displayScreenshot ? (
          <Box
            sx={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '100%',
              height: '100%',
            }}
          >
            <Tooltip
              title={
                clickCoords
                  ? `Click coordinates: (${clickCoords.x}, ${clickCoords.y})`
                  : 'Click on the browser to get coordinates'
              }
              placement="top"
            >
              <img
                ref={imgRef}
                src={`data:image/jpeg;base64,${displayScreenshot}`}
                alt="Browser screenshot"
                onClick={handleImageClick}
                style={{
                  maxWidth: '100%',
                  maxHeight: '100%',
                  objectFit: 'contain',
                  borderRadius: '4px',
                  cursor: 'crosshair',
                  transition: 'transform 0.1s',
                }}
              />
            </Tooltip>

            {/* Click indicator animation */}
            {showClickIndicator && clickCoords && (
              <Box
                sx={{
                  position: 'absolute',
                  pointerEvents: 'none',
                  animation: 'ripple 1s ease-out',
                  '@keyframes ripple': {
                    '0%': {
                      width: '10px',
                      height: '10px',
                      opacity: 1,
                    },
                    '100%': {
                      width: '100px',
                      height: '100px',
                      opacity: 0,
                    },
                  },
                  border: '3px solid',
                  borderColor: 'primary.main',
                  borderRadius: '50%',
                  transform: 'translate(-50%, -50%)',
                  left: '50%',
                  top: '50%',
                }}
              />
            )}
          </Box>
        ) : (
          <Box
            sx={{
              textAlign: 'center',
              color: 'text.secondary',
            }}
          >
            <PausedIcon sx={{ fontSize: 64, mb: 2, opacity: 0.3 }} />
            <Typography variant="body1">
              Waiting for browser screenshots...
            </Typography>
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              Screenshots will appear here when browser automation starts
            </Typography>
          </Box>
        )}
      </Box>

      {/* Footer with timestamp */}
      {screenshot && (
        <Box
          sx={{
            p: 1,
            borderTop: 1,
            borderColor: 'divider',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Typography variant="caption" color="text.secondary">
            Last updated: {new Date(screenshot.timestamp).toLocaleTimeString()}
          </Typography>
          <Chip
            label="Live"
            size="small"
            color="success"
            sx={{
              animation: 'pulse 2s infinite',
              '@keyframes pulse': {
                '0%, 100%': { opacity: 1 },
                '50%': { opacity: 0.5 },
              },
            }}
          />
        </Box>
      )}

      {/* Snackbar for click feedback */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={TIMING.UI.SNACKBAR}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Paper>
  );
}
