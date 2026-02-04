/**
 * ActionBlock - Component for rendering and executing Toolbox Assistant actions
 *
 * Detects `assistant-action` code blocks in AI responses and provides
 * interactive buttons to execute them.
 */

import { useState } from 'react';
import {
  Box,
  Button,
  Paper,
  Typography,
  CircularProgress,
  Collapse,
  Alert,
  IconButton,
  Chip,
} from '@mui/material';
import {
  PlayArrow as ExecuteIcon,
  Check as SuccessIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { api } from '../../api/client';
import { createLogger } from '../../utils/logger';

const logger = createLogger('ActionBlock');

/**
 * Parsed action from an assistant-action block
 */
export interface ParsedAction {
  action: string;
  params: Record<string, unknown>;
  raw: string;
}

/**
 * Action execution result
 */
interface ActionResult {
  success: boolean;
  result: unknown;
  message?: string;
  error?: string;
}

/**
 * Props for ActionBlock component
 */
interface ActionBlockProps {
  action: ParsedAction;
  onActionComplete?: (action: string, result: ActionResult) => void;
}

/**
 * Actions that require user confirmation before execution
 */
const CONFIRMATION_ACTIONS = [
  'execute_playbook',
  'control_execution',
];

/**
 * Format action name for display
 */
function formatActionName(action: string): string {
  return action
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Format result for display
 */
function formatResult(result: unknown): string {
  if (result === null || result === undefined) {
    return 'No data';
  }
  if (typeof result === 'string') {
    return result;
  }
  try {
    return JSON.stringify(result, null, 2);
  } catch {
    return String(result);
  }
}

/**
 * ActionBlock component
 */
export function ActionBlock({ action, onActionComplete }: ActionBlockProps) {
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<ActionResult | null>(null);
  const [showResult, setShowResult] = useState(true);
  const [confirmed, setConfirmed] = useState(false);

  const requiresConfirmation = CONFIRMATION_ACTIONS.includes(action.action);
  const canExecute = !requiresConfirmation || confirmed;

  const handleExecute = async () => {
    if (!canExecute) {
      setConfirmed(true);
      return;
    }

    setIsExecuting(true);
    setResult(null);

    try {
      logger.info(`Executing action: ${action.action}`, action.params);
      const response = await api.assistant.execute(action.action, action.params);
      setResult(response);
      setShowResult(true);

      if (onActionComplete) {
        onActionComplete(action.action, response);
      }
    } catch (error) {
      const errorResult: ActionResult = {
        success: false,
        result: null,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
      setResult(errorResult);
      setShowResult(true);

      if (onActionComplete) {
        onActionComplete(action.action, errorResult);
      }
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <Paper
      elevation={0}
      sx={{
        mt: 1,
        mb: 1,
        border: '1px solid',
        borderColor: result
          ? result.success
            ? 'success.main'
            : 'error.main'
          : 'primary.main',
        borderRadius: 1,
        overflow: 'hidden',
      }}
    >
      {/* Action header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 1,
          bgcolor: result
            ? result.success
              ? 'success.dark'
              : 'error.dark'
            : 'primary.dark',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            label={formatActionName(action.action)}
            size="small"
            sx={{
              bgcolor: 'rgba(255,255,255,0.1)',
              color: 'white',
              fontWeight: 'bold',
            }}
          />
          {requiresConfirmation && !result && (
            <Chip
              icon={<WarningIcon sx={{ fontSize: 14 }} />}
              label="Requires Confirmation"
              size="small"
              color="warning"
              variant="outlined"
              sx={{ borderColor: 'rgba(255,255,255,0.5)', color: 'white' }}
            />
          )}
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {result && (
            <>
              {result.success ? (
                <SuccessIcon sx={{ color: 'white', fontSize: 20 }} />
              ) : (
                <ErrorIcon sx={{ color: 'white', fontSize: 20 }} />
              )}
              <IconButton
                size="small"
                onClick={() => setShowResult(!showResult)}
                sx={{ color: 'white' }}
              >
                {showResult ? <CollapseIcon /> : <ExpandIcon />}
              </IconButton>
            </>
          )}
        </Box>
      </Box>

      {/* Action parameters */}
      {Object.keys(action.params).length > 0 && (
        <Box sx={{ p: 1, bgcolor: 'background.default', borderBottom: '1px solid', borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
            Parameters:
          </Typography>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 0.5,
              fontSize: '0.75rem',
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {JSON.stringify(action.params, null, 2)}
          </Box>
        </Box>
      )}

      {/* Execute button or confirmation */}
      {!result && (
        <Box sx={{ p: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
          {requiresConfirmation && !confirmed ? (
            <>
              <Alert severity="warning" sx={{ flex: 1, py: 0 }}>
                <Typography variant="body2">
                  This action will modify the system. Click to confirm.
                </Typography>
              </Alert>
              <Button
                variant="contained"
                color="warning"
                size="small"
                onClick={() => setConfirmed(true)}
              >
                Confirm
              </Button>
            </>
          ) : (
            <Button
              variant="contained"
              color="primary"
              size="small"
              startIcon={isExecuting ? <CircularProgress size={16} color="inherit" /> : <ExecuteIcon />}
              onClick={handleExecute}
              disabled={isExecuting}
              sx={{ minWidth: 100 }}
            >
              {isExecuting ? 'Running...' : 'Execute'}
            </Button>
          )}
        </Box>
      )}

      {/* Result display */}
      <Collapse in={showResult && !!result}>
        <Box sx={{ p: 1, bgcolor: 'background.paper' }}>
          {result?.success ? (
            <>
              {result.message && (
                <Alert severity="success" sx={{ mb: 1 }}>
                  {result.message}
                </Alert>
              )}
              <Box
                component="pre"
                sx={{
                  m: 0,
                  p: 1,
                  fontSize: '0.75rem',
                  fontFamily: 'monospace',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  bgcolor: 'background.default',
                  borderRadius: 1,
                  maxHeight: 300,
                  overflow: 'auto',
                }}
              >
                {formatResult(result.result)}
              </Box>
            </>
          ) : (
            <Alert severity="error">
              {result?.error || 'Action failed'}
            </Alert>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
}

/**
 * Parse assistant-action blocks from message content
 */
export function parseActionBlocks(content: string): ParsedAction[] {
  const actions: ParsedAction[] = [];

  // Match ```assistant-action ... ``` blocks (also support legacy clawdbot-action)
  const actionBlockRegex = /```(?:assistant|clawdbot)-action\s*\n?([\s\S]*?)```/g;
  let match;

  while ((match = actionBlockRegex.exec(content)) !== null) {
    const raw = match[1].trim();
    try {
      const parsed = JSON.parse(raw);
      if (parsed.action && typeof parsed.action === 'string') {
        actions.push({
          action: parsed.action,
          params: parsed.params || {},
          raw,
        });
      }
    } catch (error) {
      logger.warn('Failed to parse action block:', raw, error);
    }
  }

  return actions;
}

/**
 * Remove assistant-action blocks from content for clean display
 */
export function removeActionBlocks(content: string): string {
  return content.replace(/```(?:assistant|clawdbot)-action\s*\n?[\s\S]*?```/g, '').trim();
}
