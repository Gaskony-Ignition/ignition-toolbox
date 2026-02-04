/**
 * ChatPanel - Shared chat UI component for Toolbox Assistant
 *
 * Displays chat messages, input field, and handles user interactions.
 * Can be used in both the full Chat page and the floating drawer.
 */

import { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Typography,
  Paper,
  CircularProgress,
  Button,
  Alert,
  Link,
} from '@mui/material';
import {
  Send as SendIcon,
  Stop as StopIcon,
  DeleteOutline as ClearIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { useClaudeCode, type ChatMessage } from '../../hooks/useClaudeCode';
import ReactMarkdown from 'react-markdown';
import { ActionBlock, parseActionBlocks, removeActionBlocks } from './ActionBlock';

interface ChatPanelProps {
  /** Height of the panel (default: 100%) */
  height?: string | number;
  /** Show the clear history button */
  showClearButton?: boolean;
  /** Compact mode for smaller displays */
  compact?: boolean;
}

/**
 * Message bubble component
 */
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  // Parse action blocks from assistant messages
  const actionBlocks = !isUser && !message.isStreaming
    ? parseActionBlocks(message.content)
    : [];
  const displayContent = actionBlocks.length > 0
    ? removeActionBlocks(message.content)
    : message.content;

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
      }}
    >
      {/* Avatar and role indicator */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          mb: 0.5,
          color: 'text.secondary',
        }}
      >
        {isUser ? (
          <>
            <Typography variant="caption">You</Typography>
            <PersonIcon sx={{ fontSize: 16 }} />
          </>
        ) : (
          <>
            <BotIcon sx={{ fontSize: 16, color: 'primary.main' }} />
            <Typography variant="caption" sx={{ color: 'primary.main' }}>
              Assistant
            </Typography>
          </>
        )}
      </Box>

      {/* Message content */}
      <Paper
        elevation={0}
        sx={{
          maxWidth: '85%',
          p: 1.5,
          borderRadius: 2,
          bgcolor: isUser ? 'primary.main' : 'background.paper',
          color: isUser ? 'primary.contrastText' : 'text.primary',
          border: isUser ? 'none' : '1px solid',
          borderColor: 'divider',
        }}
      >
        {message.isStreaming && !message.content ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CircularProgress size={16} />
            <Typography variant="body2" color="text.secondary">
              Thinking...
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              '& p': { m: 0, mb: 1 },
              '& p:last-child': { mb: 0 },
              '& pre': {
                bgcolor: 'rgba(0,0,0,0.1)',
                p: 1,
                borderRadius: 1,
                overflow: 'auto',
                fontSize: '0.85rem',
              },
              '& code': {
                bgcolor: 'rgba(0,0,0,0.1)',
                px: 0.5,
                borderRadius: 0.5,
                fontFamily: 'monospace',
                fontSize: '0.9em',
              },
              '& ul, & ol': { pl: 2, m: 0, mb: 1 },
              '& li': { mb: 0.5 },
            }}
          >
            <ReactMarkdown>{displayContent}</ReactMarkdown>
          </Box>
        )}

        {/* Render action blocks for assistant messages */}
        {actionBlocks.length > 0 && (
          <Box sx={{ mt: 1 }}>
            {actionBlocks.map((action, index) => (
              <ActionBlock
                key={`${action.action}-${index}`}
                action={action}
              />
            ))}
          </Box>
        )}

        {message.error && (
          <Typography variant="caption" color="error" sx={{ display: 'block', mt: 1 }}>
            Error: {message.error}
          </Typography>
        )}
      </Paper>

      {/* Timestamp */}
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ mt: 0.5, fontSize: '0.7rem' }}
      >
        {message.timestamp.toLocaleTimeString()}
      </Typography>
    </Box>
  );
}

/**
 * Not available message when Claude Code is not installed
 */
