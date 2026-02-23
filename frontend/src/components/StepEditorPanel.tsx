/**
 * StepEditorPanel - Dynamic form for editing step parameters
 *
 * Renders appropriate input controls based on parameter types:
 * - string: TextField
 * - integer/float: TextField with number type
 * - boolean: Switch
 * - credential: Credential selector
 * - file: File path input with browse
 * - selector: TextField for CSS selectors
 * - list/dict: TextArea for JSON input
 * - enum (options): Select dropdown
 */

import { useState } from 'react';
import {
  Box,
  TextField,
  FormControl,
  FormLabel,
  Select,
  MenuItem,
  Switch,
  Typography,
  IconButton,
  InputAdornment,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Folder as FolderIcon,
  Code as CodeIcon,
} from '@mui/icons-material';
import type { StepTypeInfo, StepTypeParameter, CredentialInfo } from '../types/api';
import { HelpTooltip } from './HelpTooltip';

interface StepConfig {
  id: string;
  name: string;
  type: string;
  parameters: Record<string, unknown>;
  timeout?: number;
  retry_count?: number;
  retry_delay?: number;
  on_failure?: string;
}

interface StepEditorPanelProps {
  stepType: StepTypeInfo | null;
  step: StepConfig;
  credentials: CredentialInfo[];
  onChange: (step: StepConfig) => void;
}

