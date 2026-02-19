/**
 * TimeoutSettings - Collapsible section for configuring per-playbook timeout overrides
 */

import { useState } from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Box,
  TextField,
  Typography,
  InputAdornment,
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon, Timer as TimerIcon } from '@mui/icons-material';
import { HelpTooltip } from './HelpTooltip';
import type { TimeoutOverrides } from '../types/api';

interface TimeoutSettingsProps {
  timeoutOverrides: TimeoutOverrides;
  onChange: (overrides: TimeoutOverrides) => void;
  relevantTimeouts?: string[];
}

// Default timeout values
const DEFAULTS = {
  gateway_restart: 120,    // seconds
  module_install: 300,     // seconds
  designer_launch: 60,     // seconds
  browser_operation: 30000 // milliseconds
};

export function TimeoutSettings({ timeoutOverrides, onChange, relevantTimeouts }: TimeoutSettingsProps) {
  const [expanded, setExpanded] = useState(false);

  const handleChange = (key: keyof TimeoutOverrides, value: string) => {
    const numValue = value === '' ? undefined : parseInt(value, 10);
    // Only update if it's a valid positive number or empty (undefined)
    if (value === '' || (!isNaN(numValue!) && numValue! > 0)) {
      onChange({
        ...timeoutOverrides,
        [key]: numValue,
      });
    }
  };

  const getValue = (key: keyof TimeoutOverrides): string => {
    const value = timeoutOverrides[key];
    return value !== undefined ? String(value) : '';
  };

  // Check if any timeout has been customized
  const hasCustomTimeouts = Object.values(timeoutOverrides).some(v => v !== undefined);

  // If relevantTimeouts is provided and empty, no timeouts apply to this playbook
  if (relevantTimeouts !== undefined && relevantTimeouts !== null && relevantTimeouts.length === 0) {
    return null;
  }

  return (
    <Accordion
      expanded={expanded}
      onChange={(_, isExpanded) => setExpanded(isExpanded)}
      sx={{
        backgroundColor: 'transparent',
        backgroundImage: 'none',
        boxShadow: 'none',
        '&:before': { display: 'none' },
        '&.Mui-expanded': { margin: 0 },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          minHeight: 40,
          padding: 0,
          '& .MuiAccordionSummary-content': {
            margin: 0,
            alignItems: 'center',
            gap: 1,
          },
        }}
      >
        <TimerIcon fontSize="small" sx={{ color: 'text.secondary' }} />
        <Typography variant="subtitle2" color="text.secondary">
          Timeout Settings
          {hasCustomTimeouts && (
            <Typography
              component="span"
              variant="caption"
              sx={{ ml: 1, color: 'success.main' }}
            >
              (customized)
            </Typography>
          )}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ padding: '8px 0 16px 0' }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {(relevantTimeouts == null || relevantTimeouts.includes('gateway_restart')) && (
            <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
              <TextField
                label={`Gateway Restart (default: ${DEFAULTS.gateway_restart}s)`}
                type="number"
                size="small"
                fullWidth
                value={getValue('gateway_restart')}
                onChange={(e) => handleChange('gateway_restart', e.target.value)}
                helperText="Time to wait for gateway to restart and become ready"
                InputProps={{
                  endAdornment: <InputAdornment position="end">seconds</InputAdornment>,
                  inputProps: { min: 1 },
                }}
              />
              <HelpTooltip content="How long to wait after triggering a gateway restart before timing out. Increase this if your gateway takes longer than 2 minutes to restart (e.g., large projects or slow hardware)." />
            </Box>
          )}
          {(relevantTimeouts == null || relevantTimeouts.includes('module_install')) && (
            <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
              <TextField
                label={`Module Installation (default: ${DEFAULTS.module_install}s)`}
                type="number"
                size="small"
                fullWidth
                value={getValue('module_install')}
                onChange={(e) => handleChange('module_install', e.target.value)}
                helperText="Time to wait for module installation to complete"
                InputProps={{
                  endAdornment: <InputAdornment position="end">seconds</InputAdornment>,
                  inputProps: { min: 1 },
                }}
              />
              <HelpTooltip content="Maximum time allowed for module upload and installation. Large modules or slow systems may need more time. The default 5 minutes is usually sufficient." />
            </Box>
          )}
          {(relevantTimeouts == null || relevantTimeouts.includes('designer_launch')) && (
            <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
              <TextField
                label={`Designer Launch (default: ${DEFAULTS.designer_launch}s)`}
                type="number"
                size="small"
                fullWidth
                value={getValue('designer_launch')}
                onChange={(e) => handleChange('designer_launch', e.target.value)}
                helperText="Time to wait for Designer windows to appear"
                InputProps={{
                  endAdornment: <InputAdornment position="end">seconds</InputAdornment>,
                  inputProps: { min: 1 },
                }}
              />
              <HelpTooltip content="How long to wait for the Designer login window and project selection screens to appear. Increase this if the Designer takes longer to start up on your system (e.g., slow hardware or large gateway)." />
            </Box>
          )}
          {(relevantTimeouts == null || relevantTimeouts.includes('browser_operation')) && (
            <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
              <TextField
                label={`Browser Operations (default: ${DEFAULTS.browser_operation}ms)`}
                type="number"
                size="small"
                fullWidth
                value={getValue('browser_operation')}
                onChange={(e) => handleChange('browser_operation', e.target.value)}
                helperText="Time for browser clicks, fills, and waits"
                InputProps={{
                  endAdornment: <InputAdornment position="end">ms</InputAdornment>,
                  inputProps: { min: 100 },
                }}
              />
              <HelpTooltip content="Timeout for individual browser actions like clicking buttons, filling forms, or waiting for elements. Increase for slow networks or when pages take longer to load. Value is in milliseconds (1000ms = 1 second)." />
            </Box>
          )}
          <Typography variant="caption" color="text.secondary" sx={{ mt: -1 }}>
            Leave empty to use default values shown in labels.
          </Typography>
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}
