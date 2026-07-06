/**
 * Composer entry screen — quick-start preset cards (device-class templates,
 * pre-filled) plus a "Start blank" card. Mirrors the loading/error/empty
 * handling the old questionnaire template picker used.
 */

import { Box, Typography, Card, CardActionArea, CardContent, Alert, CircularProgress } from '@mui/material';
import { AddCircleOutline as BlankIcon } from '@mui/icons-material';
import type { UdtPreset } from '../../types/api';

interface PresetPickerProps {
  presets: UdtPreset[];
  isLoading: boolean;
  isError: boolean;
  onSelectPreset: (preset: UdtPreset) => void;
  onStartBlank: () => void;
}

export function PresetPicker({ presets, isLoading, isError, onSelectPreset, onStartBlank }: PresetPickerProps) {
  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" fontWeight={700} gutterBottom>
          UDT Builder
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Start from a quick-start preset or build any UDT from scratch in a guided wizard —
          standardised naming, alarms, history, and documentation, with live quality checks as you
          go. Download-only: nothing is pushed to a gateway, import the JSON yourself
          (Tag Browser → Import).
        </Typography>
      </Box>

      {isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Loading presets…
          </Typography>
        </Box>
      )}

      {isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load UDT presets.
        </Alert>
      )}

      {!isLoading && !isError && presets.length === 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No UDT presets were found. This indicates a broken installation — the bundled preset
          files are missing. Try reinstalling the app. You can still start blank below.
        </Alert>
      )}

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: 2,
        }}
      >
        {presets.map((preset) => (
          <Card key={preset.id} variant="outlined">
            <CardActionArea
              onClick={() => onSelectPreset(preset)}
              data-testid={`preset-card-${preset.id}`}
              sx={{ height: '100%' }}
            >
              <CardContent>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  {preset.label}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {preset.description}
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        ))}

        <Card variant="outlined" sx={{ borderStyle: 'dashed' }}>
          <CardActionArea onClick={onStartBlank} data-testid="preset-card-blank" sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
              <BlankIcon sx={{ fontSize: 32, color: 'text.secondary', mb: 1 }} />
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Start blank
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Build any UDT from scratch in the guided wizard.
              </Typography>
            </CardContent>
          </CardActionArea>
        </Card>
      </Box>
    </Box>
  );
}
