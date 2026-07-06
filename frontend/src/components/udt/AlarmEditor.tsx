/**
 * Composer wizard — "Alarms" step: per-analog-tag toggleable standard
 * HiHi/Hi/Lo/LoLo rows (setpoint + mode + priority), per-Bool-tag a single
 * state alarm row. `priority: null` means "apply the ISA-18.2 default for
 * this alarm name" — surfaced as the "ISA default" option.
 */

import { Box, Typography, Paper, Stack, FormControlLabel, Switch, FormControl, InputLabel, Select, MenuItem, TextField } from '@mui/material';
import type { UdtComposition, UdtCompositionAlarm, UdtCompositionTag } from '../../types/api';
import { flattenTags, updateMemberAt, type Path } from './treeUtils';
import { ALARM_MODES, ALARM_PRIORITIES, BOOL_ALARM_MODES, STANDARD_BOOL_ALARMS, STANDARD_ANALOG_ALARMS } from './udtConstants';

const ISA_SENTINEL = '__isa_default__';

function findAlarm(alarms: UdtCompositionAlarm[] | undefined, name: string): UdtCompositionAlarm | undefined {
  return alarms?.find((a) => a.name === name);
}

function setAlarm(alarms: UdtCompositionAlarm[] | undefined, alarm: UdtCompositionAlarm): UdtCompositionAlarm[] {
  const existing = alarms ?? [];
  const index = existing.findIndex((a) => a.name === alarm.name);
  if (index === -1) return [...existing, alarm];
  return existing.map((a, i) => (i === index ? alarm : a));
}

function removeAlarm(alarms: UdtCompositionAlarm[] | undefined, name: string): UdtCompositionAlarm[] {
  return (alarms ?? []).filter((a) => a.name !== name);
}

interface TagAlarmCardProps {
  location: string;
  tag: UdtCompositionTag;
  onChangeAlarms: (alarms: UdtCompositionAlarm[]) => void;
}

function TagAlarmCard({ location, tag, onChangeAlarms }: TagAlarmCardProps) {
  const isBool = tag.data_type === 'Boolean';
  const rows = isBool ? STANDARD_BOOL_ALARMS : STANDARD_ANALOG_ALARMS;

  return (
    <Paper variant="outlined" sx={{ p: 1.5 }} data-testid={`alarm-card-${location}`}>
      <Typography variant="subtitle2" fontFamily="monospace" gutterBottom>
        {location}
      </Typography>
      <Stack spacing={1}>
        {rows.map((row) => {
          const alarm = findAlarm(tag.alarms, row.name);
          const enabled = !!alarm;
          const rowId = `${location}-${row.name}`;

          return (
            <Box key={row.name} sx={{ display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
              <FormControlLabel
                sx={{ minWidth: 110 }}
                control={
                  <Switch
                    size="small"
                    checked={enabled}
                    onChange={(e) => {
                      if (e.target.checked) {
                        onChangeAlarms(
                          setAlarm(tag.alarms, {
                            name: row.name,
                            // Boolean alarms fire on their mode (BooleanTrue/False),
                            // no setpoint; analog alarms need a setpoint plus a
                            // positive deadband or the lint pack flags them.
                            ...(isBool ? {} : { setpoint: 0, deadband: 1 }),
                            mode: row.defaultMode,
                            priority: null,
                          })
                        );
                      } else {
                        onChangeAlarms(removeAlarm(tag.alarms, row.name));
                      }
                    }}
                  />
                }
                label={row.name}
              />

              {enabled && alarm && (
                <>
                  {isBool ? (
                    <FormControl size="small" sx={{ minWidth: 150 }}>
                      <InputLabel id={`${rowId}-mode`}>Alarm on</InputLabel>
                      <Select
                        labelId={`${rowId}-mode`}
                        label="Alarm on"
                        value={alarm.mode ?? row.defaultMode}
                        onChange={(e) => onChangeAlarms(setAlarm(tag.alarms, { ...alarm, mode: e.target.value }))}
                      >
                        {BOOL_ALARM_MODES.map((mode) => (
                          <MenuItem key={mode} value={mode}>
                            {mode === 'BooleanTrue' ? 'True' : 'False'}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  ) : (
                    <TextField
                      label="Setpoint"
                      type="number"
                      size="small"
                      sx={{ width: 120 }}
                      value={alarm.setpoint ?? ''}
                      onChange={(e) =>
                        onChangeAlarms(
                          setAlarm(tag.alarms, {
                            ...alarm,
                            setpoint: e.target.value === '' ? '' : Number(e.target.value),
                          })
                        )
                      }
                    />
                  )}

                  {!isBool && (
                    <TextField
                      label="Deadband"
                      type="number"
                      size="small"
                      sx={{ width: 110 }}
                      value={alarm.deadband ?? ''}
                      onChange={(e) =>
                        onChangeAlarms(
                          setAlarm(tag.alarms, {
                            ...alarm,
                            deadband: e.target.value === '' ? '' : Number(e.target.value),
                          })
                        )
                      }
                    />
                  )}

                  {!isBool && (
                    <FormControl size="small" sx={{ minWidth: 170 }}>
                      <InputLabel id={`${rowId}-mode`}>Mode</InputLabel>
                      <Select
                        labelId={`${rowId}-mode`}
                        label="Mode"
                        value={alarm.mode ?? row.defaultMode}
                        onChange={(e) => onChangeAlarms(setAlarm(tag.alarms, { ...alarm, mode: e.target.value }))}
                      >
                        {ALARM_MODES.map((mode) => (
                          <MenuItem key={mode} value={mode}>
                            {mode}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  )}

                  <FormControl size="small" sx={{ minWidth: 150 }}>
                    <InputLabel id={`${rowId}-priority`}>Priority</InputLabel>
                    <Select
                      labelId={`${rowId}-priority`}
                      label="Priority"
                      value={alarm.priority ?? ISA_SENTINEL}
                      onChange={(e) => {
                        const value = e.target.value;
                        onChangeAlarms(setAlarm(tag.alarms, { ...alarm, priority: value === ISA_SENTINEL ? null : value }));
                      }}
                    >
                      {ALARM_PRIORITIES.map((p) => (
                        <MenuItem key={p.label} value={p.value ?? ISA_SENTINEL}>
                          {p.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </>
              )}
            </Box>
          );
        })}
      </Stack>
    </Paper>
  );
}

interface AlarmEditorProps {
  composition: UdtComposition;
  onChange: (updater: (c: UdtComposition) => UdtComposition) => void;
}

export function AlarmEditor({ composition, onChange }: AlarmEditorProps) {
  const tags = flattenTags(composition.members);
  const alarmable = tags.filter(({ tag }) => tag.data_type !== 'String');

  const updateAlarms = (path: Path, alarms: UdtCompositionAlarm[]) => {
    onChange((c) => ({
      ...c,
      members: updateMemberAt(c.members, path, (m) => (m.kind === 'tag' ? { ...m, alarms } : m)),
    }));
  };

  if (alarmable.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No analog or boolean tags yet — add some in the Structure step to configure alarms.
      </Typography>
    );
  }

  return (
    <Stack spacing={2}>
      {alarmable.map(({ path, location, tag }) => (
        <TagAlarmCard key={location} location={location} tag={tag} onChangeAlarms={(alarms) => updateAlarms(path, alarms)} />
      ))}
    </Stack>
  );
}
