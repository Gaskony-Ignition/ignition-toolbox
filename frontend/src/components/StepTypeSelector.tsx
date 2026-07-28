/**
 * StepTypeSelector - Grouped dropdown for selecting step types
 *
 * Organizes step types by domain (gateway, browser, etc.)
 * with descriptions for each step type.
 */

import { useMemo } from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  ListSubheader,
  Typography,
  Box,
} from '@mui/material';
import type { StepTypeInfo } from '../types/api';

interface StepTypeSelectorProps {
  stepTypes: StepTypeInfo[];
  value: string;
  onChange: (stepType: string) => void;
  disabled?: boolean;
}

// Domain display names and icons
const DOMAIN_CONFIG: Record<string, { label: string; icon: string }> = {
  gateway: { label: 'Gateway', icon: '🔧' },
  browser: { label: 'Browser', icon: '🌐' },
  perspective: { label: 'Perspective', icon: '📱' },
  utility: { label: 'Utility', icon: '⚙️' },
  playbook: { label: 'Playbook', icon: '📋' },
  fat: { label: 'FAT Reporting', icon: '📊' },
};

export function StepTypeSelector({
  stepTypes,
  value,
  onChange,
  disabled = false,
}: StepTypeSelectorProps) {
  // Group step types by domain
  const groupedStepTypes = useMemo(() => {
    const groups: Record<string, StepTypeInfo[]> = {};

    stepTypes.forEach((stepType) => {
      if (!groups[stepType.domain]) {
        groups[stepType.domain] = [];
      }
      groups[stepType.domain].push(stepType);
    });

    // Sort groups by domain order
    const domainOrder = ['gateway', 'browser', 'perspective', 'utility', 'playbook', 'fat'];
    const sortedGroups: [string, StepTypeInfo[]][] = [];

    domainOrder.forEach((domain) => {
      if (groups[domain]) {
        sortedGroups.push([domain, groups[domain]]);
      }
    });

    // Add any domains not in the predefined order
    Object.keys(groups).forEach((domain) => {
      if (!domainOrder.includes(domain)) {
        sortedGroups.push([domain, groups[domain]]);
      }
    });

    return sortedGroups;
  }, [stepTypes]);

  // Get selected step type info for display
  const selectedStepType = stepTypes.find((st) => st.type === value);

  return (
    <FormControl fullWidth disabled={disabled}>
      <InputLabel id="step-type-label">Step Type</InputLabel>
      <Select
        labelId="step-type-label"
        value={value}
        label="Step Type"
        onChange={(e) => onChange(e.target.value)}
        MenuProps={{
          PaperProps: {
            sx: { maxHeight: 400 },
          },
        }}
      >
        {groupedStepTypes.map(([domain, types]) => {
          const config = DOMAIN_CONFIG[domain] || { label: domain, icon: '📦' };
          return [
            <ListSubheader
              key={`header-${domain}`}
              sx={{
                bgcolor: 'background.paper',
                fontWeight: 600,
                fontSize: '0.85rem',
                lineHeight: '32px',
              }}
            >
              {config.icon} {config.label}
            </ListSubheader>,
            ...types.map((stepType) => (
              <MenuItem key={stepType.type} value={stepType.type}>
                <Box sx={{ display: 'flex', flexDirection: 'column', py: 0.5 }}>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {stepType.type}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ fontSize: '0.7rem' }}
                  >
                    {stepType.description}
                  </Typography>
                </Box>
              </MenuItem>
            )),
          ];
        })}
      </Select>

      {/* Show description of selected step type below */}
      {selectedStepType && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ mt: 0.5, display: 'block' }}
        >
          {selectedStepType.description}
        </Typography>
      )}
    </FormControl>
  );
}