function NotAvailableMessage() {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        p: 3,
        textAlign: 'center',
      }}
    >
      <BotIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
      <Typography variant="h6" gutterBottom>
        Claude Code Not Found
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        The Toolbox Assistant requires Claude Code CLI to be installed on your system.
      </Typography>
      <Alert severity="info" sx={{ maxWidth: 400, textAlign: 'left' }}>
        <Typography variant="body2">
          To install Claude Code, run:
        </Typography>
        <Box
          component="pre"
          sx={{
            bgcolor: 'background.default',
            p: 1,
            borderRadius: 1,
            mt: 1,
            overflow: 'auto',
          }}
        >
          npm install -g @anthropic-ai/claude-code
        </Box>
        <Typography variant="body2" sx={{ mt: 1 }}>
          Or visit{' '}
          <Link
            href="https://claude.ai/claude-code"
            target="_blank"
            rel="noopener noreferrer"
          >
            claude.ai/claude-code
          </Link>{' '}
          for more information.
        </Typography>
      </Alert>
    </Box>
  );
}

/**
 * Welcome message for new chat
 */
function WelcomeMessage() {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        p: 3,
        textAlign: 'center',
      }}
    >
      <BotIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
      <Typography variant="h6" gutterBottom>
        Toolbox Assistant
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 400 }}>
        I'm your AI assistant for Ignition Toolbox. I can see all your playbooks,
        executions, and logs - and I can run playbooks, control executions,
        and diagnose issues for you.
      </Typography>
      <Box sx={{ mt: 3, display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Try asking:
        </Typography>
      </Box>
      <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
          "Show me all gateway playbooks"
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
          "Run the Gateway Login playbook"
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
          "Why did my last execution fail?"
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
          "What's the system status?"
        </Typography>
      </Box>
    </Box>
  );
}

/**
 * Main ChatPanel component
 */
export function ChatPanel({
  height = '100%',
  showClearButton = true,
  compact = false,
}: ChatPanelProps) {
  const {
    isAvailable,
    isCheckingAvailability,
    isLoading,
    messages,
    sendMessage,
    clearHistory,
    cancelQuery,
  } = useClaudeCode();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    if (isAvailable && !isCheckingAvailability) {
      inputRef.current?.focus();
    }
  }, [isAvailable, isCheckingAvailability]);

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      sendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Show loading state while checking availability
  if (isCheckingAvailability) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height,
        }}
      >
        <CircularProgress size={32} />
      </Box>
    );
  }

  // Show not available message if Claude Code is not installed
  if (!isAvailable) {
    return <NotAvailableMessage />;
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height,
        overflow: 'hidden',
      }}
    >
      {/* Header with clear button */}
      {showClearButton && messages.length > 0 && (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'flex-end',
            p: 1,
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Button
            size="small"
            startIcon={<ClearIcon />}
            onClick={clearHistory}
            sx={{ textTransform: 'none' }}
          >
            Clear Chat
          </Button>
        </Box>
      )}

      {/* Messages area */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: compact ? 1 : 2,
        }}
      >
        {messages.length === 0 ? (
          <WelcomeMessage />
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </Box>

      {/* Input area */}
      <Box
        sx={{
          p: compact ? 1 : 2,
          borderTop: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
        }}
      >
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            inputRef={inputRef}
            fullWidth
            placeholder="Ask me anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            size={compact ? 'small' : 'medium'}
            multiline
            maxRows={4}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              },
            }}
          />
          {isLoading ? (
            <IconButton
              color="error"
              onClick={cancelQuery}
              sx={{ alignSelf: 'flex-end' }}
            >
              <StopIcon />
            </IconButton>
          ) : (
            <IconButton
              color="primary"
              onClick={handleSend}
              disabled={!input.trim()}
              sx={{ alignSelf: 'flex-end' }}
            >
              <SendIcon />
            </IconButton>
          )}
        </Box>
      </Box>
    </Box>
  );
}
