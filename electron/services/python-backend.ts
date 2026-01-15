import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import { app } from 'electron';
import * as http from 'http';

export interface BackendStatus {
  running: boolean;
  port: number | null;
  pid: number | null;
}

export class PythonBackend {
  private process: ChildProcess | null = null;
  private port: number | null = null;
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private restartCount = 0;
  private maxRestarts = 3;
  private isShuttingDown = false;

  /**
   * Find a free port for the backend server
   */
  private async findFreePort(): Promise<number> {
    return new Promise((resolve, reject) => {
      const server = require('net').createServer();
      server.unref();
      server.on('error', reject);
      server.listen(0, () => {
        const port = server.address().port;
        server.close(() => resolve(port));
      });
    });
  }

  /**
   * Check if we should use the frozen executable (production) or Python script (development)
   */
  private useFrozenExecutable(): boolean {
    if (app.isPackaged) {
      // Production: always use frozen executable
      return true;
    }

    // Development: check if frozen executable exists (for testing builds)
    const frozenPath = this.getFrozenExecutablePath();
    return fs.existsSync(frozenPath);
  }

  /**
   * Get the path to the frozen backend executable
   */
  private getFrozenExecutablePath(): string {
    const isDev = !app.isPackaged;

    if (isDev) {
      // Development: look in backend/dist/backend/
      const exeName = process.platform === 'win32' ? 'backend.exe' : 'backend';
      return path.join(__dirname, '../../backend/dist/backend', exeName);
    }

    // Production: executable is in resources/backend/
    const exeName = process.platform === 'win32' ? 'backend.exe' : 'backend';
    return path.join(process.resourcesPath, 'backend', exeName);
  }

  /**
   * Find the Python executable (for development mode)
   */
  private findPythonExecutable(): string {
    const backendPath = this.getBackendPath();

    // First, check for a virtual environment in the backend directory
    const venvPaths = [
      path.join(backendPath, '.venv', 'bin', 'python'),      // Linux/Mac .venv
      path.join(backendPath, '.venv', 'Scripts', 'python.exe'), // Windows .venv
      path.join(backendPath, 'venv', 'bin', 'python'),       // Linux/Mac venv
      path.join(backendPath, 'venv', 'Scripts', 'python.exe'),  // Windows venv
    ];

    for (const venvPython of venvPaths) {
      if (fs.existsSync(venvPython)) {
        console.log(`Using virtual environment Python: ${venvPython}`);
        return venvPython;
      }
    }

    // Fall back to system Python
    if (process.platform === 'win32') {
      return 'python';
    }
    return 'python3';
  }

  /**
   * Get the backend directory path
   */
  private getBackendPath(): string {
    const isDev = !app.isPackaged;

    if (isDev) {
      // Development: backend is in project root
      return path.join(__dirname, '../../backend');
    }

    // Production: backend is in resources
    return path.join(process.resourcesPath, 'backend');
  }

  /**
   * Start the Python backend server
   */
  async start(): Promise<void> {
    if (this.process) {
      console.log('Python backend already running');
      return;
    }

    this.isShuttingDown = false;
    this.port = await this.findFreePort();

    const useFrozen = this.useFrozenExecutable();
    let executable: string;
    let args: string[];
    let cwd: string;

    // Log environment info for debugging
    console.log(`[Backend] App packaged: ${app.isPackaged}`);
    console.log(`[Backend] Resources path: ${process.resourcesPath}`);
    console.log(`[Backend] Use frozen: ${useFrozen}`);

    if (useFrozen) {
      // Production: use frozen executable
      executable = this.getFrozenExecutablePath();
      args = [];
      cwd = path.dirname(executable);
      console.log(`[Backend] Starting frozen backend: ${executable}`);

      // Verify executable exists
      if (!fs.existsSync(executable)) {
        console.error(`[Backend] ERROR: Executable not found at: ${executable}`);
        // List what's actually in the resources directory
        const resourcesBackend = path.join(process.resourcesPath, 'backend');
        if (fs.existsSync(resourcesBackend)) {
          console.log(`[Backend] Contents of ${resourcesBackend}:`);
          try {
            const files = fs.readdirSync(resourcesBackend);
            files.forEach(f => console.log(`  - ${f}`));
          } catch (e) {
            console.error(`[Backend] Could not list directory: ${e}`);
          }
        } else {
          console.error(`[Backend] Backend directory does not exist: ${resourcesBackend}`);
          // List resources directory
          console.log(`[Backend] Contents of ${process.resourcesPath}:`);
          try {
            const files = fs.readdirSync(process.resourcesPath);
            files.forEach(f => console.log(`  - ${f}`));
          } catch (e) {
            console.error(`[Backend] Could not list resources: ${e}`);
          }
        }
        throw new Error(`Backend executable not found at: ${executable}`);
      }
    } else {
      // Development: use Python script
      executable = this.findPythonExecutable();
      const backendPath = this.getBackendPath();
      const scriptPath = path.join(backendPath, 'run_backend.py');
      args = [scriptPath];
      cwd = backendPath;
      console.log(`[Backend] Starting Python backend: ${executable} ${scriptPath}`);
    }

    console.log(`[Backend] Working directory: ${cwd}`);
    console.log(`[Backend] Port: ${this.port}`);

    // Set environment variables
    const env = {
      ...process.env,
      IGNITION_TOOLKIT_PORT: String(this.port),
      IGNITION_TOOLKIT_HOST: '127.0.0.1',
      PYTHONUNBUFFERED: '1',
      // Use app data directory for toolkit data
      IGNITION_TOOLKIT_DATA: path.join(app.getPath('userData'), 'toolkit-data'),
    };

    // Ensure data directory exists
    const dataDir = env.IGNITION_TOOLKIT_DATA;
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }

