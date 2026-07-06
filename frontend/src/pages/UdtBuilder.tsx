/**
 * UDT Builder page
 *
 * Pick a device-class template -> fill in a dynamic questionnaire form
 * rendered from the template's schema -> preview the generated UDT JSON ->
 * download or copy it. Download-JSON-only delivery (Nigel-ratified
 * 2026-07-06): nothing here pushes to a gateway, the user imports the
 * downloaded file into Designer (Tag Browser -> Import) themselves.
 */

import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Card,
  CardActionArea,
  CardContent,
  TextField,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  InputLabel,
  FormControl,
  Button,
  Alert,
  Paper,
  Stack,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  Download as DownloadIcon,
  ContentCopy as CopyIcon,
  Visibility as PreviewIcon,
} from '@mui/icons-material';
import { api, APIError } from '../api/client';
import { JsonViewer } from '../components/api-explorer/JsonViewer';
import type { UdtQuestionnaireField, UdtTemplateMeta } from '../types/api';

type AnswerValue = string | number | boolean;
type Answers = Record<string, AnswerValue>;

// ============================================================================
// Answer defaults + field-level validation-error mapping
// ============================================================================

function defaultAnswerFor(field: UdtQuestionnaireField): AnswerValue {
  if (field.default !== null && field.default !== undefined) return field.default;
  if (field.type === 'boolean') return false;
  if (field.type === 'integer' || field.type === 'float') return 0;
  return '';
}

function defaultAnswers(fields: UdtQuestionnaireField[]): Answers {
  const answers: Answers = {};
  for (const field of fields) {
    answers[field.name] = defaultAnswerFor(field);
  }
  return answers;
}

/**
 * Best-effort split of the backend's joined 422 validation message (e.g.
 * "Invalid answers: missing required field 'device_path'; 'eng_unit' must be
 * a string") into per-field errors (shown inline next to the offending
 * field) and a leftover general list (shown as a summary alert). A clause
 * that doesn't name a known questionnaire field — e.g. "unknown field(s):
 * foo" — always falls back to the summary.
 */
function splitFieldErrors(
  message: string,
  fieldNames: Set<string>
): { fieldErrors: Record<string, string>; general: string[] } {
  const withoutPrefix = message.replace(/^Invalid answers:\s*/, '');
  const clauses = withoutPrefix
    .split(';')
    .map((clause) => clause.trim())
    .filter(Boolean);

  const fieldErrors: Record<string, string> = {};
  const general: string[] = [];
  for (const clause of clauses) {
    const match = clause.match(/'([^']+)'/);
    if (match && fieldNames.has(match[1])) {
      fieldErrors[match[1]] = clause;
    } else {
      general.push(clause);
    }
  }
  return { fieldErrors, general };
}

// ============================================================================
// Dynamic questionnaire field input
// ============================================================================

interface QuestionnaireFieldInputProps {
  field: UdtQuestionnaireField;
  value: AnswerValue | undefined;
  error?: string;
  onChange: (value: AnswerValue) => void;
}

function QuestionnaireFieldInput({ field, value, error, onChange }: QuestionnaireFieldInputProps) {
  const label = field.required ? `${field.name} *` : field.name;

  if (field.type === 'boolean') {
    return (
      <Box>
        <FormControlLabel
          control={<Switch checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />}
          label={label}
        />
        {field.description && (
          <Typography variant="caption" color="text.secondary" display="block">
            {field.description}
          </Typography>
        )}
        {error && (
          <Typography variant="caption" color="error" display="block">
            {error}
          </Typography>
        )}
      </Box>
    );
  }

  const isNumeric = field.type === 'integer' || field.type === 'float';

  return (
    <TextField
      label={label}
      value={value ?? ''}
      onChange={(e) => {
        const raw = e.target.value;
        if (!isNumeric) {
          onChange(raw);
          return;
        }
        if (raw === '') {
          onChange('');
          return;
        }
        const parsed = field.type === 'integer' ? parseInt(raw, 10) : parseFloat(raw);
        onChange(Number.isNaN(parsed) ? raw : parsed);
      }}
      type={isNumeric ? 'number' : 'text'}
      size="small"
      fullWidth
      required={field.required}
      error={Boolean(error)}
      helperText={error ?? field.description}
      slotProps={{ htmlInput: { 'aria-label': field.name } }}
    />
  );
}

// ============================================================================
// Template picker
// ============================================================================

interface TemplatePickerProps {
  templates: UdtTemplateMeta[];
  selectedId: string | null;
  onSelect: (template: UdtTemplateMeta) => void;
}

function TemplatePicker({ templates, selectedId, onSelect }: TemplatePickerProps) {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: 2,
        mb: 3,
      }}
    >
      {templates.map((template) => (
        <Card
          key={template.id}
          variant="outlined"
          sx={{
            borderColor: selectedId === template.id ? 'primary.main' : undefined,
            borderWidth: selectedId === template.id ? 2 : 1,
          }}
        >
          <CardActionArea onClick={() => onSelect(template)} data-testid={`template-card-${template.id}`}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                {template.label}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {template.description}
              </Typography>
            </CardContent>
          </CardActionArea>
        </Card>
      ))}
    </Box>
  );
}

// ============================================================================
// Main UdtBuilder page
// ============================================================================

