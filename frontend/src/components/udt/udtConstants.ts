/**
 * Shared constants for the UDT composer wizard — data types, alarm
 * priorities/modes, and the standard analog/digital alarm names. Kept
 * separate from convention *logic* (which lives server-side in
 * udt/composer.py) — these are just UI choice lists.
 */

import type { UdtDataType } from '../../types/api';

export const DATA_TYPES: UdtDataType[] = ['Float4', 'Float8', 'Short', 'Integer', 'Long', 'Boolean', 'String'];

/** Numeric ("analog") data types get eng unit/low/high and the standard HiHi/Hi/Lo/LoLo alarm set. */
export const ANALOG_DATA_TYPES: UdtDataType[] = ['Float4', 'Float8', 'Short', 'Integer', 'Long'];

export function isAnalogDataType(dataType: UdtDataType): boolean {
  return (ANALOG_DATA_TYPES as string[]).includes(dataType);
}

export const NAMING_STYLES = ['camelCase', 'PascalCase'] as const;

/** null priority = "ISA default" (server applies the ISA-18.2 mapping for this alarm name). */
export const ISA_DEFAULT_PRIORITY = null;

export const ALARM_PRIORITIES: Array<{ value: string | null; label: string }> = [
  { value: null, label: 'ISA default' },
  { value: 'Diagnostic', label: 'Diagnostic' },
  { value: 'Low', label: 'Low' },
  { value: 'Medium', label: 'Medium' },
  { value: 'High', label: 'High' },
  { value: 'Critical', label: 'Critical' },
];

export const ALARM_MODES = ['AboveValue', 'BelowValue', 'AboveOrEqualValue', 'BelowOrEqualValue'] as const;

/** Standard ISA-18.2-aligned analog alarm rows, in display order, with their conventional mode. */
export const STANDARD_ANALOG_ALARMS: Array<{ name: string; defaultMode: string }> = [
  { name: 'HiHi', defaultMode: 'AboveValue' },
  { name: 'Hi', defaultMode: 'AboveValue' },
  { name: 'Lo', defaultMode: 'BelowValue' },
  { name: 'LoLo', defaultMode: 'BelowValue' },
];

/** Standard discrete (Boolean) alarm rows — matches the server's STANDARD_ALARM_DEFAULTS. */
export const STANDARD_BOOL_ALARMS: Array<{ name: string; defaultMode: string }> = [
  { name: 'Fault', defaultMode: 'BooleanTrue' },
  { name: 'Trip', defaultMode: 'BooleanTrue' },
  { name: 'Warning', defaultMode: 'BooleanTrue' },
];

export const BOOL_ALARM_MODES = ['BooleanTrue', 'BooleanFalse'] as const;

export const DEADBAND_STYLES = ['Auto', 'Percent', 'Absolute'] as const;

export const DEFAULT_TAG_GROUP = 'Default Historical';
