/**
 * Centralized timing and polling configuration.
 *
 * All polling intervals, delay values, and WebSocket timing constants
 * are defined here. Import from this file instead of hardcoding numbers.
 *
 * All values are in milliseconds unless noted otherwise.
 */

export const TIMING = {
  /** Polling intervals for React Query refetchInterval */
  POLLING: {
    /** ExecutionDetail page - fast polling during active execution */
    EXECUTION_ACTIVE: 2000,
    /** ExecutionDetail page - log polling when logs panel is open */
    EXECUTION_LOGS: 3000,
    /** Playbooks page - background refresh for playbook list */
    PLAYBOOKS: 30000,
    /** Playbooks page - check for library updates */
    PLAYBOOK_UPDATES: 300000,
    /** Designer page - status check when running */
    DESIGNER_FAST: 5000,
    /** Designer page - status check when idle */
    DESIGNER_SLOW: 30000,
    /** Designer page - log polling while a mutation is pending */
    DESIGNER_LOGS_PENDING: 1500,
    /** StackBuilder page - status check during deployment */
    STACKBUILDER_FAST: 5000,
    /** StackBuilder page - status check when idle */
    STACKBUILDER_SLOW: 30000,
    /** PlaybookCard - interval to re-check saved config from localStorage */
    PLAYBOOK_CONFIG_CHECK: 5000,
  },

  /** Short-lived UI delays (snackbars, toast, copy-button reset, etc.) */
  UI: {
    /** MUI Snackbar autoHideDuration */
    SNACKBAR: 3000,
    /** PlaybookCard snackbar autoHideDuration */
    SNACKBAR_CARD: 4000,
    /** Copy-to-clipboard button reset delay */
    COPY_RESET: 3000,
    /** Save button text reset delay */
    SAVE_RESET: 3000,
    /** Generic notification dismiss delay */
    NOTIFICATION: 3000,
  },

  /** WebSocket reconnection and heartbeat timing */
  WEBSOCKET: {
    /** Initial reconnect backoff delay */
    RECONNECT_INITIAL: 1000,
    /** Maximum reconnect backoff delay */
    RECONNECT_MAX: 30000,
    /** Backoff multiplier applied after each failed reconnect attempt */
    RECONNECT_BACKOFF: 1.5,
    /** Interval between ping/heartbeat messages */
    HEARTBEAT_INTERVAL: 15000,
  },
} as const;
