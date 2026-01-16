import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { getInitPromise } from './api/client'
import { getWsInitPromise } from './hooks/useWebSocket'

// Wait for API and WebSocket URLs to initialize before rendering
// This ensures Electron IPC calls complete before any API/WS connections
async function initializeApp() {
  await Promise.all([
    getInitPromise(),
    getWsInitPromise(),
  ]);

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

initializeApp();
