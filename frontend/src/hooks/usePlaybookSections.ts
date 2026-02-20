/**
 * Custom hook for managing user-created playbook sections with localStorage persistence
 */

import { useState, useCallback } from 'react';

export interface PlaybookSection {
  id: string;
  name: string;
  expanded: boolean;
  playbooks: string[]; // playbook paths
}

interface PlaybookSectionsState {
  sections: PlaybookSection[];
  createSection: (name: string) => void;
  deleteSection: (sectionId: string) => void;
  renameSection: (sectionId: string, newName: string) => void;
  toggleSection: (sectionId: string) => void;
  movePlaybook: (playbookPath: string, sectionId: string | null) => void;
  reorderSections: (newSections: PlaybookSection[]) => void;
  reorderPlaybooksInSection: (sectionId: string, newPlaybooks: string[]) => void;
  getUnsortedPlaybooks: (allPaths: string[]) => string[];
}

function getStorageKey(domain: string): string {
  return `playbook_sections_${domain}`;
}

/**
 * Hook for managing user-created sections for playbook organization
 *
 * @param domain - Domain name (gateway, designer, perspective)
 * @returns Object with sections state and management functions
 */
export function usePlaybookSections(domain: string): PlaybookSectionsState {
  const [sections, setSections] = useState<PlaybookSection[]>(() => {
    const stored = localStorage.getItem(getStorageKey(domain));
    return stored ? JSON.parse(stored) : [];
  });

  const persist = useCallback((newSections: PlaybookSection[]) => {
    setSections(newSections);
    localStorage.setItem(getStorageKey(domain), JSON.stringify(newSections));
  }, [domain]);

  const createSection = useCallback((name: string) => {
    const newSection: PlaybookSection = {
      id: `sec-${Date.now()}`,
      name,
      expanded: true,
      playbooks: [],
    };
    persist([...sections, newSection]);
  }, [sections, persist]);

  const deleteSection = useCallback((sectionId: string) => {
    persist(sections.filter(s => s.id !== sectionId));
  }, [sections, persist]);

  const renameSection = useCallback((sectionId: string, newName: string) => {
    persist(sections.map(s =>
      s.id === sectionId ? { ...s, name: newName } : s
    ));
  }, [sections, persist]);

  const toggleSection = useCallback((sectionId: string) => {
    persist(sections.map(s =>
      s.id === sectionId ? { ...s, expanded: !s.expanded } : s
    ));
  }, [sections, persist]);

  const movePlaybook = useCallback((playbookPath: string, sectionId: string | null) => {
    persist(sections.map(s => {
      // Remove from all sections first
      const filtered = s.playbooks.filter(p => p !== playbookPath);
      // Add to target section
      if (s.id === sectionId) {
        return { ...s, playbooks: [...filtered, playbookPath] };
      }
      return { ...s, playbooks: filtered };
    }));
  }, [sections, persist]);

  const reorderSections = useCallback((newSections: PlaybookSection[]) => {
    persist(newSections);
  }, [persist]);

  const reorderPlaybooksInSection = useCallback((sectionId: string, newPlaybooks: string[]) => {
    persist(sections.map(s =>
      s.id === sectionId ? { ...s, playbooks: newPlaybooks } : s
    ));
  }, [sections, persist]);

  const getUnsortedPlaybooks = useCallback((allPaths: string[]): string[] => {
    const assigned = new Set(sections.flatMap(s => s.playbooks));
    return allPaths.filter(p => !assigned.has(p));
  }, [sections]);

  return {
    sections,
    createSection,
    deleteSection,
    renameSection,
    toggleSection,
    movePlaybook,
    reorderSections,
    reorderPlaybooksInSection,
    getUnsortedPlaybooks,
  };
}