export function StepEditorPanel({
  stepType,
  step,
  credentials,
  onChange,
}: StepEditorPanelProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Update parameter value
  const handleParamChange = (name: string, value: unknown) => {
    onChange({
      ...step,
      parameters: {
        ...step.parameters,
        [name]: value,
      },
    });
  };

  // Update step metadata
  const handleMetaChange = (field: keyof StepConfig, value: StepConfig[keyof StepConfig]) => {
    onChange({
      ...step,
      [field]: value,
    });
  };

  if (!stepType) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="text.secondary">
          Select a step type to configure parameters
        </Typography>
      </Box>
    );
  }

  // Separate required and optional parameters
  const requiredParams = stepType.parameters.filter((p) => p.required);
  const optionalParams = stepType.parameters.filter((p) => !p.required);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Step ID and Name */}
      <Box sx={{ display: 'flex', gap: 2 }}>
        <TextField
          label="Step ID"
          value={step.id}
          onChange={(e) => handleMetaChange('id', e.target.value)}
          size="small"
          required
          sx={{ flex: 1 }}
          helperText="Unique identifier (e.g., step1, login_step)"
        />
        <TextField
          label="Step Name"
          value={step.name}
          onChange={(e) => handleMetaChange('name', e.target.value)}
          size="small"
          required
          sx={{ flex: 2 }}
          helperText="Human-readable name"
        />
      </Box>

      {/* Required Parameters */}
      {requiredParams.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
            Required Parameters
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {requiredParams.map((param) => (
              <ParameterInput
                key={param.name}
                parameter={param}
                value={step.parameters[param.name]}
                credentials={credentials}
                onChange={(value) => handleParamChange(param.name, value)}
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Optional Parameters */}
      {optionalParams.length > 0 && (
        <Accordion
          expanded={showAdvanced}
          onChange={(_, expanded) => setShowAdvanced(expanded)}
          sx={{ bgcolor: 'background.default' }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2" sx={{ color: 'text.secondary' }}>
              Optional Parameters ({optionalParams.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {optionalParams.map((param) => (
                <ParameterInput
                  key={param.name}
                  parameter={param}
                  value={step.parameters[param.name] ?? param.default}
                  credentials={credentials}
                  onChange={(value) => handleParamChange(param.name, value)}
                />
              ))}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Step Options (timeout, retry, on_failure) */}
      <Accordion sx={{ bgcolor: 'background.default' }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle2" sx={{ color: 'text.secondary' }}>
            Step Options
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <TextField
              label="Timeout (seconds)"
              type="number"
              value={step.timeout ?? 300}
              onChange={(e) =>
                handleMetaChange('timeout', parseInt(e.target.value) || 300)
              }
              size="small"
              InputProps={{ inputProps: { min: 1, max: 3600 } }}
              helperText="Maximum time to wait for step completion"
            />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="Retry Count"
                type="number"
                value={step.retry_count ?? 0}
                onChange={(e) =>
                  handleMetaChange('retry_count', parseInt(e.target.value) || 0)
                }
                size="small"
                sx={{ flex: 1 }}
                InputProps={{ inputProps: { min: 0, max: 10 } }}
                helperText="Number of retries on failure"
              />
              <TextField
                label="Retry Delay (seconds)"
                type="number"
                value={step.retry_delay ?? 5}
                onChange={(e) =>
                  handleMetaChange('retry_delay', parseInt(e.target.value) || 5)
                }
                size="small"
                sx={{ flex: 1 }}
                InputProps={{ inputProps: { min: 1, max: 60 } }}
                helperText="Delay between retries"
              />
            </Box>
            <FormControl fullWidth size="small">
              <FormLabel sx={{ fontSize: '0.75rem', mb: 0.5 }}>On Failure</FormLabel>
              <Select
                value={step.on_failure ?? 'abort'}
                onChange={(e) => handleMetaChange('on_failure', e.target.value)}
              >
                <MenuItem value="abort">Abort - Stop playbook execution</MenuItem>
                <MenuItem value="continue">Continue - Proceed to next step</MenuItem>
                <MenuItem value="rollback">Rollback - Attempt cleanup</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
}

// Individual parameter input component
function ParameterInput({
  parameter,
  value,
  credentials,
  onChange,
}: {
  parameter: StepTypeParameter;
  value: unknown;
  credentials: CredentialInfo[];
  onChange: (value: unknown) => void;
}) {
  // Handle file browse (Electron native dialog with web fallback)
  const handleBrowseFile = async () => {
    if (window.electronAPI?.openFileDialog) {
      try {
        const result = await window.electronAPI.openFileDialog({
          title: 'Select File',
          properties: ['openFile'],
        });
        if (result && result.length > 0) {
          onChange(result[0]);
        }
      } catch (error) {
        console.error('Failed to open file dialog:', error);
      }
    } else {
      // Web mode: prompt user for file path
      const path = window.prompt('Enter file path:');
      if (path) {
        onChange(path);
      }
    }
  };

  // Render based on parameter type
  const renderInput = () => {
    // If parameter has options, render as select
    if (parameter.options && parameter.options.length > 0) {
      return (
        <Select
          value={value ?? parameter.default ?? ''}
          onChange={(e) => onChange(e.target.value)}
          size="small"
          fullWidth
        >
          {parameter.options.map((option) => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </Select>
      );
    }

    switch (parameter.type) {
      case 'boolean':
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Switch
              checked={value === true || value === 'true'}
              onChange={(e) => onChange(e.target.checked)}
              size="small"
            />
            <Typography variant="body2">
              {value === true || value === 'true' ? 'True' : 'False'}
            </Typography>
          </Box>
        );

      case 'integer':
        return (
          <TextField
            type="number"
            value={value ?? parameter.default ?? ''}
            onChange={(e) => onChange(parseInt(e.target.value) || 0)}
            size="small"
            fullWidth
            InputProps={{ inputProps: { step: 1 } }}
          />
        );

      case 'float':
        return (
          <TextField
            type="number"
            value={value ?? parameter.default ?? ''}
            onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
            size="small"
            fullWidth
            InputProps={{ inputProps: { step: 0.1 } }}
          />
        );

      case 'credential':
        return (
          <Select
            value={value ?? ''}
            onChange={(e) => onChange(e.target.value)}
            size="small"
            fullWidth
            displayEmpty
          >
            <MenuItem value="" disabled>
              Select credential...
            </MenuItem>
            {credentials.map((cred) => (
              <MenuItem key={cred.name} value={cred.name}>
                {cred.name} ({cred.username})
              </MenuItem>
            ))}
          </Select>
        );

      case 'file':
        return (
          <TextField
            value={value ?? ''}
            onChange={(e) => onChange(e.target.value)}
            size="small"
            fullWidth
            placeholder="Enter file path..."
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={handleBrowseFile}
                    edge="end"
                    size="small"
                    title="Browse files"
                    sx={{ color: '#00ff00' }}
                  >
                    <FolderIcon />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
        );

      case 'selector':
        return (
          <TextField
            value={value ?? ''}
            onChange={(e) => onChange(e.target.value)}
            size="small"
            fullWidth
            placeholder="CSS selector (e.g., #id, .class, [data-attr])"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <CodeIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                </InputAdornment>
              ),
            }}
          />
        );

      case 'list':
      case 'dict':
        return (
          <TextField
            value={typeof value === 'string' ? value : JSON.stringify(value ?? (parameter.type === 'list' ? [] : {}), null, 2)}
            onChange={(e) => {
              try {
                onChange(JSON.parse(e.target.value));
              } catch {
                onChange(e.target.value);
              }
            }}
            size="small"
            fullWidth
            multiline
            rows={3}
            placeholder={parameter.type === 'list' ? '["item1", "item2"]' : '{"key": "value"}'}
            sx={{ '& .MuiInputBase-input': { fontFamily: 'monospace', fontSize: '0.8rem' } }}
          />
        );

      case 'string':
      default:
        // Check if this looks like it needs multiline (script parameter)
        if (parameter.name === 'script' || parameter.name === 'code') {
          return (
            <TextField
              value={value ?? parameter.default ?? ''}
              onChange={(e) => onChange(e.target.value)}
              size="small"
              fullWidth
              multiline
              rows={4}
              placeholder={parameter.description}
              sx={{ '& .MuiInputBase-input': { fontFamily: 'monospace', fontSize: '0.8rem' } }}
            />
          );
        }
        return (
          <TextField
            value={value ?? parameter.default ?? ''}
            onChange={(e) => onChange(e.target.value)}
            size="small"
            fullWidth
            placeholder={parameter.description}
          />
        );
    }
  };

  return (
    <FormControl fullWidth>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5, gap: 0.5 }}>
        <FormLabel sx={{ fontSize: '0.8rem' }}>
          {parameter.name}
          {parameter.required && <span style={{ color: '#ff4444' }}> *</span>}
        </FormLabel>
        <Chip
          label={parameter.type}
          size="small"
          sx={{ fontSize: '0.65rem', height: 18 }}
        />
        {parameter.description && (
          <HelpTooltip size="small" content={parameter.description} />
        )}
      </Box>
      {renderInput()}
    </FormControl>
  );
}
