/**
 * Composer wizard — "Basics" step: type name, description, naming style,
 * and the instance parameter list ({ParamName} refs used elsewhere in the
 * composition).
 */

import {
  Box,
  Stack,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  IconButton,
  Button,
  Paper,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import type { UdtComposition, UdtCompositionParameter, UdtDataType } from '../../types/api';
import { DATA_TYPES, NAMING_STYLES } from './udtConstants';

interface BasicsStepProps {
  composition: UdtComposition;
  onChange: (updater: (c: UdtComposition) => UdtComposition) => void;
}

export function BasicsStep({ composition, onChange }: BasicsStepProps) {
  const updateParameter = (index: number, patch: Partial<UdtCompositionParameter>) => {
    onChange((c) => ({
      ...c,
      parameters: c.parameters.map((p, i) => (i === index ? { ...p, ...patch } : p)),
    }));
  };

  const addParameter = () => {
    onChange((c) => ({
      ...c,
      parameters: [...c.parameters, { name: '', data_type: 'String', default_value: '', description: '' }],
    }));
  };

  const removeParameter = (index: number) => {
    onChange((c) => ({ ...c, parameters: c.parameters.filter((_, i) => i !== index) }));
  };

  return (
    <Stack spacing={3} sx={{ maxWidth: 700 }}>
      <TextField
        label="Type name"
        value={composition.type_name}
        onChange={(e) => onChange((c) => ({ ...c, type_name: e.target.value }))}
        required
        fullWidth
        size="small"
        helperText="The UDT's type name, e.g. ConveyorMotor."
        slotProps={{ htmlInput: { 'aria-label': 'Type name' } }}
      />

      <TextField
        label="Description"
        value={composition.description ?? ''}
        onChange={(e) => onChange((c) => ({ ...c, description: e.target.value }))}
        fullWidth
        size="small"
        multiline
        minRows={2}
      />

      <FormControl size="small" fullWidth sx={{ maxWidth: 260 }}>
        <InputLabel id="udt-naming-style-label">Naming style</InputLabel>
        <Select
          labelId="udt-naming-style-label"
          label="Naming style"
          value={composition.naming_style}
          onChange={(e) => onChange((c) => ({ ...c, naming_style: e.target.value as UdtComposition['naming_style'] }))}
        >
          {NAMING_STYLES.map((style) => (
            <MenuItem key={style} value={style}>
              {style}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2">Parameters</Typography>
          <Button size="small" startIcon={<AddIcon />} onClick={addParameter} data-testid="add-parameter">
            Add parameter
          </Button>
        </Box>

        {composition.parameters.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No parameters yet. Parameters are instance inputs referenced as {'{ParamName}'} elsewhere
            in the composition (e.g. an OPC item path).
          </Typography>
        )}

        <Stack spacing={1.5}>
          {composition.parameters.map((parameter, index) => (
            <Paper key={index} variant="outlined" sx={{ p: 1.5 }}>
              <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                <TextField
                  label="Name"
                  value={parameter.name}
                  onChange={(e) => updateParameter(index, { name: e.target.value })}
                  size="small"
                  sx={{ flex: '1 1 160px' }}
                  slotProps={{ htmlInput: { 'aria-label': `Parameter ${index + 1} name` } }}
                />
                <FormControl size="small" sx={{ flex: '1 1 130px' }}>
                  <InputLabel id={`param-type-${index}`}>Data type</InputLabel>
                  <Select
                    labelId={`param-type-${index}`}
                    label="Data type"
                    value={parameter.data_type}
                    onChange={(e) => updateParameter(index, { data_type: e.target.value as UdtDataType })}
                  >
                    {DATA_TYPES.map((dt) => (
                      <MenuItem key={dt} value={dt}>
                        {dt}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  label="Default value"
                  value={parameter.default_value ?? ''}
                  onChange={(e) => updateParameter(index, { default_value: e.target.value })}
                  size="small"
                  sx={{ flex: '1 1 140px' }}
                />
                <TextField
                  label="Description"
                  value={parameter.description ?? ''}
                  onChange={(e) => updateParameter(index, { description: e.target.value })}
                  size="small"
                  sx={{ flex: '2 1 200px' }}
                />
                <IconButton
                  size="small"
                  onClick={() => removeParameter(index)}
                  aria-label={`Remove parameter ${index + 1}`}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            </Paper>
          ))}
        </Stack>
      </Box>
    </Stack>
  );
}
