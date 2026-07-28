/**
 * Centralized help content for contextual tooltips throughout the app
 */

export const helpContent = {
  // StackBuilder section
  stackBuilder: {
    services:
      'Browse and add services to your Docker Compose stack. Click "Add" to include a service, then configure its settings.',
    settings:
      'Configure global stack settings like name, timezone, and container restart policy. These apply to all services in the stack.',
    integrations:
      'When you add compatible services (like Traefik, databases, or MQTT brokers), integration options appear here to configure how they work together.',
    preview:
      'Preview the generated docker-compose.yml file before downloading. Click "Preview" in the actions bar to generate.',
    deploy:
      'Deploy this stack directly to your local Docker environment. Requires Docker to be installed and running.',
  },

  // Credentials section
  credentials: {
    overview:
      'Gateway credentials are securely stored and used for automated login during playbook execution. Credentials are encrypted at rest.',
    gatewayUrl:
      'The full URL to your Ignition Gateway, including protocol and port (e.g., https://gateway.local:8043).',
    usage:
      'Select a credential from the header dropdown to use it across all playbooks, or specify credentials per-playbook.',
  },

  // Playbooks section
  playbooks: {
    overview:
      'Playbooks are automated sequences of steps that test or configure your Ignition system. Each step performs a specific action.',
    execution:
      'Run playbooks to execute all steps in sequence. Failed steps can be retried, and you can watch execution in real-time.',
    parameters:
      'Some playbooks accept parameters that customize their behavior. Parameters can be set before execution.',
    domains:
      'Playbooks are organized by domain: Gateway (config/backup), Designer (project work), Perspective (UI testing), and API (REST calls).',
  },

  // Settings section
  settings: {
    theme:
      'Choose between dark and light color themes. Dark mode is easier on the eyes in low-light environments.',
    density:
      'Adjust spacing between UI elements. Compact shows more content, Spacious provides more breathing room.',
    updates:
      'Check for and install application updates. Updates are downloaded in the background and applied on restart.',
  },

  // General
  general: {
    globalCredential:
      'The selected credential will be used as the default for all operations. You can override this in individual playbooks.',
  },
};

export type HelpSection = keyof typeof helpContent;
export type HelpKey<T extends HelpSection> = keyof typeof helpContent[T];
