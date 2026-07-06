/**
 * Composer wizard — "Structure" step: a tree editor for the composition's
 * member folders/tags (add/remove/rename at any depth) plus a detail
 * editor for whichever tag is currently selected.
 */

import { useState } from 'react';
import { Box, Typography, IconButton, Button, Paper, TextField, Stack, FormControl, InputLabel, Select, MenuItem, Chip } from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ChevronRight as ChevronRightIcon,
  CreateNewFolder as AddFolderIcon,
  Add as AddTagIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import type { UdtComposition, UdtCompositionMember, UdtCompositionTag, UdtDataType, UdtValueSource } from '../../types/api';
import { getMemberAt, updateMemberAt, removeMemberAt, addChildAt, blankFolder, blankTag, type Path } from './treeUtils';
import { DATA_TYPES, isAnalogDataType } from './udtConstants';

function pathsEqual(a: Path | null, b: Path): boolean {
  return a !== null && a.length === b.length && a.every((v, i) => v === b[i]);
}

interface MemberNodeProps {
  member: UdtCompositionMember;
  path: Path;
  depth: number;
  selectedPath: Path | null;
  onSelect: (path: Path) => void;
  onAddChild: (parentPath: Path, kind: 'folder' | 'tag') => void;
  onRemove: (path: Path) => void;
  onRename: (path: Path, name: string) => void;
}

function MemberNode({ member, path, depth, selectedPath, onSelect, onAddChild, onRemove, onRename }: MemberNodeProps) {
  const [expanded, setExpanded] = useState(true);
  const isSelected = pathsEqual(selectedPath, path);
  const isFolder = member.kind === 'folder';

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          pl: depth * 2,
          py: 0.25,
          borderRadius: 1,
          bgcolor: isSelected ? 'action.selected' : undefined,
        }}
      >
        {isFolder ? (
          <IconButton size="small" onClick={() => setExpanded((v) => !v)} aria-label={expanded ? 'Collapse' : 'Expand'}>
            {expanded ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
          </IconButton>
        ) : (
          <Box sx={{ width: 32 }} />
        )}
        <Chip
          label={isFolder ? 'folder' : member.data_type}
          size="small"
          variant="outlined"
          sx={{ height: 20, fontSize: '0.65rem' }}
        />
        <TextField
          value={member.name}
          onChange={(e) => onRename(path, e.target.value)}
          onFocus={() => onSelect(path)}
          onClick={() => onSelect(path)}
          size="small"
          variant="standard"
          sx={{ flex: 1, minWidth: 60 }}
          slotProps={{ htmlInput: { 'aria-label': `${isFolder ? 'Folder' : 'Tag'} name` } }}
        />
        {isFolder && (
          <>
            <IconButton size="small" onClick={() => onAddChild(path, 'folder')} aria-label={`Add folder to ${member.name}`}>
              <AddFolderIcon fontSize="small" />
            </IconButton>
            <IconButton size="small" onClick={() => onAddChild(path, 'tag')} aria-label={`Add tag to ${member.name}`}>
              <AddTagIcon fontSize="small" />
            </IconButton>
          </>
        )}
        <IconButton size="small" onClick={() => onRemove(path)} aria-label={`Remove ${member.name}`}>
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Box>
      {isFolder && expanded && (
        <Box>
          {member.members.map((child, index) => (
            <MemberNode
              key={index}
              member={child}
              path={[...path, index]}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
              onAddChild={onAddChild}
              onRemove={onRemove}
              onRename={onRename}
            />
          ))}
        </Box>
      )}
    </Box>
  );
}

interface TagDetailEditorProps {
  tag: UdtCompositionTag;
  onChange: (patch: Partial<UdtCompositionTag>) => void;
}

