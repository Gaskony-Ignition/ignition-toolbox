import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  ToggleButtonGroup,
  ToggleButton,
  Alert,
} from '@mui/material';
import type { PlaybookInfo } from '../types/api';

interface ScheduleDialogProps {
  open: boolean;
  onClose: () => void;
  playbook: PlaybookInfo;
  savedConfig: any;
}

type ScheduleType = 'interval' | 'daily' | 'weekly' | 'monthly' | 'cron';

const DAYS_OF_WEEK = [
  { value: 'mon', label: 'Mon' },
  { value: 'tue', label: 'Tue' },
  { value: 'wed', label: 'Wed' },
  { value: 'thu', label: 'Thu' },
  { value: 'fri', label: 'Fri' },
  { value: 'sat', label: 'Sat' },
  { value: 'sun', label: 'Sun' },
];

export default function ScheduleDialog({
  open,
  onClose,
  playbook,
  savedConfig,
}: ScheduleDialogProps) {
  const [scheduleName, setScheduleName] = useState('');
  const [scheduleType, setScheduleType] = useState<ScheduleType>('daily');

  // Interval settings
  const [intervalMinutes, setIntervalMinutes] = useState(60);

  // Daily/Weekly/Monthly time settings
  const [scheduleTime, setScheduleTime] = useState('09:00');

  // Weekly settings
  const [selectedDays, setSelectedDays] = useState<string[]>(['mon']);

  // Monthly settings
  const [dayOfMonth, setDayOfMonth] = useState(1);

  // Cron expression
  const [cronExpression, setCronExpression] = useState('0 9 * * *');

  // Preview
  const [preview, setPreview] = useState('');

  useEffect(() => {
    if (open) {
      setScheduleName(`${playbook.name} - Scheduled`);
    }
  }, [open, playbook.name]);

  useEffect(() => {
    updatePreview();
  }, [scheduleType, intervalMinutes, scheduleTime, selectedDays, dayOfMonth, cronExpression]);

  const updatePreview = () => {
    switch (scheduleType) {
      case 'interval':
        setPreview(`Every ${intervalMinutes} minute${intervalMinutes !== 1 ? 's' : ''}`);
        break;
      case 'daily':
        setPreview(`Every day at ${scheduleTime}`);
        break;
      case 'weekly':
        const days = selectedDays.map(d => DAYS_OF_WEEK.find(day => day.value === d)?.label).join(', ');
        setPreview(`Every ${days} at ${scheduleTime}`);
        break;
      case 'monthly':
        const suffix = getDaySuffix(dayOfMonth);
        setPreview(`Every month on the ${dayOfMonth}${suffix} at ${scheduleTime}`);
        break;
      case 'cron':
        setPreview(`Cron: ${cronExpression}`);
        break;
    }
  };

  const getDaySuffix = (day: number): string => {
    if (day >= 11 && day <= 13) return 'th';
    switch (day % 10) {
      case 1: return 'st';
      case 2: return 'nd';
      case 3: return 'rd';
      default: return 'th';
    }
  };

  const handleDaysChange = (_event: React.MouseEvent<HTMLElement>, newDays: string[]) => {
    if (newDays.length > 0) {
      setSelectedDays(newDays);
    }
  };

  const handleSave = async () => {
    const scheduleConfig: any = {};

    switch (scheduleType) {
      case 'interval':
        scheduleConfig.minutes = intervalMinutes;
        break;
      case 'daily':
        scheduleConfig.time = scheduleTime;
        break;
      case 'weekly':
        scheduleConfig.time = scheduleTime;
        scheduleConfig.day_of_week = selectedDays.join(',');
        break;
      case 'monthly':
        scheduleConfig.time = scheduleTime;
        scheduleConfig.day = dayOfMonth;
        break;
      case 'cron':
        scheduleConfig.expression = cronExpression;
        break;
    }

    const payload = {
      name: scheduleName,
      playbook_path: playbook.path,
      schedule_type: scheduleType,
      schedule_config: scheduleConfig,
      parameters: savedConfig?.parameters || {},
      gateway_url: savedConfig?.gateway_url || null,
      credential_name: savedConfig?.credential_name || null,
      enabled: true,
    };

    try {
      const response = await fetch('/api/schedules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create schedule');
      }

      onClose();
    } catch (error) {
      console.error('Failed to create schedule:', error);
      alert(`Failed to create schedule: ${error}`);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Schedule Playbook: {playbook.name}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 2 }}>
          {/* Schedule Name */}
          <TextField
            label="Schedule Name"
            value={scheduleName}
            onChange={(e) => setScheduleName(e.target.value)}
            fullWidth
            required
            helperText="A friendly name for this scheduled playbook"
          />

          {/* Schedule Type */}
          <FormControl fullWidth>
            <InputLabel>Schedule Type</InputLabel>
            <Select
              value={scheduleType}
              label="Schedule Type"
              onChange={(e) => setScheduleType(e.target.value as ScheduleType)}
            >
              <MenuItem value="interval">Interval (every X minutes)</MenuItem>
              <MenuItem value="daily">Daily (specific time)</MenuItem>
              <MenuItem value="weekly">Weekly (specific days)</MenuItem>
              <MenuItem value="monthly">Monthly (specific day)</MenuItem>
              <MenuItem value="cron">Advanced (cron expression)</MenuItem>
            </Select>
          </FormControl>

          {/* Interval Settings */}
          {scheduleType === 'interval' && (
            <TextField
              label="Interval (minutes)"
              type="number"
              value={intervalMinutes}
              onChange={(e) => setIntervalMinutes(Math.max(1, parseInt(e.target.value) || 1))}
              fullWidth
              inputProps={{ min: 1 }}
              helperText="Run every X minutes"
            />
          )}

          {/* Daily Settings */}
          {scheduleType === 'daily' && (
            <TextField
              label="Time"
              type="time"
              value={scheduleTime}
              onChange={(e) => setScheduleTime(e.target.value)}
              fullWidth
              helperText="Time to run daily (24-hour format)"
              InputLabelProps={{ shrink: true }}
            />
          )}

          {/* Weekly Settings */}
          {scheduleType === 'weekly' && (
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Select Days of Week
              </Typography>
              <ToggleButtonGroup
                value={selectedDays}
                onChange={handleDaysChange}
                aria-label="days of week"
                sx={{ mb: 2, flexWrap: 'wrap', gap: 1 }}
                color="primary"
              >
                {DAYS_OF_WEEK.map((day) => (
                  <ToggleButton key={day.value} value={day.value} aria-label={day.label}>
                    {day.label}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>

              <TextField
                label="Time"
                type="time"
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
                fullWidth
                helperText="Time to run on selected days (24-hour format)"
                InputLabelProps={{ shrink: true }}
              />
            </Box>
          )}

          {/* Monthly Settings */}
          {scheduleType === 'monthly' && (
            <Box>
              <TextField
                label="Day of Month"
                type="number"
                value={dayOfMonth}
                onChange={(e) => setDayOfMonth(Math.max(1, Math.min(31, parseInt(e.target.value) || 1)))}
                fullWidth
                inputProps={{ min: 1, max: 31 }}
                helperText="Day of the month (1-31)"
                sx={{ mb: 2 }}
              />

              <TextField
                label="Time"
                type="time"
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
                fullWidth
                helperText="Time to run on the specified day (24-hour format)"
                InputLabelProps={{ shrink: true }}
              />
            </Box>
          )}

          {/* Cron Settings */}
          {scheduleType === 'cron' && (
            <Box>
              <TextField
                label="Cron Expression"
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                fullWidth
                helperText="Advanced: Use cron syntax (minute hour day month day_of_week)"
                placeholder="0 9 * * *"
              />
              <Alert severity="info" sx={{ mt: 1 }}>
                <Typography variant="caption">
                  Examples:<br />
                  • <code>0 9 * * *</code> - Every day at 9:00 AM<br />
                  • <code>*/15 * * * *</code> - Every 15 minutes<br />
                  • <code>0 0 * * 0</code> - Every Sunday at midnight
                </Typography>
              </Alert>
            </Box>
          )}

          {/* Preview */}
          <Box
            sx={{
              p: 2,
              bgcolor: 'rgba(0, 255, 0, 0.05)',
              border: '1px solid rgba(0, 255, 0, 0.3)',
              borderRadius: 1,
            }}
          >
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Schedule Preview:
            </Typography>
            <Typography variant="body1" color="primary" fontFamily="monospace">
              {preview}
            </Typography>
          </Box>

          {/* Warning if no config */}
          {!savedConfig && (
            <Alert severity="warning">
              This playbook has no saved configuration. Please configure the playbook parameters before scheduling.
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} sx={{ color: '#00ff00' }}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={!scheduleName || !savedConfig}
          sx={{
            bgcolor: '#00ff00',
            color: '#000',
            '&:hover': { bgcolor: '#00cc00' },
            '&:disabled': { bgcolor: 'rgba(0, 255, 0, 0.3)' },
          }}
        >
          Create Schedule
        </Button>
      </DialogActions>
    </Dialog>
  );
}
