/**
 * Tests for useWebSocket hook
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from './useWebSocket';

// Store instances for testing
let mockWebSocketInstances: MockWebSocket[] = [];

// Mock WebSocket class
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  sendMock = vi.fn();
  closeMock = vi.fn();

  constructor(url: string) {
    this.url = url;
    mockWebSocketInstances.push(this);
    // Simulate async connection
    setTimeout(() => {
      if (this.readyState !== MockWebSocket.CLOSED) {
        this.readyState = MockWebSocket.OPEN;
        this.onopen?.(new Event('open'));
      }
    }, 0);
  }

  send(data: string) {
    this.sendMock(data);
  }

  close() {
    this.closeMock();
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: 1000, reason: 'Normal closure' }));
  }

  // Helper to simulate receiving a message
  simulateMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  // Helper to simulate an error
  simulateError() {
    this.onerror?.(new Event('error'));
  }

  // Helper to simulate server-initiated close
  simulateClose(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code, reason }));
  }
}

describe('useWebSocket', () => {
  const originalWebSocket = global.WebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    mockWebSocketInstances = [];

    // Replace global WebSocket with our mock class
    global.WebSocket = MockWebSocket as unknown as typeof WebSocket;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    global.WebSocket = originalWebSocket;
  });

  it('connects on mount', async () => {
    const { result } = renderHook(() => useWebSocket());

    expect(result.current.connectionStatus).toBe('connecting');
    expect(mockWebSocketInstances.length).toBe(1);

    // Let the connection open
    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(result.current.connectionStatus).toBe('connected');
    expect(result.current.isConnected).toBe(true);
  });

  it('calls onOpen callback when connected', async () => {
    const onOpen = vi.fn();
    renderHook(() => useWebSocket({ onOpen }));

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(onOpen).toHaveBeenCalled();
  });

  it('calls onExecutionUpdate when receiving execution_update message', async () => {
    const onExecutionUpdate = vi.fn();
    renderHook(() => useWebSocket({ onExecutionUpdate }));

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    const updateData = {
      execution_id: 'test-123',
      status: 'running',
      playbook_name: 'Test Playbook',
    };

    act(() => {
      mockWebSocketInstances[0].simulateMessage({
        type: 'execution_update',
        data: updateData,
      });
    });

    expect(onExecutionUpdate).toHaveBeenCalledWith(updateData);
  });

  it('calls onScreenshotFrame when receiving screenshot_frame message', async () => {
    const onScreenshotFrame = vi.fn();
    renderHook(() => useWebSocket({ onScreenshotFrame }));

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    const frameData = {
      execution_id: 'test-123',
      timestamp: 1234567890,
      frame: 'base64data',
    };

    act(() => {
      mockWebSocketInstances[0].simulateMessage({
        type: 'screenshot_frame',
        data: frameData,
      });
    });

    expect(onScreenshotFrame).toHaveBeenCalledWith(frameData);
  });

  it('handles batched messages', async () => {
    const onExecutionUpdate = vi.fn();
    const onScreenshotFrame = vi.fn();
    renderHook(() => useWebSocket({ onExecutionUpdate, onScreenshotFrame }));

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    // Send a batch message with multiple updates
    act(() => {
      mockWebSocketInstances[0].simulateMessage({
        type: 'batch',
        messages: [
          { type: 'execution_update', data: { execution_id: '1', status: 'running' } },
          { type: 'screenshot_frame', data: { execution_id: '1', frame: 'data1' } },
          { type: 'execution_update', data: { execution_id: '2', status: 'completed' } },
        ],
      });
    });

    expect(onExecutionUpdate).toHaveBeenCalledTimes(2);
    expect(onScreenshotFrame).toHaveBeenCalledTimes(1);
  });

  it('disconnects on unmount', async () => {
    const { unmount } = renderHook(() => useWebSocket());

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(mockWebSocketInstances[0].readyState).toBe(MockWebSocket.OPEN);

    unmount();

    expect(mockWebSocketInstances[0].closeMock).toHaveBeenCalled();
  });

  it('calls onClose callback when disconnected', async () => {
    const onClose = vi.fn();
    const { result } = renderHook(() => useWebSocket({ onClose }));

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    act(() => {
      result.current.disconnect();
    });

    expect(onClose).toHaveBeenCalled();
    expect(result.current.connectionStatus).toBe('disconnected');
  });

  it('sends heartbeat ping every 15 seconds', async () => {
    renderHook(() => useWebSocket());

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(mockWebSocketInstances[0].sendMock).not.toHaveBeenCalled();

    // Advance 15 seconds
    await act(async () => {
      vi.advanceTimersByTime(15000);
    });

    expect(mockWebSocketInstances[0].sendMock).toHaveBeenCalledTimes(1);
    expect(JSON.parse(mockWebSocketInstances[0].sendMock.mock.calls[0][0])).toMatchObject({
      type: 'ping',
    });

    // Advance another 15 seconds
    await act(async () => {
      vi.advanceTimersByTime(15000);
    });

    expect(mockWebSocketInstances[0].sendMock).toHaveBeenCalledTimes(2);
  });

  it('calls onError callback on WebSocket error', async () => {
    const onError = vi.fn();
    const { result } = renderHook(() => useWebSocket({ onError }));

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    act(() => {
      mockWebSocketInstances[0].simulateError();
    });

    expect(onError).toHaveBeenCalled();
    expect(result.current.connectionStatus).toBe('disconnected');
  });

  it('reconnects automatically after server-initiated close', async () => {
    const { result } = renderHook(() => useWebSocket());

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(result.current.connectionStatus).toBe('connected');
    expect(mockWebSocketInstances.length).toBe(1);

    // Simulate server-initiated close
    act(() => {
      mockWebSocketInstances[0].simulateClose(1006, 'Abnormal closure');
    });

    expect(result.current.connectionStatus).toBe('disconnected');

    // Initial reconnect delay is 1000ms * 1.5 = 1500ms (after first backoff)
    await act(async () => {
      vi.advanceTimersByTime(1500);
    });

    // Should have created a new WebSocket
    expect(mockWebSocketInstances.length).toBe(2);
  });

  it('uses exponential backoff for reconnection', async () => {
    renderHook(() => useWebSocket());

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    // First disconnect - should reconnect after initial delay * backoff = 1500ms
    act(() => {
      mockWebSocketInstances[0].simulateClose();
    });

    await act(async () => {
      vi.advanceTimersByTime(1500);
    });
    expect(mockWebSocketInstances.length).toBe(2);

    // Let second connection establish
    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    // Second disconnect - should reconnect after 1500 * 1.5 = 2250ms
    act(() => {
      mockWebSocketInstances[1].simulateClose();
    });

    await act(async () => {
      vi.advanceTimersByTime(2250);
    });
    expect(mockWebSocketInstances.length).toBe(3);

    // Let third connection establish
    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    // Third disconnect - should reconnect after 2250 * 1.5 = 3375ms
    act(() => {
      mockWebSocketInstances[2].simulateClose();
    });

    await act(async () => {
      vi.advanceTimersByTime(3375);
    });
    expect(mockWebSocketInstances.length).toBe(4);
  });

  it('does not reconnect after intentional disconnect', async () => {
    const { result } = renderHook(() => useWebSocket());

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(mockWebSocketInstances.length).toBe(1);

    // Intentionally disconnect
    act(() => {
      result.current.disconnect();
    });

    // Wait for potential reconnect
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });

    // Should still only have one instance
    expect(mockWebSocketInstances.length).toBe(1);
    expect(result.current.connectionStatus).toBe('disconnected');
  });

  it('provides reconnect function', async () => {
    const { result } = renderHook(() => useWebSocket());

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    // Verify the reconnect function exists and can be called
    expect(typeof result.current.reconnect).toBe('function');
  });

  it('resets reconnect delay after successful connection', async () => {
    const { result } = renderHook(() => useWebSocket());

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    // Force multiple disconnects to increase delay
    for (let i = 0; i < 3; i++) {
      const lastInstance = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      act(() => {
        lastInstance.simulateClose();
      });

      // Wait for reconnect with some delay
      await act(async () => {
        vi.advanceTimersByTime(5000);
      });

      // Let connection establish
      await act(async () => {
        vi.advanceTimersByTime(10);
      });
    }

    expect(result.current.connectionStatus).toBe('connected');

    // Now disconnect again - delay should be reset to initial
    const instanceCountBefore = mockWebSocketInstances.length;
    const lastInstance = mockWebSocketInstances[mockWebSocketInstances.length - 1];
    act(() => {
      lastInstance.simulateClose();
    });

    // Should reconnect after initial delay * backoff (1500ms), not the accumulated delay
    await act(async () => {
      vi.advanceTimersByTime(1500);
    });

    expect(mockWebSocketInstances.length).toBe(instanceCountBefore + 1);
  });

  it('handles pong/keepalive messages without errors', async () => {
    renderHook(() => useWebSocket());

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    // These should not throw errors
    act(() => {
      mockWebSocketInstances[0].simulateMessage({ type: 'pong' });
      mockWebSocketInstances[0].simulateMessage({ type: 'keepalive' });
    });

    // Test passes if no errors are thrown
  });

  it('handles malformed messages gracefully', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    renderHook(() => useWebSocket());

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    // Send malformed message (not valid JSON)
    act(() => {
      mockWebSocketInstances[0].onmessage?.(
        new MessageEvent('message', { data: 'not json' })
      );
    });

    // Should not throw, but may log error
    consoleSpy.mockRestore();
  });
});