function TagDetailEditor({ tag, onChange }: TagDetailEditorProps) {
  const analog = isAnalogDataType(tag.data_type);

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle2">Tag settings — {tag.name}</Typography>

      <FormControl size="small" fullWidth>
        <InputLabel id="value-source-label">Value source</InputLabel>
        <Select
          labelId="value-source-label"
          label="Value source"
          value={tag.value_source}
          onChange={(e) => onChange({ value_source: e.target.value as UdtValueSource })}
        >
          <MenuItem value="opc">OPC</MenuItem>
          <MenuItem value="memory">Memory</MenuItem>
          <MenuItem value="expression">Expression</MenuItem>
        </Select>
      </FormControl>

      <FormControl size="small" fullWidth>
        <InputLabel id="data-type-label">Data type</InputLabel>
        <Select
          labelId="data-type-label"
          label="Data type"
          value={tag.data_type}
          onChange={(e) => onChange({ data_type: e.target.value as UdtDataType })}
        >
          {DATA_TYPES.map((dt) => (
            <MenuItem key={dt} value={dt}>
              {dt}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {tag.value_source === 'opc' && (
        <>
          <TextField
            label="OPC item path"
            value={tag.opc_item_path ?? ''}
            onChange={(e) => onChange({ opc_item_path: e.target.value })}
            size="small"
            fullWidth
            helperText="Supports {ParamName} references, e.g. ns=1;s={DevicePath}/Speed"
          />
          <TextField
            label="OPC server"
            value={tag.opc_server ?? ''}
            onChange={(e) => onChange({ opc_server: e.target.value })}
            size="small"
            fullWidth
          />
        </>
      )}

      {tag.value_source === 'memory' && (
        <TextField
          label="Value"
          value={tag.value ?? ''}
          onChange={(e) => onChange({ value: e.target.value })}
          size="small"
          fullWidth
        />
      )}

      {tag.value_source === 'expression' && (
        <TextField
          label="Expression"
          value={tag.expression ?? ''}
          onChange={(e) => onChange({ expression: e.target.value })}
          size="small"
          fullWidth
          multiline
          minRows={2}
        />
      )}

      {analog && (
        <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
          <TextField
            label="Eng unit"
            value={tag.eng_unit ?? ''}
            onChange={(e) => onChange({ eng_unit: e.target.value })}
            size="small"
            sx={{ flex: '1 1 100px' }}
          />
          <TextField
            label="Eng low"
            type="number"
            value={tag.eng_low ?? ''}
            onChange={(e) => onChange({ eng_low: e.target.value === '' ? undefined : Number(e.target.value) })}
            size="small"
            sx={{ flex: '1 1 100px' }}
          />
          <TextField
            label="Eng high"
            type="number"
            value={tag.eng_high ?? ''}
            onChange={(e) => onChange({ eng_high: e.target.value === '' ? undefined : Number(e.target.value) })}
            size="small"
            sx={{ flex: '1 1 100px' }}
          />
        </Box>
      )}

      <TextField
        label="Documentation"
        value={tag.documentation ?? ''}
        onChange={(e) => onChange({ documentation: e.target.value })}
        size="small"
        fullWidth
        multiline
        minRows={2}
      />
      <TextField
        label="Tooltip"
        value={tag.tooltip ?? ''}
        onChange={(e) => onChange({ tooltip: e.target.value })}
        size="small"
        fullWidth
      />
    </Stack>
  );
}

interface MemberTreeEditorProps {
  composition: UdtComposition;
  onChange: (updater: (c: UdtComposition) => UdtComposition) => void;
}

export function MemberTreeEditor({ composition, onChange }: MemberTreeEditorProps) {
  const [selectedPath, setSelectedPath] = useState<Path | null>(null);

  const addMember = (parentPath: Path, kind: 'folder' | 'tag') => {
    const newMember = kind === 'folder' ? blankFolder('newFolder') : blankTag('newTag');
    onChange((c) => ({ ...c, members: addChildAt(c.members, parentPath, newMember) }));
  };

  const removeMember = (path: Path) => {
    onChange((c) => ({ ...c, members: removeMemberAt(c.members, path) }));
    setSelectedPath((prev) => (pathsEqual(prev, path) ? null : prev));
  };

  const renameMember = (path: Path, name: string) => {
    onChange((c) => ({ ...c, members: updateMemberAt(c.members, path, (m) => ({ ...m, name })) }));
  };

  const updateTag = (path: Path, patch: Partial<UdtCompositionTag>) => {
    onChange((c) => ({
      ...c,
      members: updateMemberAt(c.members, path, (m) => (m.kind === 'tag' ? { ...m, ...patch } : m)),
    }));
  };

  const selectedMember = selectedPath ? getMemberAt(composition.members, selectedPath) : null;
  const selectedTag = selectedMember && selectedMember.kind === 'tag' ? selectedMember : null;

  return (
    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
      <Paper variant="outlined" sx={{ flex: '1 1 340px', minWidth: 300, p: 1.5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2">Structure</Typography>
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <Button size="small" startIcon={<AddFolderIcon />} onClick={() => addMember([], 'folder')} data-testid="add-root-folder">
              Folder
            </Button>
            <Button size="small" startIcon={<AddTagIcon />} onClick={() => addMember([], 'tag')} data-testid="add-root-tag">
              Tag
            </Button>
          </Box>
        </Box>

        {composition.members.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No members yet. Add a folder or tag to get started.
          </Typography>
        ) : (
          composition.members.map((member, index) => (
            <MemberNode
              key={index}
              member={member}
              path={[index]}
              depth={0}
              selectedPath={selectedPath}
              onSelect={setSelectedPath}
              onAddChild={addMember}
              onRemove={removeMember}
              onRename={renameMember}
            />
          ))
        )}
      </Paper>

      <Paper variant="outlined" sx={{ flex: '1 1 380px', minWidth: 320, p: 1.5 }}>
        {selectedTag ? (
          <TagDetailEditor tag={selectedTag} onChange={(patch) => updateTag(selectedPath!, patch)} />
        ) : selectedMember ? (
          <Typography variant="body2" color="text.secondary">
            Folder &quot;{selectedMember.name}&quot; — add tags or subfolders to it from the tree on the left.
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Select a tag in the tree to edit its settings.
          </Typography>
        )}
      </Paper>
    </Box>
  );
}
