/**
 * React hook for Claude Code chat functionality
 *
 * Provides state management and API for AI chat using Claude Code CLI.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { createLogger } from '../utils/logger';

const logger = createLogger('useClaudeCode');

/**
 * Chat message structure
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  error?: string;
}

/**
 * Context summary for display
 */
export interface ContextSummary {
  playbookCount: number;
  recentExecutions: { name: string; status: string }[];
  cloudDesignerStatus: string;
}

/**
 * Hook return type
 */
interface UseClaudeCodeResult {
  /** Whether Claude Code CLI is available */
  isAvailable: boolean;
  /** Whether availability check is still loading */
  isCheckingAvailability: boolean;
  /** Whether a query is currently being processed */
  isLoading: boolean;
  /** Chat message history */
  messages: ChatMessage[];
  /** Current context summary */
  context: ContextSummary | null;
  /** Send a message to Claude */
  sendMessage: (prompt: string) => Promise<void>;
  /** Clear chat history */
  clearHistory: () => void;
  /** Cancel current query */
  cancelQuery: () => void;
  /** Refresh context */
  refreshContext: () => Promise<void>;
}

/**
 * Generate a unique message ID
 */
function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Check if running in Electron environment
 */
function isElectron(): boolean {
  return typeof window !== 'undefined' && !!window.electronAPI?.chat;
}

/**
 * Hook for Claude Code chat functionality
 */
export function useClaudeCode(): UseClaudeCodeResult {
  const [isAvailable, setIsAvailable] = useState(false);
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [context, setContext] = useState<ContextSummary | null>(null);

  // Track current streaming message
  const streamingMessageIdRef = useRef<string | null>(null);

  // Check Claude Code availability on mount
  useEffect(() => {
    async function checkAvailability() {
      if (!isElectron()) {
        setIsAvailable(false);
        setIsCheckingAvailability(false);
        return;
      }

      try {
        const available = await window.electronAPI!.chat.checkAvailability();
        setIsAvailable(available);
      } catch (error) {
        logger.error('Availability check failed:', error);
        setIsAvailable(false);
      } finally {
        setIsCheckingAvailability(false);
      }
    }

    checkAvailability();
  }, []);

  // Load initial context
  useEffect(() => {
    refreshContext();
  }, []);

  // Set up streaming listener
  useEffect(() => {
    if (!isElectron()) return;

    const unsubscribe = window.electronAPI!.on('chat:stream', (chunk: unknown) => {
      const messageId = streamingMessageIdRef.current;
      if (messageId && typeof chunk === 'string') {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === messageId
              ? { ...msg, content: msg.content + chunk }
              : msg
          )
        );
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  /**
   * Refresh context from backend
   */
  const refreshContext = useCallback(async () => {
    if (!isElectron()) return;

    try {
      const ctx = await window.electronAPI!.chat.getContext();
      setContext(ctx);
    } catch (error) {
      logger.error('Failed to fetch context:', error);
    }
  }, []);

  /**
   * Send a message to Claude
   */
  const sendMessage = useCallback(async (prompt: string) => {
    if (!isElectron() || !isAvailable || isLoading) return;

    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: trimmedPrompt,
      timestamp: new Date(),
    };

    // Add placeholder assistant message for streaming
    const assistantMessage: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };

    streamingMessageIdRef.current = assistantMessage.id;

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsLoading(true);

    try {
      const result = await window.electronAPI!.chat.execute(trimmedPrompt);

      // Update the assistant message with final result
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessage.id
            ? {
                ...msg,
                content: result.success ? result.output : msg.content || result.output,
                isStreaming: false,
                error: result.success ? undefined : result.error,
              }
            : msg
        )
      );
    } catch (error) {
      // Handle unexpected errors
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessage.id
            ? {
                ...msg,
                content: 'An error occurred while processing your request.',
                isStreaming: false,
                error: error instanceof Error ? error.message : 'Unknown error',
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      streamingMessageIdRef.current = null;
    }
  }, [isAvailable, isLoading]);

  /**
   * Clear chat history
   */
  const clearHistory = useCallback(() => {
    setMessages([]);
  }, []);

  /**
   * Cancel current query
   */
  const cancelQuery = useCallback(() => {
    if (!isElectron() || !isLoading) return;

    window.electronAPI!.chat.cancel().catch((error: unknown) => {
      logger.error('Failed to cancel query:', error);
    });

    // Mark current streaming message as cancelled
    if (streamingMessageIdRef.current) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === streamingMessageIdRef.current
            ? { ...msg, isStreaming: false, error: 'Query cancelled' }
            : msg
        )
      );
    }

    setIsLoading(false);
    streamingMessageIdRef.current = null;
  }, [isLoading]);

  return {
    isAvailable,
    isCheckingAvailability,
    isLoading,
    messages,
    context,
    sendMessage,
    clearHistory,
    cancelQuery,
    refreshContext,
  };
}
