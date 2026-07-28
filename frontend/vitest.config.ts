import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    // Heavy jsdom + MUI page files (Playbooks, UdtBuilder, Executions) are slow
    // to transform and render. With unbounded file parallelism they starve each
    // other: a dynamic import() overruns its timeout, the aborted render leaves
    // an empty body, and following tests in the file fail too. Which files lose
    // the race varied per run, so the suite went red intermittently.
    // Capping workers removes the contention; the timeouts are headroom.
    // NOTE: use maxWorkers, not poolOptions.{forks,threads}.max* — Vitest 4
    // dropped those keys and ignores them silently.
    maxWorkers: 4,
    testTimeout: 30000,
    hookTimeout: 30000,
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/test/'],
    },
  },
});