    return new Promise((resolve, reject) => {
      this.process = spawn(executable, args, {
        cwd,
        env,
        stdio: ['ignore', 'pipe', 'pipe'],
      });

      let started = false;
      let startupTimeout: NodeJS.Timeout | null = null;
      let stdoutBuffer = '';
      let stderrBuffer = '';

      // Handle stdout
      this.process.stdout?.on('data', (data: Buffer) => {
        const output = data.toString();
        stdoutBuffer += output;
        console.log('[Python]', output.trim());

        // Check for startup message
        if (output.includes('Uvicorn running') || output.includes('Application startup complete')) {
          if (!started) {
            started = true;
            if (startupTimeout) clearTimeout(startupTimeout);
            this.startHealthCheck();
            resolve();
          }
        }
      });

      // Handle stderr
      this.process.stderr?.on('data', (data: Buffer) => {
        const output = data.toString();
        stderrBuffer += output;
        console.error('[Python Error]', output.trim());
      });

      // Handle process exit
      this.process.on('close', (code) => {
        console.log(`Python backend exited with code ${code}`);
        this.process = null;

        if (!started) {
          // Include captured output in error message for debugging
          let errorDetails = `Exit code: ${code}`;
          if (stderrBuffer.trim()) {
            errorDetails += `\n\nStderr:\n${stderrBuffer.slice(-1000)}`; // Last 1000 chars
          }
          if (stdoutBuffer.trim() && !stderrBuffer.trim()) {
            errorDetails += `\n\nStdout:\n${stdoutBuffer.slice(-1000)}`;
          }
          reject(new Error(errorDetails));
        } else if (!this.isShuttingDown && this.restartCount < this.maxRestarts) {
          // Attempt restart
          console.log(`Attempting to restart backend (attempt ${this.restartCount + 1}/${this.maxRestarts})`);
          this.restartCount++;
          setTimeout(() => this.start(), 1000);
        }
      });

      this.process.on('error', (error) => {
        console.error('Failed to start Python backend:', error);
        reject(error);
      });

      // Timeout for startup
      startupTimeout = setTimeout(() => {
        if (!started) {
          // Try health check as fallback
          this.checkHealth().then((healthy) => {
            if (healthy && !started) {
              started = true;
              this.startHealthCheck();
              resolve();
            } else if (!started) {
              reject(new Error('Python backend failed to start within timeout'));
            }
          });
        }
      }, 10000);
    });
  }

  /**
   * Stop the Python backend server
   */
  async stop(): Promise<void> {
    this.isShuttingDown = true;

    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }

    if (!this.process) {
      return;
    }

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        // Force kill if graceful shutdown fails
        if (this.process) {
          console.log('Force killing Python backend');
          this.process.kill('SIGKILL');
        }
        resolve();
      }, 5000);

      this.process!.on('close', () => {
        clearTimeout(timeout);
        this.process = null;
        resolve();
      });

      // Send graceful shutdown signal
      if (process.platform === 'win32') {
        this.process!.kill();
      } else {
        this.process!.kill('SIGTERM');
      }
    });
  }

  /**
   * Restart the backend
   */
  async restart(): Promise<void> {
    await this.stop();
    this.restartCount = 0;
    await this.start();
  }

  /**
   * Check if backend is healthy
   */
  private async checkHealth(): Promise<boolean> {
    if (!this.port) return false;

    return new Promise((resolve) => {
      const req = http.request(
        {
          hostname: '127.0.0.1',
          port: this.port,
          path: '/health',
          method: 'GET',
          timeout: 2000,
        },
        (res) => {
          resolve(res.statusCode === 200);
        }
      );

      req.on('error', () => resolve(false));
      req.on('timeout', () => {
        req.destroy();
        resolve(false);
      });

      req.end();
    });
  }

  /**
   * Start periodic health checks
   */
  private startHealthCheck(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }

    this.healthCheckInterval = setInterval(async () => {
      if (this.isShuttingDown) return;

      const healthy = await this.checkHealth();
      if (!healthy && this.process && !this.isShuttingDown) {
        console.warn('Backend health check failed, attempting restart...');
        await this.restart();
      }
    }, 30000); // Check every 30 seconds
  }

  /**
   * Get the port the backend is running on
   */
  getPort(): number | null {
    return this.port;
  }

  /**
   * Get backend status
   */
  getStatus(): BackendStatus {
    return {
      running: this.process !== null,
      port: this.port,
      pid: this.process?.pid ?? null,
    };
  }

  /**
   * Get the base URL for the backend
   */
  getBaseUrl(): string {
    return `http://127.0.0.1:${this.port}`;
  }

  /**
   * Get the WebSocket URL for the backend
   */
  getWebSocketUrl(): string {
    return `ws://127.0.0.1:${this.port}`;
  }
}