export function UdtBuilder() {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Answers>({});
  const [namingStyle, setNamingStyle] = useState<string>('');

  const templatesQuery = useQuery({
    queryKey: ['udt-templates'],
    queryFn: api.udt.getTemplates,
  });

  const buildMutation = useMutation({
    mutationFn: (vars: { templateId: string; answers: Answers; namingStyle: string }) =>
      api.udt.build(vars.templateId, vars.answers, vars.namingStyle || undefined),
  });

  const templates = useMemo(() => templatesQuery.data ?? [], [templatesQuery.data]);
  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId) ?? null;

  const handleSelectTemplate = (template: UdtTemplateMeta) => {
    setSelectedTemplateId(template.id);
    setAnswers(defaultAnswers(template.questionnaire));
    setNamingStyle(template.default_naming_style);
    buildMutation.reset();
  };

  const handleFieldChange = (name: string, value: AnswerValue) => {
    setAnswers((prev) => ({ ...prev, [name]: value }));
  };

  const handlePreview = () => {
    if (!selectedTemplate) return;
    buildMutation.mutate({ templateId: selectedTemplate.id, answers, namingStyle });
  };

  const handleCopy = async () => {
    if (!buildMutation.data) return;
    await navigator.clipboard.writeText(JSON.stringify(buildMutation.data.udt, null, 2));
  };

  const handleDownload = () => {
    if (!buildMutation.data) return;
    const blob = new Blob([JSON.stringify(buildMutation.data.udt, null, 2)], {
      type: 'application/json',
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = buildMutation.data.filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  const fieldNames = useMemo(
    () => new Set((selectedTemplate?.questionnaire ?? []).map((f) => f.name)),
    [selectedTemplate]
  );

  const { fieldErrors, general } = useMemo(() => {
    if (buildMutation.error instanceof APIError && buildMutation.error.status === 422) {
      return splitFieldErrors(buildMutation.error.message, fieldNames);
    }
    return { fieldErrors: {} as Record<string, string>, general: [] as string[] };
  }, [buildMutation.error, fieldNames]);

  const summaryErrorMessage = (): string | null => {
    if (!buildMutation.isError) return null;
    const error = buildMutation.error;
    if (error instanceof APIError) {
      if (error.status === 422) {
        return general.length > 0 ? general.join('; ') : null;
      }
      return error.getDisplayMessage();
    }
    return 'An unexpected error occurred.';
  };

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" fontWeight={700} gutterBottom>
          UDT Builder
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Answer a short questionnaire for a device class and get back a convention-conforming
          UDT type definition — standardised naming, alarms, history, and documentation, no
          hand-assembly in Designer. Download-only: nothing is pushed to a gateway, import the
          JSON yourself (Tag Browser → Import).
        </Typography>
      </Box>

      {templatesQuery.isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Loading templates…
          </Typography>
        </Box>
      )}

      {templatesQuery.isError && <Alert severity="error">Failed to load UDT templates.</Alert>}

      {templates.length > 0 && (
        <TemplatePicker
          templates={templates}
          selectedId={selectedTemplateId}
          onSelect={handleSelectTemplate}
        />
      )}

      {selectedTemplate && (
        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
          <Paper variant="outlined" sx={{ p: 2, flex: '1 1 400px', minWidth: 320 }}>
            <Typography variant="subtitle1" gutterBottom>
              {selectedTemplate.label} questionnaire
            </Typography>
            <Stack spacing={2}>
              {selectedTemplate.questionnaire.map((field) => (
                <QuestionnaireFieldInput
                  key={field.name}
                  field={field}
                  value={answers[field.name]}
                  error={fieldErrors[field.name]}
                  onChange={(value) => handleFieldChange(field.name, value)}
                />
              ))}

              <FormControl size="small" fullWidth>
                <InputLabel id="udt-naming-style-label">Naming style</InputLabel>
                <Select
                  labelId="udt-naming-style-label"
                  label="Naming style"
                  value={namingStyle}
                  onChange={(e) => setNamingStyle(e.target.value)}
                >
                  {selectedTemplate.naming_styles.map((style) => (
                    <MenuItem key={style} value={style}>
                      {style}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                variant="contained"
                startIcon={<PreviewIcon />}
                onClick={handlePreview}
                disabled={buildMutation.isPending}
              >
                {buildMutation.isPending ? 'Building…' : 'Preview'}
              </Button>

              {summaryErrorMessage() && <Alert severity="error">{summaryErrorMessage()}</Alert>}
            </Stack>
          </Paper>

          <Paper variant="outlined" sx={{ p: 2, flex: '1 1 400px', minWidth: 320 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="subtitle1">Preview</Typography>
              <Stack direction="row" spacing={1}>
                <Button
                  size="small"
                  startIcon={<CopyIcon />}
                  onClick={handleCopy}
                  disabled={!buildMutation.data}
                >
                  Copy JSON
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<DownloadIcon />}
                  onClick={handleDownload}
                  disabled={!buildMutation.data}
                >
                  {buildMutation.data ? `Download ${buildMutation.data.filename}` : 'Download'}
                </Button>
              </Stack>
            </Box>
            <Divider sx={{ mb: 1 }} />
            {buildMutation.data ? (
              <JsonViewer data={buildMutation.data.udt} />
            ) : (
              <Typography variant="body2" color="text.secondary">
                Fill in the questionnaire and click Preview to generate the UDT JSON.
              </Typography>
            )}
          </Paper>
        </Box>
      )}
    </Box>
  );
}
