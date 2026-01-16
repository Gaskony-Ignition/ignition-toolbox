/**
 * ParameterInput - Single parameter input component for playbook execution
 * Reduces complexity of PlaybookExecutionDialog by extracting parameter rendering logic
 */

import { useState } from 'react';
import {
  FormControl,
  FormLabel,
  Select,
  MenuItem,
  TextField,
  Typography,
  IconButton,
  InputAdornment,
  Box,
  Switch,
} from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import type { ParameterInfo, CredentialInfo } from '../types/api';
import FolderBrowserDialog from './FolderBrowserDialog';

// Check if running in Electron
const isElectron = (): boolean => {
  return typeof window !== 'undefined' && !!window.electronAPI;
};

interface ParameterInputProps {
  parameter: ParameterInfo;
  value: string;
  credentials?: CredentialInfo[];
  onChange: (name: string, value: string) => void;
}

export function ParameterInput({
  parameter,
  value,
  credentials = [],
  onChange,
}: ParameterInputProps) {
  const [folderDialogOpen, setFolderDialogOpen] = useState(false);

  const handleChange = (newValue: string) => {
    onChange(parameter.name, newValue);
  };

  // Detect if parameter is path-related
  const isPathParameter = parameter.name.toLowerCase().includes('path') ||
                          parameter.name.toLowerCase().includes('directory') ||
                          parameter.name.toLowerCase().includes('folder') ||
                          parameter.name.toLowerCase().includes('dir');

  // Handle folder browse - use native Electron dialog if available
  const handleBrowseFolder = async () => {
    if (isElectron() && window.electronAPI) {
      try {
        const result = await window.electronAPI.openFileDialog({
          title: 'Select Folder',
          properties: ['openDirectory'],
        });
        if (result && result.length > 0) {
          handleChange(result[0]);
        }
      } catch (error) {
        console.error('Failed to open folder dialog:', error);
        // Fall back to custom dialog
        setFolderDialogOpen(true);
      }
    } else {
      // Use custom dialog for web/non-Electron
      setFolderDialogOpen(true);
    }
  };

  return (
    <FormControl fullWidth>
      <FormLabel htmlFor={`param-${parameter.name}`} sx={{ mb: 0.5, fontSize: '0.875rem' }}>
        {parameter.name}
        {parameter.required && ' *'}
      </FormLabel>

      {parameter.type === 'credential' ? (
        <Select
          id={`param-${parameter.name}`}
          value={value || ''}
          onChange={(e) => handleChange(e.target.value)}
          displayEmpty
          size="small"
          inputProps={{
            'aria-label': `${parameter.name} credential`,
          }}
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
      ) : parameter.type === 'boolean' ? (
        (() => {
          // Determine labels based on parameter name
          const isModuleTypeParam = parameter.name.toLowerCase().includes('module_type') ||
                                     parameter.name.toLowerCase().includes('unsigned');
          const leftLabel = isModuleTypeParam ? 'Signed' : 'False';
          const rightLabel = isModuleTypeParam ? 'Unsigned' : 'True';
          const isChecked = value === 'true';

          return (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 1 }}>
              <Typography variant="body2" sx={{ minWidth: '80px', color: isChecked ? 'text.secondary' : '#00ff00' }}>
                {leftLabel}
              </Typography>
              <Switch
                checked={isChecked}
                onChange={(e) => handleChange(e.target.checked ? 'true' : 'false')}
                sx={{
                  '& .MuiSwitch-switchBase.Mui-checked': {
                    color: '#00ff00',
                  },
                  '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                    backgroundColor: '#00ff00',
                  },
                }}
              />
              <Typography variant="body2" sx={{ minWidth: '80px', color: isChecked ? '#00ff00' : 'text.secondary' }}>
                {rightLabel}
              </Typography>
            </Box>
          );
        })()
      ) : parameter.type === 'file' ? (
        <TextField
          id={`param-${parameter.name}`}
          value={value || ''}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Enter file path..."
          size="small"
          fullWidth
          inputProps={{
            'aria-label': `${parameter.name} file path`,
          }}
        />
      ) : (
        <>
          <TextField
            id={`param-${parameter.name}`}
            value={value || ''}
            onChange={(e) => handleChange(e.target.value)}
            placeholder={parameter.default || `Enter ${parameter.name}...`}
            size="small"
            fullWidth
            inputProps={{
              'aria-label': parameter.name,
            }}
            InputProps={isPathParameter ? {
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={handleBrowseFolder}
                    edge="end"
                    size="small"
                    sx={{ color: '#00ff00' }}
                    title="Browse folders"
                  >
                    <FolderIcon />
                  </IconButton>
                </InputAdornment>
              ),
            } : undefined}
          />

          {isPathParameter && (
            <FolderBrowserDialog
              open={folderDialogOpen}
              onClose={() => setFolderDialogOpen(false)}
              onSelect={(selectedPath) => handleChange(selectedPath)}
              initialPath={value || '/modules'}
            />
          )}
        </>
      )}

      {parameter.description && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
          {parameter.description}
        </Typography>
      )}
    </FormControl>
  );
}
