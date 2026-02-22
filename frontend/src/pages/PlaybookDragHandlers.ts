/**
 * Playbook drag-end handlers - Unified drag handler for playbook reordering
 *
 * Consolidates the 3 identical per-category drag handlers into a single
 * parameterized function.
 */

import { arrayMove } from '@dnd-kit/sortable';
import type { DragEndEvent } from '@dnd-kit/core';
import type { PlaybookInfo } from '../types/api';
import { STORAGE_KEYS } from '../utils/localStorage';

// Save custom order to localStorage
export function savePlaybookOrder(category: string, order: string[]) {
  localStorage.setItem(STORAGE_KEYS.PLAYBOOK_ORDER(category), JSON.stringify(order));
}

// Load custom order from localStorage
export function getPlaybookOrder(category: string): string[] {
  const stored = localStorage.getItem(STORAGE_KEYS.PLAYBOOK_ORDER(category));
  return stored ? JSON.parse(stored) : [];
}

// Apply saved order to playbooks
export function applyOrder(playbooks: PlaybookInfo[], category: string): PlaybookInfo[] {
  const savedOrder = getPlaybookOrder(category);
  if (savedOrder.length === 0) return playbooks;

  // Create a map for quick lookup
  const playbookMap = new Map(playbooks.map(p => [p.path, p]));

  // First, add playbooks in saved order
  const ordered: PlaybookInfo[] = [];
  savedOrder.forEach(path => {
    const playbook = playbookMap.get(path);
    if (playbook) {
      ordered.push(playbook);
      playbookMap.delete(path);
    }
  });

  // Then add any new playbooks that weren't in the saved order
  playbookMap.forEach(playbook => ordered.push(playbook));

  return ordered;
}

/**
 * Creates a unified drag-end handler for any playbook category.
 *
 * Replaces the 3 identical handleGatewayDragEnd / handleDesignerDragEnd /
 * handlePerspectiveDragEnd with a single parameterized factory.
 *
 * @param categoryPlaybooks - The current ordered list for this category
 * @param setPlaybooks - State setter for this category's playbook list
 * @param categoryKey - The localStorage key for this category ('gateway' | 'designer' | 'perspective')
 */
export function createCategoryDragEndHandler(
  categoryPlaybooks: PlaybookInfo[],
  setPlaybooks: React.Dispatch<React.SetStateAction<PlaybookInfo[]>>,
  categoryKey: string
) {
  return (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = categoryPlaybooks.findIndex(p => p.path === active.id);
      const newIndex = categoryPlaybooks.findIndex(p => p.path === over.id);
      const newOrder = arrayMove(categoryPlaybooks, oldIndex, newIndex);
      setPlaybooks(newOrder);
      savePlaybookOrder(categoryKey, newOrder.map(p => p.path));
    }
  };
}
