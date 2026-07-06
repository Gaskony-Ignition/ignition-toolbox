/**
 * Composer wizard — "History" step: per-tag enable toggle, tag group, and
 * deadband style. Deliberate per-member choice — never blanket-enabled.
 */

import {
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Switch,
  TextField,
  FormControl,
  Select,
  MenuItem,
} from '@mui/material';
import type { UdtComposition, UdtCompositionHistory } from '../../types/api';
import { flattenTags, updateMemberAt, type Path } from './treeUtils';
import { DEADBAND_STYLES, DEFAULT_TAG_GROUP } from './udtConstants';

const DEFAULT_HISTORY: UdtCompositionHistory = {
  enabled: false,
  tag_group: DEFAULT_TAG_GROUP,
  deadband_style: 'Auto',
};

interface HistoryEditorProps {
  composition: UdtComposition;
  onChange: (updater: (c: UdtComposition) => UdtComposition) => void;
}

export function HistoryEditor({ composition, onChange }: HistoryEditorProps) {
  const tags = flattenTags(composition.members);

  const updateHistory = (path: Path, patch: Partial<UdtCompositionHistory>) => {
    onChange((c) => ({
      ...c,
      members: updateMemberAt(c.members, path, (m) => {
        if (m.kind !== 'tag') return m;
        return { ...m, history: { ...DEFAULT_HISTORY, ...m.history, ...patch } };
      }),
    }));
  };

  if (tags.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No tags yet — add some in the Structure step to configure history.
      </Typography>
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Tag</TableCell>
            <TableCell>History</TableCell>
            <TableCell>Tag group</TableCell>
            <TableCell>Deadband style</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {tags.map(({ path, location, tag }) => {
            const history = tag.history ?? DEFAULT_HISTORY;
            return (
              <TableRow key={location}>
                <TableCell>
                  <Typography variant="body2" fontFamily="monospace">
                    {location}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Switch
                    size="small"
                    checked={history.enabled}
                    onChange={(e) => updateHistory(path, { enabled: e.target.checked })}
                    slotProps={{ input: { 'aria-label': `Enable history for ${location}` } }}
                  />
                </TableCell>
                <TableCell>
                  <TextField
                    size="small"
                    value={history.tag_group ?? DEFAULT_TAG_GROUP}
                    onChange={(e) => updateHistory(path, { tag_group: e.target.value })}
                    disabled={!history.enabled}
                    slotProps={{ htmlInput: { 'aria-label': `Tag group for ${location}` } }}
                  />
                </TableCell>
                <TableCell>
                  <FormControl size="small" disabled={!history.enabled} sx={{ minWidth: 130 }}>
                    <Select
                      value={history.deadband_style ?? 'Auto'}
                      onChange={(e) => updateHistory(path, { deadband_style: e.target.value })}
                      inputProps={{ 'aria-label': `Deadband style for ${location}` }}
                    >
                      {DEADBAND_STYLES.map((style) => (
                        <MenuItem key={style} value={style}>
                          {style}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
