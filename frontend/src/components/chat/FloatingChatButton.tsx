/**
 * FloatingChatButton - Floating chat panel that doesn't block page interaction
 *
 * Provides quick access to Clawdbot from any page in the application.
 * The chat panel floats above the content and can be minimized/resized.
 */

import { useState, useRef, useEffect } from 'react';
import {
  Fab,
  Box,
  IconButton,
  Typography,
  Paper,
  Tooltip,
  Collapse,
} from '@mui/material';
import {
  SmartToy as BotIcon,
  Close as CloseIcon,
  Remove as MinimizeIcon,
  OpenInFull as ExpandIcon,
  DragIndicator as DragIcon,
} from '@mui/icons-material';
import { ChatPanel } from './ChatPanel';
import { useClaudeCode } from '../../hooks/useClaudeCode';

interface FloatingChatButtonProps {
  /** Hide the button (e.g., on the Chat page) */
  hidden?: boolean;
}

// Panel size options
type PanelSize = 'compact' | 'normal' | 'large';

const PANEL_SIZES: Record<PanelSize, { width: number; height: number }> = {
  compact: { width: 360, height: 400 },
  normal: { width: 420, height: 520 },
  large: { width: 500, height: 650 },
};

/**
 * Floating chat panel component
 */
export function FloatingChatButton({ hidden = false }: FloatingChatButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [panelSize, setPanelSize] = useState<PanelSize>('normal');
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{ startX: number; startY: number; startPosX: number; startPosY: number } | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const { isAvailable, isCheckingAvailability } = useClaudeCode();

  // Initialize position on first open
  useEffect(() => {
    if (isOpen && position.x === 0 && position.y === 0) {
      // Position in bottom-right with some padding
      const size = PANEL_SIZES[panelSize];
      setPosition({
        x: window.innerWidth - size.width - 24,
        y: window.innerHeight - size.height - 80,
      });
    }
  }, [isOpen, panelSize, position.x, position.y]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (isOpen) {
        const size = PANEL_SIZES[panelSize];
        setPosition((prev) => ({
          x: Math.min(prev.x, window.innerWidth - size.width - 24),
          y: Math.min(prev.y, window.innerHeight - size.height - 24),
        }));
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isOpen, panelSize]);

  // Don't render if hidden
  if (hidden) {
    return null;
  }

  const handleOpen = () => {
    setIsOpen(true);
    setIsMinimized(false);
  };

  const handleClose = () => {
    setIsOpen(false);
  };

  const handleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  const handleCycleSize = () => {
    const sizes: PanelSize[] = ['compact', 'normal', 'large'];
    const currentIndex = sizes.indexOf(panelSize);
    const nextIndex = (currentIndex + 1) % sizes.length;
    setPanelSize(sizes[nextIndex]);
  };

  // Drag handlers
  const handleDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startPosX: position.x,
      startPosY: position.y,
    };

    const handleDragMove = (moveEvent: MouseEvent) => {
      if (dragRef.current) {
        const deltaX = moveEvent.clientX - dragRef.current.startX;
        const deltaY = moveEvent.clientY - dragRef.current.startY;
        const size = PANEL_SIZES[panelSize];

        // Clamp position to viewport
        const newX = Math.max(0, Math.min(
          window.innerWidth - size.width,
          dragRef.current.startPosX + deltaX
        ));
        const newY = Math.max(0, Math.min(
          window.innerHeight - size.height,
          dragRef.current.startPosY + deltaY
        ));

        setPosition({ x: newX, y: newY });
      }
    };

    const handleDragEnd = () => {
      setIsDragging(false);
      dragRef.current = null;
      document.removeEventListener('mousemove', handleDragMove);
      document.removeEventListener('mouseup', handleDragEnd);
    };

    document.addEventListener('mousemove', handleDragMove);
    document.addEventListener('mouseup', handleDragEnd);
  };

  // Tooltip text based on availability
  const getTooltipText = () => {
    if (isCheckingAvailability) {
      return 'Checking Claude Code availability...';
    }
    if (!isAvailable) {
      return 'Install Claude Code for AI features';
    }
    return 'Chat with Clawdbot';
  };

  const size = PANEL_SIZES[panelSize];

  return (
    <>
      {/* Floating Action Button - shown when panel is closed */}
      {!isOpen && (
        <Tooltip title={getTooltipText()} placement="left">
          <Fab
            color="primary"
            aria-label="open chat"
            onClick={handleOpen}
            sx={{
              position: 'fixed',
              bottom: 24,
              right: 24,
              zIndex: 1200,
              // Subtle pulse animation when available
              ...(isAvailable && {
                animation: 'pulse-subtle 3s ease-in-out infinite',
                '@keyframes pulse-subtle': {
                  '0%, 100%': { boxShadow: '0 4px 20px rgba(59, 130, 246, 0.3)' },
                  '50%': { boxShadow: '0 4px 30px rgba(59, 130, 246, 0.5)' },
                },
              }),
              // Dimmed when not available
              ...(!isAvailable && !isCheckingAvailability && {
                opacity: 0.6,
                '&:hover': {
                  opacity: 0.8,
                },
              }),
            }}
          >
            <BotIcon />
          </Fab>
        </Tooltip>
      )}

      {/* Floating Chat Panel */}
      {isOpen && (
        <Paper
          ref={panelRef}
          elevation={8}
          sx={{
            position: 'fixed',
            left: position.x,
            top: position.y,
            width: size.width,
            zIndex: 1300,
            borderRadius: 2,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            transition: isDragging ? 'none' : 'width 0.2s, height 0.2s',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          {/* Header - Draggable */}
          <Box
            onMouseDown={handleDragStart}
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              p: 1,
              pl: 1.5,
              bgcolor: 'primary.main',
              color: 'primary.contrastText',
              cursor: isDragging ? 'grabbing' : 'grab',
              userSelect: 'none',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <DragIcon sx={{ fontSize: 18, opacity: 0.7 }} />
              <BotIcon sx={{ fontSize: 20 }} />
              <Typography variant="subtitle2" fontWeight="medium">
                Clawdbot
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 0.25 }}>
              <Tooltip title={`Size: ${panelSize}`}>
                <IconButton
                  size="small"
                  onClick={handleCycleSize}
                  sx={{ color: 'inherit', p: 0.5 }}
                >
                  <ExpandIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
              <Tooltip title={isMinimized ? 'Expand' : 'Minimize'}>
                <IconButton
                  size="small"
                  onClick={handleMinimize}
                  sx={{ color: 'inherit', p: 0.5 }}
                >
                  <MinimizeIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
              <Tooltip title="Close">
                <IconButton
                  size="small"
                  onClick={handleClose}
                  sx={{ color: 'inherit', p: 0.5 }}
                >
                  <CloseIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {/* Chat Content - Collapsible */}
          <Collapse in={!isMinimized}>
            <Box
              sx={{
                height: size.height - 44, // Subtract header height
                bgcolor: 'background.paper',
              }}
            >
              <ChatPanel height="100%" showClearButton={false} compact />
            </Box>
          </Collapse>
        </Paper>
      )}
    </>
  );
}
