/**
 * Centralized localStorage key constants and typed access utilities.
 *
 * All localStorage key strings are defined here as a single source of truth.
 * Use STORAGE_KEYS.* everywhere instead of raw string literals.
 *
 * Key naming prefixes:
 *   playbook_config_*     - per-playbook parameter/config state
 *   playbook_debug_*      - per-playbook debug mode state
 *   playbook_schedule_*   - per-playbook schedule mode state
 *   playbook_order_*      - per-category drag-drop ordering
 *   playbook_sections_*   - per-domain user-created section groupings
 */

/** Keys that take a dynamic suffix (returns a function) */
export const STORAGE_KEYS = {
  // Per-playbook keys (parameterized by playbook path)
  PLAYBOOK_CONFIG: (path: string) => `playbook_config_${path}`,
  PLAYBOOK_DEBUG: (path: string) => `playbook_debug_${path}`,
  PLAYBOOK_SCHEDULE_MODE: (path: string) => `playbook_schedule_mode_${path}`,

  // Per-category keys (parameterized by category name)
  PLAYBOOK_ORDER: (category: string) => `playbook_order_${category}`,

  // Per-domain keys (parameterized by domain name)
  PLAYBOOK_SECTIONS: (domain: string) => `playbook_sections_${domain}`,

  // Static keys (simple strings)
  CATEGORY_ORDER: 'category_order',
  CATEGORY_EXPANDED: 'category_expanded',
  GROUP_EXPANDED: 'group_expanded',
  MAIN_TAB: 'mainTab',
  PLAYBOOK_SUB_TAB: 'playbookSubTab',
  STACK_SUB_TAB: 'stackSubTab',
  THEME: 'theme',
  PLAYBOOK_GRID_COLUMNS: 'playbookGridColumns',
  SELECTED_CREDENTIAL_NAME: 'selectedCredentialName',
  WELCOME_DIALOG_DISMISSED: 'ignition-toolbox-welcome-dismissed',
} as const;

/** Prefixes for scanning/clearing all keys of a type */
export const STORAGE_PREFIXES = {
  PLAYBOOK_CONFIG: 'playbook_config_',
  PLAYBOOK_DEBUG: 'playbook_debug_',
  PLAYBOOK_SCHEDULE_MODE: 'playbook_schedule_mode_',
  PLAYBOOK_ORDER: 'playbook_order_',
  PLAYBOOK_SECTIONS: 'playbook_sections_',
} as const;
