/**
 * ExecutionCard - Display execution with expandable step details
 */

import { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Chip,
  Box,
  IconButton,
  Collapse,
  LinearProgress,
  Button,
  Stack,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Pause as PauseIcon,
  PlayArrow as ResumeIcon,
  SkipNext as SkipIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';
import type { ExecutionStatusResponse } from '../types/api';
import { getStatusChipColor, getStatusIcon } from '../constants/executionStatus';

interface ExecutionCardProps {
  execution: ExecutionStatusResponse;
  onPause?: (executionId: string) => void;
  onResume?: (executionId: string) => void;
  onSkip?: (executionId: string) => void;
  onCancel?: (executionId: string) => void;
}

export function ExecutionCard({
  execution,
  onPause,
  onResume,
  onSkip,
  onCancel,
}: ExecutionCardProps) {
  const [expanded, setExpanded] = useState(false);

  const progress = execution.total_steps > 0 && execution.current_step_index != null
    ? (execution.current_step_index / execution.total_steps) * 100
    : 0;

  const handleExpand = () => {
    setExpanded(!expanded);
  };

  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
  };

  const getDuration = () => {
    if (!execution.started_at) return 'N/A';
    const start = new Date(execution.started_at).getTime();
    const end = execution.completed_at
      ? new Date(execution.completed_at).getTime()
      : Date.now();
    const seconds = Math.floor((end - start) / 1000);

    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6">{execution.playbook_name}</Typography>
            <Chip
              label={execution.status}
              color={getStatusChipColor(execution.status)}
              size="small"
              icon={getStatusIcon(execution.status)}
            />
          </Box>
          <IconButton
            onClick={handleExpand}
            aria-label={expanded ? 'Collapse execution details' : 'Expand execution details'}
            sx={{
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.3s',
            }}
          >
            <ExpandMoreIcon />
          </IconButton>
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
          ID: {execution.execution_id.substring(0, 8)}...
        </Typography>

        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="body2" color="text.secondary">
              Progress: {execution.current_step_index} / {execution.total_steps} steps
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {Math.round(progress)}%
            </Typography>
          </Box>
          <LinearProgress variant="determinate" value={progress} />
        </Box>

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Typography variant="caption" color="text.secondary">
            Started: {formatTimestamp(execution.started_at)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Duration: {getDuration()}
          </Typography>
          {execution.completed_at && (
            <Typography variant="caption" color="text.secondary">
              Completed: {formatTimestamp(execution.completed_at)}
            </Typography>
          )}
        </Box>

        {execution.error && (
          <Box sx={{ mt: 2, p: 1, bgcolor: 'error.dark', borderRadius: 1 }}>
            <Typography variant="body2" color="error.contrastText">
              Error: {execution.error}
            </Typography>
          </Box>
        )}

        <Collapse in={expanded} timeout="auto" unmountOnExit>
          <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
            <Typography variant="subtitle2" gutterBottom>
              Step Results
            </Typography>
            {execution.step_results && execution.step_results.length > 0 ? (
              <Stack spacing={1}>
                {execution.step_results.map((step, index) => (
                  <Box
                    key={step.step_id || index}
                    sx={{
                      p: 1,
                      bgcolor: 'background.paper',
                      borderLeft: 3,
                      borderColor:
                        step.status === 'completed'
                          ? 'success.main'
                          : step.status === 'failed'
                          ? 'error.main'
                          : step.status === 'running'
                          ? 'primary.main'
                          : 'grey.500',
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" fontWeight="medium">
                        {step.step_name || step.step_id}
                      </Typography>
                      <Chip
                        label={step.status}
                        size="small"
                        color={getStatusChipColor(step.status)}
                      />
                    </Box>
                    {step.error && (
                      <Typography variant="caption" color="error" sx={{ display: 'block', mt: 0.5 }}>
                        {step.error}
                      </Typography>
                    )}
                    {step.started_at && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                        Started: {formatTimestamp(step.started_at)}
                      </Typography>
                    )}
                  </Box>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No step results yet
              </Typography>
            )}
          </Box>
        </Collapse>
      </CardContent>

      <CardActions sx={{ justifyContent: 'flex-end', gap: 1 }}>
        {execution.status === 'running' && (
          <>
            <Button
              size="small"
              startIcon={<PauseIcon />}
              onClick={() => onPause?.(execution.execution_id)}
              aria-label="Pause execution"
            >
              Pause
            </Button>
            <Button
              size="small"
              startIcon={<SkipIcon />}
              onClick={() => onSkip?.(execution.execution_id)}
              aria-label="Skip current step"
            >
              Skip
            </Button>
            <Button
              size="small"
              color="error"
              startIcon={<CancelIcon />}
              onClick={() => onCancel?.(execution.execution_id)}
              aria-label="Cancel execution"
            >
              Cancel
            </Button>
          </>
        )}
        {execution.status === 'paused' && (
          <>
            <Button
              size="small"
              startIcon={<ResumeIcon />}
              onClick={() => onResume?.(execution.execution_id)}
              aria-label="Resume execution"
            >
              Resume
            </Button>
            <Button
              size="small"
              startIcon={<SkipIcon />}
              onClick={() => onSkip?.(execution.execution_id)}
              aria-label="Skip current step"
            >
              Skip
            </Button>
            <Button
              size="small"
              color="error"
              startIcon={<CancelIcon />}
              onClick={() => onCancel?.(execution.execution_id)}
              aria-label="Cancel execution"
            >
              Cancel
            </Button>
          </>
        )}
      </CardActions>
    </Card>
  );
}
