/**
 * Exchange page - Ignition Exchange resource scraper
 *
 * Five-tab layout: Results | Changes | History | Logs | Settings
 */

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Switch,
  FormControlLabel,
  Stack,
  Link,
  Tooltip,
} from '@mui/material';
import {
  PlayArrow as RunIcon,
  Stop as StopIcon,
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { api } from '../api/client';
import type { ExchangeConfig, ExchangeItem } from '../types/api';

// ============================================================================
// Sub-components
// ============================================================================

function StatusHeader() {
  const queryClient = useQueryClient();

  const { data: status, isLoading } = useQuery({
    queryKey: ['exchange-status'],
    queryFn: api.exchange.getStatus,
    refetchInterval: (query) => (query.state.data?.is_running ? 2000 : 10000),
  });

  const runMutation = useMutation({
    mutationFn: () => api.exchange.run(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['exchange-status'] }),
  });

  const stopMutation = useMutation({
    mutationFn: api.exchange.stop,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['exchange-status'] }),
  });

  const isRunning = status?.is_running ?? false;

  const formatRelativeTime = (iso: string | null) => {
    if (!iso) return 'Never';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  return (
    <Box
      sx={{
        p: 2,
        mb: 2,
        bgcolor: 'background.paper',
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
        {/* Left: status + progress */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {isRunning ? (
              <>
                <CircularProgress size={14} thickness={5} />
                <Typography variant="body2" color="primary.main" fontWeight={600}>
                  Running
                  {status && status.progress_total > 0
                    ? ` — ${status.progress_current}/${status.progress_total}`
                    : ''}
                </Typography>
              </>
            ) : (
              <Chip
                label={status?.status ?? 'Idle'}
                size="small"
                color={status?.status === 'error' ? 'error' : status?.status === 'completed' ? 'success' : 'default'}
                variant="outlined"
              />
            )}
          </Box>

          <Typography variant="body2" color="text.secondary">
            Last run: {isLoading ? '…' : formatRelativeTime(status?.last_run ?? null)}
          </Typography>

          {status && status.item_count > 0 && (
            <Typography variant="body2" color="text.secondary">
              {status.item_count.toLocaleString()} resources
            </Typography>
          )}
        </Box>

        {/* Right: action buttons */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            size="small"
            startIcon={<RunIcon />}
            onClick={() => runMutation.mutate()}
            disabled={isRunning || runMutation.isPending}
          >
            Run Scrape
          </Button>
          <Button
            variant="outlined"
            size="small"
            startIcon={<StopIcon />}
            onClick={() => stopMutation.mutate()}
            disabled={!isRunning || stopMutation.isPending}
            color="error"
          >
            Stop
          </Button>
        </Box>
      </Box>

      {/* Changes summary */}
      <ChangeSummaryRow />

      {/* Error */}
      {status?.last_error && (
        <Alert severity="error" sx={{ mt: 1 }} onClose={() => {}}>
          {status.last_error}
        </Alert>
      )}
    </Box>
  );
}

function ChangeSummaryRow() {
  const { data: changes } = useQuery({
    queryKey: ['exchange-changes'],
    queryFn: api.exchange.getChanges,
  });

  const hasChanges =
    changes && (changes.new.length > 0 || changes.updated.length > 0 || changes.removed.length > 0);

  if (!hasChanges) return null;

  return (
    <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
      {changes.new.length > 0 && (
        <Chip label={`${changes.new.length} new`} size="small" color="success" variant="outlined" />
      )}
      {changes.updated.length > 0 && (
        <Chip label={`${changes.updated.length} updated`} size="small" color="warning" variant="outlined" />
      )}
      {changes.removed.length > 0 && (
        <Chip label={`${changes.removed.length} removed`} size="small" color="error" variant="outlined" />
      )}
    </Box>
  );
}

// ============================================================================
// Results Tab
// ============================================================================

function ResultsTab() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['exchange-results'],
    queryFn: () => api.exchange.getResults(),
    staleTime: 60_000,
  });

  const items = useMemo(() => data?.items ?? [], [data?.items]);

  // Client-side filter
  const filtered = useMemo(() => {
    let result = items;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          r.contributor.toLowerCase().includes(q) ||
          r.tagline.toLowerCase().includes(q),
      );
    }
    if (category) {
      result = result.filter((r) => r.category === category);
    }
    return result;
  }, [items, search, category]);

  const categories = useMemo(
    () => Array.from(new Set(items.map((r) => r.category).filter(Boolean))).sort(),
    [items],
  );

  if (isLoading) return <Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">Failed to load results</Alert>;

  if (items.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', opacity: 0.6 }}>
        <Typography variant="h6" gutterBottom>No results yet</Typography>
        <Typography variant="body2">Run a scrape to collect Exchange resources.</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <TextField
          size="small"
          placeholder="Search title, contributor, tagline…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ minWidth: 280 }}
        />
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Category</InputLabel>
          <Select
            value={category}
            label="Category"
            onChange={(e) => setCategory(e.target.value)}
          >
            <MenuItem value="">All categories</MenuItem>
            {categories.map((cat) => (
              <MenuItem key={cat} value={cat}>{cat}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <Typography variant="body2" color="text.secondary" sx={{ alignSelf: 'center' }}>
          {filtered.length} of {items.length}
        </Typography>
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Contributor</TableCell>
              <TableCell>Category</TableCell>
              <TableCell align="right">Downloads</TableCell>
              <TableCell>Version</TableCell>
              <TableCell>Updated</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((item) => (
              <TableRow key={item.id} hover>
                <TableCell>
                  <Tooltip title={item.tagline || item.title} arrow placement="top">
                    <Link href={item.url} target="_blank" rel="noopener noreferrer" underline="hover">
                      {item.title || item.id}
                    </Link>
                  </Tooltip>
                </TableCell>
                <TableCell>{item.contributor}</TableCell>
                <TableCell>
                  {item.category && (
                    <Chip label={item.category} size="small" variant="outlined" />
                  )}
                </TableCell>
                <TableCell align="right">
                  {item.download_count > 0 ? item.download_count.toLocaleString() : '—'}
                </TableCell>
                <TableCell>{item.version || '—'}</TableCell>
                <TableCell>{item.updated_date || '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

// ============================================================================
// Changes Tab
// ============================================================================

function ChangesTab() {
  const { data: changes, isLoading } = useQuery({
    queryKey: ['exchange-changes'],
    queryFn: api.exchange.getChanges,
  });

  if (isLoading) return <Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>;

  const renderItemTable = (items: ExchangeItem[]) => (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Title</TableCell>
            <TableCell>Contributor</TableCell>
            <TableCell>Category</TableCell>
            <TableCell>Version</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id} hover>
              <TableCell>
                <Link href={item.url} target="_blank" rel="noopener noreferrer" underline="hover">
                  {item.title || item.id}
                </Link>
              </TableCell>
              <TableCell>{item.contributor}</TableCell>
              <TableCell>{item.category}</TableCell>
              <TableCell>{item.version || '—'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const hasAny =
    (changes?.new.length ?? 0) + (changes?.updated.length ?? 0) + (changes?.removed.length ?? 0) > 0;

  if (!hasAny) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', opacity: 0.6 }}>
        <Typography variant="body2">No changes detected in the last run.</Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={2}>
      {(changes?.new.length ?? 0) > 0 && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography fontWeight={600} color="success.main">
              New ({changes!.new.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 0 }}>
            {renderItemTable(changes!.new)}
          </AccordionDetails>
        </Accordion>
      )}
      {(changes?.updated.length ?? 0) > 0 && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography fontWeight={600} color="warning.main">
              Updated ({changes!.updated.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 0 }}>
            {renderItemTable(changes!.updated)}
          </AccordionDetails>
        </Accordion>
      )}
      {(changes?.removed.length ?? 0) > 0 && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography fontWeight={600} color="error.main">
              Removed ({changes!.removed.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 0 }}>
            {renderItemTable(changes!.removed)}
          </AccordionDetails>
        </Accordion>
      )}
    </Stack>
  );
}

// ============================================================================
// History Tab
// ============================================================================

function HistoryTab() {
  const { data: history, isLoading } = useQuery({
    queryKey: ['exchange-history'],
    queryFn: api.exchange.getHistory,
  });

  if (isLoading) return <Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>;

  if (!history || history.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', opacity: 0.6 }}>
        <Typography variant="body2">No scrape runs yet.</Typography>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Date / Time</TableCell>
            <TableCell align="right">Duration</TableCell>
            <TableCell align="right">Items</TableCell>
            <TableCell align="right">New</TableCell>
            <TableCell align="right">Updated</TableCell>
            <TableCell align="right">Removed</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {history.map((entry, idx) => (
            <TableRow key={idx} hover>
              <TableCell>
                <Typography variant="body2">
                  {new Date(entry.timestamp).toLocaleString()}
                </Typography>
              </TableCell>
              <TableCell align="right">{entry.duration_seconds}s</TableCell>
              <TableCell align="right">{entry.items_scraped}</TableCell>
              <TableCell align="right">
                <Typography variant="body2" color={entry.changes.new > 0 ? 'success.main' : 'text.secondary'}>
                  {entry.changes.new}
                </Typography>
              </TableCell>
              <TableCell align="right">
                <Typography variant="body2" color={entry.changes.updated > 0 ? 'warning.main' : 'text.secondary'}>
                  {entry.changes.updated}
                </Typography>
              </TableCell>
              <TableCell align="right">
                <Typography variant="body2" color={entry.changes.removed > 0 ? 'error.main' : 'text.secondary'}>
                  {entry.changes.removed}
                </Typography>
              </TableCell>
              <TableCell>
                <Chip
                  label={entry.success ? 'Success' : 'Failed'}
                  size="small"
                  color={entry.success ? 'success' : 'error'}
                  variant="outlined"
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

// ============================================================================
// Logs Tab
// ============================================================================

function LogsTab() {
  const { data: status } = useQuery({
    queryKey: ['exchange-status'],
    queryFn: api.exchange.getStatus,
    refetchInterval: 5000,
  });

  const { data: logs, refetch } = useQuery({
    queryKey: ['exchange-logs'],
    queryFn: () => api.exchange.getLogs(200),
    refetchInterval: status?.is_running ? 3000 : false,
  });

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
        <Button size="small" startIcon={<RefreshIcon />} onClick={() => refetch()}>
          Refresh
        </Button>
      </Box>
      <Box
        component="pre"
        sx={{
          fontFamily: 'monospace',
          fontSize: '0.75rem',
          bgcolor: 'background.paper',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          p: 2,
          overflow: 'auto',
          maxHeight: 500,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
          color: 'text.secondary',
        }}
      >
        {logs && logs.length > 0 ? logs.join('\n') : 'No log entries yet.'}
      </Box>
    </Box>
  );
}

// ============================================================================
// Settings Tab
// ============================================================================

function SettingsTab() {
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ['exchange-config'],
    queryFn: api.exchange.getConfig,
  });

  const [localConfig, setLocalConfig] = useState<ExchangeConfig | null>(null);
  const effective = localConfig ?? config;

  const saveMutation = useMutation({
    mutationFn: (cfg: ExchangeConfig) => api.exchange.saveConfig(cfg),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exchange-config'] });
      setLocalConfig(null);
    },
  });

  if (isLoading || !effective) return <Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>;

  const update = (patch: Partial<ExchangeConfig>) => {
    setLocalConfig((prev) => ({ ...(prev ?? effective!), ...patch }));
  };

  const updateSchedule = (patch: Partial<ExchangeConfig['schedule']>) => {
    setLocalConfig((prev) => ({
      ...(prev ?? effective!),
      schedule: { ...(prev ?? effective!).schedule, ...patch },
    }));
  };

  return (
    <Box sx={{ maxWidth: 520 }}>
      <Stack spacing={3}>
        {/* Headless */}
        <FormControlLabel
          control={
            <Switch
              checked={effective.headless}
              onChange={(e) => update({ headless: e.target.checked })}
            />
          }
          label={
            <Box>
              <Typography variant="body2" fontWeight={600}>Headless browser</Typography>
              <Typography variant="caption" color="text.secondary">
                Run Chromium without a visible window (recommended)
              </Typography>
            </Box>
          }
        />

        {/* Max resources */}
        <Box>
          <Typography variant="body2" fontWeight={600} gutterBottom>Max Resources</Typography>
          <TextField
            type="number"
            size="small"
            value={effective.max_resources}
            onChange={(e) => update({ max_resources: Math.max(0, parseInt(e.target.value) || 0) })}
            inputProps={{ min: 0 }}
            helperText="0 = scrape all resources (~530)"
            sx={{ width: 180 }}
          />
        </Box>

        {/* Schedule */}
        <Box>
          <FormControlLabel
            control={
              <Switch
                checked={effective.schedule.enabled}
                onChange={(e) => updateSchedule({ enabled: e.target.checked })}
              />
            }
            label={
              <Box>
                <Typography variant="body2" fontWeight={600}>Enable Schedule</Typography>
                <Typography variant="caption" color="text.secondary">
                  Automatically run scrape on a cron schedule
                </Typography>
              </Box>
            }
          />
          {effective.schedule.enabled && (
            <TextField
              size="small"
              label="Cron expression"
              value={effective.schedule.cron}
              onChange={(e) => updateSchedule({ cron: e.target.value })}
              helperText='e.g. "0 6 * * 1" = every Monday at 6am UTC'
              sx={{ mt: 1.5, width: 280 }}
            />
          )}
        </Box>

        {/* Save button */}
        <Box>
          <Button
            variant="contained"
            onClick={() => saveMutation.mutate(effective)}
            disabled={saveMutation.isPending || !localConfig}
          >
            {saveMutation.isPending ? 'Saving…' : 'Save Settings'}
          </Button>
          {saveMutation.isSuccess && (
            <Typography variant="caption" color="success.main" sx={{ ml: 2 }}>
              Saved
            </Typography>
          )}
          {saveMutation.isError && (
            <Typography variant="caption" color="error" sx={{ ml: 2 }}>
              Save failed
            </Typography>
          )}
        </Box>
      </Stack>
    </Box>
  );
}

// ============================================================================
// Main Exchange Page
// ============================================================================

type ExchangeTab = 'results' | 'changes' | 'history' | 'logs' | 'settings';

export function Exchange() {
  const [activeTab, setActiveTab] = useState<ExchangeTab>('results');

  return (
    <Box>
      {/* Page header */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" fontWeight={700} gutterBottom>
          Ignition Exchange
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Browse and track resources from the Inductive Automation Exchange.
        </Typography>
      </Box>

      {/* Status + run controls */}
      <StatusHeader />

      {/* Tab navigation */}
      <Tabs
        value={activeTab}
        onChange={(_e, v: ExchangeTab) => setActiveTab(v)}
        sx={{ mb: 2, borderBottom: '1px solid', borderColor: 'divider' }}
      >
        <Tab label="Results" value="results" />
        <Tab label="Changes" value="changes" />
        <Tab label="History" value="history" />
        <Tab label="Logs" value="logs" />
        <Tab label="Settings" value="settings" />
      </Tabs>

      {/* Tab content */}
      {activeTab === 'results' && <ResultsTab />}
      {activeTab === 'changes' && <ChangesTab />}
      {activeTab === 'history' && <HistoryTab />}
      {activeTab === 'logs' && <LogsTab />}
      {activeTab === 'settings' && <SettingsTab />}
    </Box>
  );
}
