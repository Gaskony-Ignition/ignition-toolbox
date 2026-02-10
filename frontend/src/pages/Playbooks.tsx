/**
 * Playbooks page - List and execute playbooks organized by category
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button,
  IconButton,
  Tooltip,
  Badge,
  Snackbar,
  Alert as MuiAlert,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Upload as UploadIcon,
  Refresh as RefreshIcon,
  DragIndicator as DragIcon,
  Add as AddIcon,
  Store as StoreIcon,
  SystemUpdate as UpdateIcon,
  RestartAlt as ResetIcon,
} from '@mui/icons-material';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { createLogger } from '../utils/logger';
import { PlaybookCard } from '../components/PlaybookCard';

const logger = createLogger('Playbooks');
import { PlaybookExecutionDialog } from '../components/PlaybookExecutionDialog';
import { PlaybookStepsDialog } from '../components/PlaybookStepsDialog';
import { PlaybookLibraryDialog } from '../components/PlaybookLibraryDialog';
import { PlaybookUpdatesDialog } from '../components/PlaybookUpdatesDialog';
import { PlaybookEditorDialog } from '../components/PlaybookEditorDialog';
import { CreatePlaybookDialog } from '../components/CreatePlaybookDialog';
import { useStore } from '../store';
import { useCategoryOrder, useCategoryExpanded, useGroupExpanded } from '../hooks/usePlaybookOrder';
import type { PlaybookInfo } from '../types/api';

// Extracted modules
import { categorizePlaybooks, groupPlaybooks, domainNames } from './PlaybookCategorySection';
import { createCategoryDragEndHandler } from './PlaybookDragHandlers';
import {
  handleExport as doExport,
  handleImport as doImport,
  handleResetMetadata as doResetMetadata,
} from './PlaybookImportExport';

// Sortable playbook card wrapper
function SortablePlaybookCard({ playbook, onConfigure, onExecute, onExport, onViewSteps, onEditPlaybook, dragEnabled }: {
  playbook: PlaybookInfo;
  onConfigure: (playbook: PlaybookInfo) => void;
  onExecute?: (playbook: PlaybookInfo) => void;
  onExport?: (playbook: PlaybookInfo) => void;
  onViewSteps?: (playbook: PlaybookInfo) => void;
  onEditPlaybook?: (playbook: PlaybookInfo) => void;
  dragEnabled: boolean;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: playbook.path, disabled: !dragEnabled });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    cursor: dragEnabled ? 'grab' : 'default',
  };

  return (
    <div ref={setNodeRef} style={style} {...(dragEnabled ? attributes : {})} {...(dragEnabled ? listeners : {})}>
      <PlaybookCard
        playbook={playbook}
        onConfigure={onConfigure}
        onExecute={onExecute}
        onExport={onExport}
        onViewSteps={onViewSteps}
        onEditPlaybook={onEditPlaybook}
      />
    </div>
  );
}

// Sortable accordion wrapper for category reordering
function SortableAccordion({
  categoryId,
  expanded,
  onChange,
  dragEnabled,
  title,
  children
}: {
  categoryId: string;
  expanded: boolean;
  onChange: (event: React.SyntheticEvent, isExpanded: boolean) => void;
  dragEnabled: boolean;
  title: string;
  children: React.ReactNode;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: categoryId, disabled: !dragEnabled });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <Accordion expanded={expanded} onChange={onChange}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          sx={{
            minHeight: '32px !important',
            '& .MuiAccordionSummary-content': { my: '6px !important', display: 'flex', alignItems: 'center', gap: 1 }
          }}
        >
          {dragEnabled && (
            <Box
              {...attributes}
              {...listeners}
              sx={{
                display: 'flex',
                alignItems: 'center',
                cursor: 'grab',
                mr: 1,
                '&:active': { cursor: 'grabbing' }
              }}
            >
              <DragIcon fontSize="small" />
            </Box>
          )}
          <Typography variant="h6" sx={{ fontSize: '1.1rem' }}>{title}</Typography>
        </AccordionSummary>
        <AccordionDetails>
          {children}
        </AccordionDetails>
      </Accordion>
    </div>
  );
}

// Inline utility functions (getPlaybookOrder, savePlaybookOrder, applyOrder,
// categorizePlaybooks, groupPlaybooks) have been extracted to:
// - PlaybookDragHandlers.ts
// - PlaybookCategorySection.tsx

interface PlaybooksProps {
  domainFilter?: 'gateway' | 'designer' | 'perspective';
}

export function Playbooks({ domainFilter }: PlaybooksProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const gap = 2;
  const gridSpacing = 2;
  const playbookGridColumns = useStore((state) => state.playbookGridColumns);

  // Snackbar notification state
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning' | 'info';
  }>({ open: false, message: '', severity: 'info' });

  const showNotification = (message: string, severity: 'success' | 'error' | 'warning' | 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  // Generate responsive grid columns based on max setting
  const getGridColumns = (forCategory = false) => {
    const max = forCategory ? Math.max(3, playbookGridColumns - 1) : playbookGridColumns;
    return {
      xs: '1fr',
      sm: 'repeat(2, 1fr)',
      md: `repeat(${Math.min(3, max)}, 1fr)`,
      lg: `repeat(${Math.min(forCategory ? 3 : 4, max)}, 1fr)`,
      xl: `repeat(${max}, 1fr)`,
    };
  };
  const [selectedPlaybook, setSelectedPlaybook] = useState<PlaybookInfo | null>(null);
  const [dragEnabled, setDragEnabled] = useState(false);
  const [stepsDialogPlaybook, setStepsDialogPlaybook] = useState<PlaybookInfo | null>(null);
  const [editorPlaybook, setEditorPlaybook] = useState<PlaybookInfo | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const { expanded: expandedGroups, toggleExpanded: toggleGroupExpanded } = useGroupExpanded();
  const [libraryDialogOpen, setLibraryDialogOpen] = useState(false);
  const [updatesDialogOpen, setUpdatesDialogOpen] = useState(false);

  // Category order and expanded state (managed by hooks with localStorage persistence)
  const { order: rawCategoryOrder, updateOrder: updateCategoryOrder } = useCategoryOrder();
  const categoryOrder = rawCategoryOrder.length > 0 ? rawCategoryOrder : ['gateway', 'designer', 'perspective'];
  const { expanded: categoryExpanded, setExpanded: setCategoryExpanded } = useCategoryExpanded();

  // Fetch playbooks
  const { data: playbooks = [], isLoading, error } = useQuery<PlaybookInfo[]>({
    queryKey: ['playbooks'],
    queryFn: api.playbooks.list,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch update stats for badge
  const { data: updateStats } = useQuery({
    queryKey: ['playbook-update-stats'],
    queryFn: async () => {
      const response = await fetch(`${api.getBaseUrl()}/api/playbooks/updates/stats`);
      if (!response.ok) return null;
      return response.json();
    },
    refetchInterval: 300000, // Refetch every 5 minutes
  });

  // Categorize playbooks
  const categories = categorizePlaybooks(playbooks);

  // State for each category to enable re-rendering on drag
  const [gatewayPlaybooks, setGatewayPlaybooks] = useState(categories.gateway);
  const [designerPlaybooks, setDesignerPlaybooks] = useState(categories.designer);
  const [perspectivePlaybooks, setPerspectivePlaybooks] = useState(categories.perspective);

  // Update state when playbooks change
  useEffect(() => {
    setGatewayPlaybooks(categories.gateway);
    setDesignerPlaybooks(categories.designer);
    setPerspectivePlaybooks(categories.perspective);

    // Clean up saved configurations for deleted playbooks
    if (playbooks.length > 0) {
      const validPaths = new Set(playbooks.map(p => p.path));
      const keysToRemove: string[] = [];

      // Find all localStorage keys for playbook configurations
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith('playbook_config_') || key?.startsWith('playbook_debug_') || key?.startsWith('playbook_order_')) {
          // Extract playbook path from key
          if (key.startsWith('playbook_config_')) {
            const playbookPath = key.replace('playbook_config_', '');
            if (!validPaths.has(playbookPath)) {
              keysToRemove.push(key);
              // Also remove associated debug mode setting
              keysToRemove.push(`playbook_debug_${playbookPath}`);
            }
          }
        }
      }

      // Remove invalid configurations
      keysToRemove.forEach(key => {
        localStorage.removeItem(key);
        logger.debug(`Removed stale configuration: ${key}`);
      });

      if (keysToRemove.length > 0) {
        logger.debug(`Cleaned up ${keysToRemove.length} stale playbook configurations`);
      }
    }
  }, [playbooks]);

  // Configure drag sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleConfigure = (playbook: PlaybookInfo) => {
    setSelectedPlaybook(playbook);
  };

  const handleExecute = async (playbook: PlaybookInfo) => {
    // v3.45.2 - Non-blocking execution with immediate navigation
    // Get global selected credential
    const selectedCredential = useStore.getState().selectedCredential;

    // Get saved configuration from localStorage
    const savedConfigKey = `playbook_config_${playbook.path}`;
    const savedConfigStr = localStorage.getItem(savedConfigKey);

    // Get debug mode preference
    const debugModeStr = localStorage.getItem(`playbook_debug_${playbook.path}`);
    const debug_mode = debugModeStr === 'true';

    // If global credential is selected, execute directly with it
    if (selectedCredential && !savedConfigStr) {
      logger.debug('Executing playbook with credential:', {
        playbook_path: playbook.path,
        credential_name: selectedCredential.name,
        gateway_url: selectedCredential.gateway_url,
        debug_mode,
      });

      // Start execution (don't await - let it run in background)
      api.executions.start({
        playbook_path: playbook.path,
        parameters: {}, // Backend will auto-fill from credential
        gateway_url: selectedCredential.gateway_url,
        credential_name: selectedCredential.name,
        debug_mode,
      }).then(response => {
        logger.info('Execution started successfully:', response);
        // Navigate to execution detail page AFTER getting execution ID
        navigate(`/executions/${response.execution_id}`);
      }).catch(error => {
        logger.error('Failed to execute playbook:', error);
        logger.error('Error details:', error instanceof Error ? error.message : String(error));
        if (error && typeof error === 'object' && 'data' in error) {
          logger.error('Error data:', (error as { data: unknown }).data);
        }
        showNotification(`Failed to start execution: ${error instanceof Error ? error.message : String(error)}`, 'error');
      });

      // Return immediately without waiting - navigation will happen when API responds
      return;
    }

    if (!savedConfigStr) {
      // No saved config and no global credential - open configure dialog
      setSelectedPlaybook(playbook);
      return;
    }

    // If we have saved config but no credential, open configure dialog
    if (!selectedCredential) {
      setSelectedPlaybook(playbook);
      return;
    }

    try {
      const savedConfig = JSON.parse(savedConfigStr);

      // Convert boolean string values to actual booleans
      const convertedParams: Record<string, string | boolean> = {};
      for (const [key, value] of Object.entries(savedConfig.parameters || {})) {
        // Find the parameter definition
        const paramDef = playbook.parameters.find(p => p.name === key);
        if (paramDef?.type === 'boolean') {
          // Convert string 'true'/'false' to boolean
          convertedParams[key] = value === 'true' || value === true;
        } else {
          convertedParams[key] = value as string;
        }
      }

      // Execute with saved config parameters + global credential (don't await - navigate when ready)
      api.executions.start({
        playbook_path: playbook.path,
        parameters: convertedParams as Record<string, string>, // Use converted params (boolean types fixed)
        gateway_url: selectedCredential.gateway_url, // Always use global credential's gateway_url
        credential_name: selectedCredential.name, // Always use global credential
        debug_mode,
        timeout_overrides: savedConfig.timeoutOverrides, // Include timeout overrides from saved config
      }).then(response => {
        // Navigate to execution detail page AFTER getting execution ID
        navigate(`/executions/${response.execution_id}`);
      }).catch(error => {
        logger.error('Failed to execute playbook:', error);
        showNotification('Failed to start execution. Please check the console for details.', 'error');
      });
    } catch (error) {
      logger.error('Failed to parse saved config:', error);
      showNotification('Failed to load saved configuration. Please try again.', 'error');
    }
  };

  // Unified drag end handlers using parameterized factory (replaces 3 identical handlers)
  const handleGatewayDragEnd = createCategoryDragEndHandler(gatewayPlaybooks, setGatewayPlaybooks, 'gateway');
  const handleDesignerDragEnd = createCategoryDragEndHandler(designerPlaybooks, setDesignerPlaybooks, 'designer');
  const handlePerspectiveDragEnd = createCategoryDragEndHandler(perspectivePlaybooks, setPerspectivePlaybooks, 'perspective');

  // Handle category reordering
  const handleCategoryDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = categoryOrder.indexOf(active.id as string);
      const newIndex = categoryOrder.indexOf(over.id as string);
      const newOrder = arrayMove(categoryOrder, oldIndex, newIndex);
      updateCategoryOrder(newOrder);
    }
  };

  // Handle category expand/collapse
  const handleCategoryExpandChange = (categoryId: string) => (
    _event: React.SyntheticEvent,
    isExpanded: boolean
  ) => {
    setCategoryExpanded(categoryId, isExpanded);
  };

  const handleViewSteps = (playbook: PlaybookInfo) => {
    setStepsDialogPlaybook(playbook);
  };

  const handleEditPlaybook = (playbook: PlaybookInfo) => {
    setEditorPlaybook(playbook);
  };

  // Delegate to extracted modules (import/export/reset use snackbar + queryClient)
  const handleExport = (playbook: PlaybookInfo) => {
    doExport(playbook, showNotification);
  };

  const handleImport = () => {
    doImport(showNotification, queryClient);
  };

  const handleResetMetadata = () => {
    doResetMetadata(showNotification, queryClient);
  };

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['playbooks'] });
    queryClient.invalidateQueries({ queryKey: ['playbook-update-stats'] });
  };

  // Get filtered playbooks based on domainFilter prop
  const getFilteredPlaybooks = () => {
    if (!domainFilter) return null;
    switch (domainFilter) {
      case 'gateway': return gatewayPlaybooks;
      case 'designer': return designerPlaybooks;
      case 'perspective': return perspectivePlaybooks;
      default: return null;
    }
  };

  const filteredPlaybooks = getFilteredPlaybooks();

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5, py: 0.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
          <Typography variant="h5" sx={{ fontSize: '1.3rem' }}>
            {domainFilter ? `${domainNames[domainFilter]} Playbooks` : 'Playbooks'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
            {domainFilter
              ? `${filteredPlaybooks?.length || 0} playbooks available`
              : 'Select a playbook to configure and execute'}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Browse and install playbooks from repository">
            <Button
              variant="contained"
              startIcon={<StoreIcon />}
              onClick={() => setLibraryDialogOpen(true)}
              size="small"
              color="secondary"
            >
              Browse Library
            </Button>
          </Tooltip>

          <Tooltip title="Check for playbook updates">
            <Badge
              badgeContent={updateStats?.total_updates_available || 0}
              color="error"
              invisible={!updateStats?.has_updates}
            >
              <Button
                variant="outlined"
                startIcon={<UpdateIcon />}
                onClick={() => setUpdatesDialogOpen(true)}
                size="small"
                color={updateStats?.has_updates ? "warning" : "primary"}
              >
                Updates
              </Button>
            </Badge>
          </Tooltip>

          <Tooltip title="Create a new playbook from template">
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
              size="small"
              color="primary"
            >
              Create New
            </Button>
          </Tooltip>

          <Tooltip title={dragEnabled ? "Disable drag mode" : "Enable drag mode to reorder playbooks"}>
            <Button
              variant={dragEnabled ? "contained" : "outlined"}
              startIcon={<DragIcon />}
              onClick={() => setDragEnabled(!dragEnabled)}
              size="small"
              color={dragEnabled ? "success" : "primary"}
            >
              {dragEnabled ? "Drag Mode ON" : "Drag Mode"}
            </Button>
          </Tooltip>

          <Tooltip title="Import playbook from JSON export">
            <Button
              variant="outlined"
              startIcon={<UploadIcon />}
              onClick={handleImport}
              size="small"
            >
              Import
            </Button>
          </Tooltip>

          <Tooltip title="Refresh playbook list">
            <IconButton
              onClick={handleRefresh}
              size="small"
              color="primary"
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Reset all playbook metadata (troubleshooting)">
            <IconButton
              onClick={handleResetMetadata}
              size="small"
              color="warning"
            >
              <ResetIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Loading state */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress aria-label="Loading playbooks" />
        </Box>
      )}

      {/* Error state */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load playbooks: {(error as Error).message}
        </Alert>
      )}

      {/* Empty state */}
      {!isLoading && !error && playbooks.length === 0 && (
        <Alert severity="info">
          No playbooks found. Add YAML playbooks to the ./playbooks directory.
        </Alert>
      )}

      {/* Empty state for filtered domain */}
      {!isLoading && !error && domainFilter && filteredPlaybooks && filteredPlaybooks.length === 0 && (
        <Alert severity="info">
          No {domainNames[domainFilter]} playbooks found. Create one or browse the library.
        </Alert>
      )}

      {/* Filtered Domain View (single domain, no accordions) */}
      {!isLoading && !error && domainFilter && filteredPlaybooks && filteredPlaybooks.length > 0 && (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={
          domainFilter === 'gateway' ? handleGatewayDragEnd :
          domainFilter === 'designer' ? handleDesignerDragEnd :
          handlePerspectiveDragEnd
        }>
          <SortableContext items={filteredPlaybooks.map(p => p.path)} strategy={verticalListSortingStrategy}>
            {(() => {
              const { grouped, ungrouped } = groupPlaybooks(filteredPlaybooks);
              return (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap }}>
                  {/* Ungrouped playbooks */}
                  {ungrouped.length > 0 && (
                    <Box
                      sx={{
                        display: 'grid',
                        gridTemplateColumns: getGridColumns(),
                        gap: gridSpacing,
                      }}
                    >
                      {ungrouped.map((playbook) => (
                        <SortablePlaybookCard
                          key={playbook.path}
                          playbook={playbook}
                          onConfigure={handleConfigure}
                          onExecute={handleExecute}
                          onExport={handleExport}
                          onViewSteps={handleViewSteps}
                          onEditPlaybook={handleEditPlaybook}
                          dragEnabled={dragEnabled}
                        />
                      ))}
                    </Box>
                  )}

                  {/* Grouped playbooks */}
                  {Object.entries(grouped).map(([groupName, groupPlaybooks]) => (
                    <Accordion
                      key={groupName}
                      expanded={dragEnabled || (expandedGroups[groupName] !== undefined ? expandedGroups[groupName] : false)}
                      onChange={() => {
                        if (!dragEnabled) {
                          toggleGroupExpanded(groupName);
                        }
                      }}
                      sx={{ bgcolor: 'background.paper', boxShadow: 1 }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: '32px !important', '& .MuiAccordionSummary-content': { my: '6px !important' } }}>
                        <Typography variant="subtitle1" sx={{ fontSize: '0.95rem', fontWeight: 500 }}>
                          {groupName} ({groupPlaybooks.length})
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Box
                          sx={{
                            display: 'grid',
                            gridTemplateColumns: getGridColumns(),
                            gap: gridSpacing,
                          }}
                        >
                          {groupPlaybooks.map((playbook) => (
                            <SortablePlaybookCard
                              key={playbook.path}
                              playbook={playbook}
                              onConfigure={handleConfigure}
                              onExecute={handleExecute}
                              onExport={handleExport}
                              onViewSteps={handleViewSteps}
                              onEditPlaybook={handleEditPlaybook}
                              dragEnabled={dragEnabled}
                            />
                          ))}
                        </Box>
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </Box>
              );
            })()}
          </SortableContext>
        </DndContext>
      )}

      {/* Organized Playbook Sections (all domains, with accordions) */}
      {!isLoading && !error && !domainFilter && (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleCategoryDragEnd}>
          <SortableContext items={categoryOrder} strategy={verticalListSortingStrategy}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap }}>
              {categoryOrder.map((categoryId) => {
                // Category configuration
                const categoryConfig = {
                  gateway: {
                    title: `🔧 Gateway (${gatewayPlaybooks.length})`,
                    playbooks: gatewayPlaybooks,
                    dragHandler: handleGatewayDragEnd,
                    emptyMessage: 'No Gateway playbooks found. Add YAML playbooks to ./playbooks/gateway/',
                  },
                  designer: {
                    title: `🎨 Designer (${designerPlaybooks.length})`,
                    playbooks: designerPlaybooks,
                    dragHandler: handleDesignerDragEnd,
                    emptyMessage: 'No Designer playbooks found. Add YAML playbooks to ./playbooks/designer/',
                  },
                  perspective: {
                    title: `📱 Perspective (${perspectivePlaybooks.length})`,
                    playbooks: perspectivePlaybooks,
                    dragHandler: handlePerspectiveDragEnd,
                    emptyMessage: 'No Perspective playbooks found. Add YAML playbooks to ./playbooks/perspective/ or ./playbooks/browser/',
                  },
                }[categoryId];

                if (!categoryConfig) return null;

                return (
                  <SortableAccordion
                    key={categoryId}
                    categoryId={categoryId}
                    expanded={categoryExpanded[categoryId] ?? true}
                    onChange={handleCategoryExpandChange(categoryId)}
                    dragEnabled={dragEnabled}
                    title={categoryConfig.title}
                  >
                    {categoryConfig.playbooks.length > 0 ? (
                      (() => {
                        // Special handling for gateway (has groups)
                        if (categoryId === 'gateway') {
                          const { grouped, ungrouped } = groupPlaybooks(categoryConfig.playbooks);
                          // Collect all playbook IDs for single DndContext
                          const allPlaybookIds = categoryConfig.playbooks.map(p => p.path);

                          return (
                            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={categoryConfig.dragHandler}>
                              <SortableContext items={allPlaybookIds} strategy={verticalListSortingStrategy}>
                                <Box sx={{ display: 'flex', flexDirection: 'column', gap }}>
                                  {/* Ungrouped playbooks */}
                                  {ungrouped.length > 0 && (
                                    <Box
                                      sx={{
                                        display: 'grid',
                                        gridTemplateColumns: getGridColumns(true),
                                        gap: gridSpacing,
                                      }}
                                    >
                                      {ungrouped.map((playbook) => (
                                        <SortablePlaybookCard
                                          key={playbook.path}
                                          playbook={playbook}
                                          onConfigure={handleConfigure}
                                          onExecute={handleExecute}
                                          onExport={handleExport}
                                          onViewSteps={handleViewSteps}
                                          onEditPlaybook={handleEditPlaybook}
                                          dragEnabled={dragEnabled}
                                        />
                                      ))}
                                    </Box>
                                  )}

                                  {/* Grouped playbooks */}
                                  {Object.entries(grouped).map(([groupName, groupPlaybooks]) => (
                                    <Accordion
                                      key={groupName}
                                      expanded={dragEnabled || (expandedGroups[groupName] !== undefined ? expandedGroups[groupName] : false)}
                                      onChange={() => {
                                        if (!dragEnabled) {
                                          toggleGroupExpanded(groupName);
                                        }
                                      }}
                                      sx={{ bgcolor: 'background.paper', boxShadow: 1 }}
                                    >
                                      <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: '32px !important', '& .MuiAccordionSummary-content': { my: '6px !important' } }}>
                                        <Typography variant="subtitle1" sx={{ fontSize: '0.95rem', fontWeight: 500 }}>
                                          📂 {groupName} ({groupPlaybooks.length})
                                        </Typography>
                                      </AccordionSummary>
                                      <AccordionDetails>
                                        <Box
                                          sx={{
                                            display: 'grid',
                                            gridTemplateColumns: getGridColumns(true),
                                            gap: gridSpacing,
                                          }}
                                        >
                                          {groupPlaybooks.map((playbook) => (
                                            <SortablePlaybookCard
                                              key={playbook.path}
                                              playbook={playbook}
                                              onConfigure={handleConfigure}
                                              onExecute={handleExecute}
                                              onExport={handleExport}
                                              onViewSteps={handleViewSteps}
                                              onEditPlaybook={handleEditPlaybook}
                                              dragEnabled={dragEnabled}
                                            />
                                          ))}
                                        </Box>
                                      </AccordionDetails>
                                    </Accordion>
                                  ))}
                                </Box>
                              </SortableContext>
                            </DndContext>
                          );
                        }

                        // Standard rendering for designer and perspective
                        return (
                          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={categoryConfig.dragHandler}>
                            <SortableContext items={categoryConfig.playbooks.map(p => p.path)} strategy={verticalListSortingStrategy}>
                              <Box
                                sx={{
                                  display: 'grid',
                                  gridTemplateColumns: getGridColumns(true),
                                  gap: gridSpacing,
                                }}
                              >
                                {categoryConfig.playbooks.map((playbook) => (
                                  <SortablePlaybookCard
                                    key={playbook.path}
                                    playbook={playbook}
                                    onConfigure={handleConfigure}
                                    onExecute={handleExecute}
                                    onExport={handleExport}
                                    onViewSteps={handleViewSteps}
                                    onEditPlaybook={handleEditPlaybook}
                                    dragEnabled={dragEnabled}
                                  />
                                ))}
                              </Box>
                            </SortableContext>
                          </DndContext>
                        );
                      })()
                    ) : (
                      <Alert severity="info">
                        {categoryConfig.emptyMessage}
                      </Alert>
                    )}
                  </SortableAccordion>
                );
              })}
            </Box>
          </SortableContext>
        </DndContext>
      )}

      {/* Execution dialog */}
      <PlaybookExecutionDialog
        open={selectedPlaybook !== null}
        playbook={selectedPlaybook}
        onClose={() => setSelectedPlaybook(null)}
      />

      {/* Steps dialog */}
      <PlaybookStepsDialog
        open={stepsDialogPlaybook !== null}
        playbook={stepsDialogPlaybook}
        onClose={() => setStepsDialogPlaybook(null)}
      />

      {/* Create New Playbook Dialog */}
      <CreatePlaybookDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        defaultDomain={domainFilter || 'gateway'}
        queryClient={queryClient}
        showNotification={showNotification}
      />

      {/* Playbook Library Dialog */}
      <PlaybookLibraryDialog
        open={libraryDialogOpen}
        onClose={() => setLibraryDialogOpen(false)}
      />

      {/* Playbook Updates Dialog */}
      <PlaybookUpdatesDialog
        open={updatesDialogOpen}
        onClose={() => setUpdatesDialogOpen(false)}
      />

      {/* Playbook Editor Dialog (Form-based) */}
      <PlaybookEditorDialog
        open={editorPlaybook !== null}
        playbook={editorPlaybook}
        onClose={() => setEditorPlaybook(null)}
        onSaved={() => {
          // Optionally refresh the playbooks list
        }}
      />

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <MuiAlert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </MuiAlert>
      </Snackbar>

    </Box>
  );
}
