/**
 * Navigation tab constants - single source of truth for all tab names and types.
 *
 * These constants replace scattered union type literals and validation arrays
 * previously duplicated between store/index.ts and component files.
 */

export const MAIN_TABS = [
  'playbooks',
  'designer',
  'api',
  'stackbuilder',
  'udtbuilder',
  'settings',
] as const;

export type MainTab = (typeof MAIN_TABS)[number];

export const PLAYBOOK_SUB_TABS = [
  'gateway',
  'designer',
  'perspective',
  'active-execution',
  'past-executions',
] as const;

export type PlaybookSubTab = (typeof PLAYBOOK_SUB_TABS)[number];

export const STACK_SUB_TABS = ['services', 'integrations', 'preview'] as const;

export type StackSubTab = (typeof STACK_SUB_TABS)[number];
