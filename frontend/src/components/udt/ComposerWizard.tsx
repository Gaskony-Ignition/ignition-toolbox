/**
 * Guided UDT composer — Basics -> Structure -> Alarms -> History -> Review,
 * with a persistent live-lint panel driven by a debounced
 * `/api/udt/compose` call on every composition edit.
 *
 * The composition itself never resets on a compose error (including a 422
 * structural error) — only the lint panel's contents change. The last
 * *successful* compose result stays available for the Review step's
 * preview/download even while a later edit is mid-debounce or failing.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Box, Stepper, Step, StepButton, Button, Paper } from '@mui/material';
import { api, APIError } from '../../api/client';
import type { UdtComposition, UdtComposeResponse } from '../../types/api';
import { BasicsStep } from './BasicsStep';
import { MemberTreeEditor } from './MemberTreeEditor';
import { AlarmEditor } from './AlarmEditor';
import { HistoryEditor } from './HistoryEditor';
import { ReviewStep } from './ReviewStep';
import { LintPanel } from './LintPanel';
import { splitBlockingErrors } from './lintUtils';

const LINT_DEBOUNCE_MS = 600;

const STEPS = [
  { id: 'basics', label: 'Basics' },
  { id: 'structure', label: 'Structure' },
  { id: 'alarms', label: 'Alarms' },
  { id: 'history', label: 'History' },
  { id: 'review', label: 'Review' },
] as const;

interface ComposerWizardProps {
  initialComposition: UdtComposition;
  onRestart: () => void;
}

export function ComposerWizard({ initialComposition, onRestart }: ComposerWizardProps) {
  const [composition, setComposition] = useState<UdtComposition>(initialComposition);
  const [activeStep, setActiveStep] = useState(0);
  const [visited, setVisited] = useState<Set<number>>(new Set([0]));

  const [composeResult, setComposeResult] = useState<UdtComposeResponse | null>(null);
  const [composeError, setComposeError] = useState<Error | null>(null);
  const [isComposing, setIsComposing] = useState(false);

  const onChange = useCallback((updater: (c: UdtComposition) => UdtComposition) => {
    setComposition((prev) => updater(prev));
  }, []);

  // Debounced live lint — fires on every composition edit, on every step.
  useEffect(() => {
    const hasContent = composition.type_name.trim().length > 0 || composition.members.length > 0;
    if (!hasContent) {
      setComposeResult(null);
      setComposeError(null);
      return;
    }

    let cancelled = false;
    setIsComposing(true);
    const handle = setTimeout(() => {
      api.udt
        .compose(composition)
        .then((result) => {
          if (cancelled) return;
          setComposeResult(result);
          setComposeError(null);
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setComposeError(err instanceof Error ? err : new Error('Unknown error composing UDT.'));
        })
        .finally(() => {
          if (!cancelled) setIsComposing(false);
        });
    }, LINT_DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [composition]);

  const typeNameValid = composition.type_name.trim().length > 0;
  const hasMembers = composition.members.length > 0;

  const stepReachable = useCallback(
    (index: number): boolean => {
      if (index <= 0) return true;
      if (index === 1) return typeNameValid;
      return typeNameValid && hasMembers; // alarms, history, review
    },
    [typeNameValid, hasMembers]
  );

  const goToStep = (index: number) => {
    if (!visited.has(index) && !stepReachable(index)) return;
    setVisited((prev) => new Set(prev).add(index));
    setActiveStep(index);
  };

  const handleNext = () => {
    const next = activeStep + 1;
    if (next < STEPS.length) goToStep(next);
  };

  const handleBack = () => {
    if (activeStep > 0) goToStep(activeStep - 1);
  };

  const blockingErrors = useMemo(() => {
    if (!composeError) return [];
    if (composeError instanceof APIError && composeError.status === 422) {
      return splitBlockingErrors(composeError.message);
    }
    return [composeError instanceof APIError ? composeError.getDisplayMessage() : composeError.message];
  }, [composeError]);

  const findings = composeResult?.findings ?? [];

  return (
    <Box>
      <Stepper nonLinear activeStep={activeStep} sx={{ mb: 3 }}>
        {STEPS.map((step, index) => (
          <Step key={step.id} completed={visited.has(index) && index !== activeStep}>
            <StepButton onClick={() => goToStep(index)} disabled={!visited.has(index) && !stepReachable(index)}>
              {step.label}
            </StepButton>
          </Step>
        ))}
      </Stepper>

      <Box sx={{ display: 'flex', gap: 3, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <Box sx={{ flex: '2 1 500px', minWidth: 320 }}>
          {activeStep === 0 && <BasicsStep composition={composition} onChange={onChange} />}
          {activeStep === 1 && <MemberTreeEditor composition={composition} onChange={onChange} />}
          {activeStep === 2 && <AlarmEditor composition={composition} onChange={onChange} />}
          {activeStep === 3 && <HistoryEditor composition={composition} onChange={onChange} />}
          {activeStep === 4 && <ReviewStep composeResult={composeResult} />}

          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
            <Button onClick={onRestart} color="inherit" data-testid="wizard-start-over">
              Start over
            </Button>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button onClick={handleBack} disabled={activeStep === 0}>
                Back
              </Button>
              {activeStep < STEPS.length - 1 && (
                <Button
                  variant="contained"
                  onClick={handleNext}
                  disabled={!stepReachable(activeStep + 1)}
                  data-testid="wizard-next"
                >
                  Next
                </Button>
              )}
            </Box>
          </Box>
        </Box>

        {activeStep > 0 && (
          <Paper variant="outlined" sx={{ flex: '1 1 320px', minWidth: 280, p: 2 }}>
            <LintPanel findings={findings} blockingErrors={blockingErrors} isPending={isComposing} />
          </Paper>
        )}
      </Box>
    </Box>
  );
}
