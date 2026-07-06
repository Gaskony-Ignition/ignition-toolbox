/**
 * UDT Builder page
 *
 * Guided composer wizard for building convention-conforming UDT type
 * definitions: pick a quick-start preset (or start blank) -> Basics ->
 * Structure -> Alarms -> History -> Review, with a live-lint panel driven
 * by a debounced `/api/udt/compose` call. Replaces the old
 * device-class-template questionnaire flow (Nigel-ratified 2026-07-06,
 * docs/plans/udt-composer-design.md).
 *
 * Download-JSON-only delivery: nothing here pushes to a gateway, the user
 * imports the downloaded file into Designer (Tag Browser -> Import)
 * themselves.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { PresetPicker } from '../components/udt/PresetPicker';
import { ComposerWizard } from '../components/udt/ComposerWizard';
import type { UdtComposition, UdtPreset } from '../types/api';

function blankComposition(): UdtComposition {
  return {
    type_name: '',
    description: '',
    naming_style: 'camelCase',
    parameters: [
      { name: 'DevicePath', data_type: 'String', default_value: '', description: 'OPC device path root.' },
    ],
    members: [],
  };
}

export function UdtBuilder() {
  const [composition, setComposition] = useState<UdtComposition | null>(null);
  // Bump to force a fresh ComposerWizard (and its internal state) whenever a
  // new preset/blank start is chosen after a restart.
  const [wizardKey, setWizardKey] = useState(0);

  const presetsQuery = useQuery({
    queryKey: ['udt-presets'],
    queryFn: api.udt.getPresets,
  });

  const handleSelectPreset = (preset: UdtPreset) => {
    setComposition(preset.composition);
    setWizardKey((k) => k + 1);
  };

  const handleStartBlank = () => {
    setComposition(blankComposition());
    setWizardKey((k) => k + 1);
  };

  const handleRestart = () => {
    setComposition(null);
  };

  if (!composition) {
    return (
      <PresetPicker
        presets={presetsQuery.data ?? []}
        isLoading={presetsQuery.isLoading}
        isError={presetsQuery.isError}
        onSelectPreset={handleSelectPreset}
        onStartBlank={handleStartBlank}
      />
    );
  }

  return <ComposerWizard key={wizardKey} initialComposition={composition} onRestart={handleRestart} />;
}
