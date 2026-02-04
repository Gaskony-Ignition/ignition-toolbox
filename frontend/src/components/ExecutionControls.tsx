/**
 * ExecutionControls - Control buttons for playbook execution
 *
 * Provides skip and cancel controls
 */

import { useState, useRef } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  SkipNext as SkipIcon,
  Cancel as CancelIcon,
  PlayArrow as ResumeIcon,
  Pause as PauseIcon,
} from '@mui/icons-material';
import { api } from '../api/client';
import { createLogger } from '../utils/logger';

const logger = createLogger('ExecutionControls');

interface ExecutionControlsProps {
  executionId: string;
  status: string;
  disabled?: boolean;
  debugMode?: boolean;
}

export function ExecutionControls({
  executionId,
  status,
  disabled = false,
  debugMode: _debugMode = false,
}: ExecutionControlsProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const cancelInProgressRef = useRef(false);

  const handleSkip = async () => {
    try {
      setLoading('skip');
      await api.executions.skip(executionId);
    } catch (error) {
      logger.error('Failed to skip step:', error);
    } finally {
      setLoading(null);
    }
  };


  const handleCancel = async () => {
    logger.debug('Cancel button clicked, executionId:', executionId);

    // Prevent duplicate cancel requests
    if (cancelInProgressRef.current) {
      logger.debug('Cancel already in progress, ignoring duplicate click');
      return;
    }

    // Mark cancel as in progress using ref (persists across re-renders)
    cancelInProgressRef.current = true;
    setLoading('cancel');

    try {
      logger.debug('Sending cancel request...');
      const response = await api.executions.cancel(executionId);
      logger.debug('Cancel request succeeded:', response);
    } catch (error) {
      logger.error('Failed to cancel execution:', error);
      alert(`Failed to cancel execution: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      logger.debug('Cancel request complete, clearing loading state');
      cancelInProgressRef.current = false;
      setLoading(null);
    }
  };

  const handlePause = async () => {
    try {
      setLoading('pause');
      await api.executions.pause(executionId);
    } catch (error) {
      logger.error('Failed to pause execution:', error);
    } finally {
      setLoading(null);
    }
  };

  const handleResume = async () => {
    try {
      setLoading('resume');
      await api.executions.resume(executionId);
    } catch (error) {
      logger.error('Failed to resume execution:', error);
    } finally {
      setLoading(null);
    }
  };

  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const isActive = isRunning || isPaused;  // Execution is active if running or paused
  const isDisabled = disabled || !isActive;  // Only disable if not active at all

  return (
    <Box sx={{ display: 'flex', gap: 1 }}>
      <ButtonGroup variant="outlined" size="small">
        {/* Skip Button */}
        <Tooltip title="Skip current step">
          <span>
            <Button
              onClick={handleSkip}
              disabled={isDisabled || loading !== null}
              startIcon={
                loading === 'skip' ? (
                  <CircularProgress size={16} />
                ) : (
                  <SkipIcon />
                )
              }
            >
              Skip
            </Button>
          </span>
        </Tooltip>

        {/* Pause/Resume Button */}
        {isPaused ? (
          <Tooltip title="Resume execution">
            <span>
              <Button
                onClick={handleResume}
                disabled={loading !== null}
                color="success"
                startIcon={
                  loading === 'resume' ? (
                    <CircularProgress size={16} />
                  ) : (
                    <ResumeIcon />
                  )
                }
              >
                Resume
              </Button>
            </span>
          </Tooltip>
        ) : (
          <Tooltip title="Pause execution">
            <span>
              <Button
                onClick={handlePause}
                disabled={isDisabled || loading !== null}
                startIcon={
                  loading === 'pause' ? (
                    <CircularProgress size={16} />
                  ) : (
                    <PauseIcon />
                  )
                }
              >
                Pause
              </Button>
            </span>
          </Tooltip>
        )}

        {/* Cancel Button */}
        <Tooltip title="Cancel execution">
          <span>
            <Button
              onClick={() => {
                logger.debug('Cancel button onClick fired', {
                  isDisabled,
                  loading,
                  cancelInProgress: cancelInProgressRef.current,
                  buttonDisabled: isDisabled || loading !== null || cancelInProgressRef.current
                });
                handleCancel();
              }}
              disabled={isDisabled || loading !== null || cancelInProgressRef.current}
              color="error"
              startIcon={
                loading === 'cancel' ? (
                  <CircularProgress size={16} />
                ) : (
                  <CancelIcon />
                )
              }
            >
              Cancel
            </Button>
          </span>
        </Tooltip>
      </ButtonGroup>
    </Box>
  );
}
