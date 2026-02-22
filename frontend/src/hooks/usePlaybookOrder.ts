/**
 * Custom hook for managing playbook order in localStorage
 */

import { useState, useCallback } from 'react';
import { STORAGE_KEYS } from '../utils/localStorage';

interface PlaybookOrderState {
  order: string[];
  updateOrder: (newOrder: string[]) => void;
}

/**
 * Hook for managing playbook display order with localStorage persistence
 *
 * @param category - Category name for the playbook group
 * @returns Object with current order and update function
 */
export function usePlaybookOrder(category: string): PlaybookOrderState {
  const [order, setOrder] = useState<string[]>(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.PLAYBOOK_ORDER(category));
    return stored ? JSON.parse(stored) : [];
  });

  const updateOrder = useCallback((newOrder: string[]) => {
    setOrder(newOrder);
    localStorage.setItem(STORAGE_KEYS.PLAYBOOK_ORDER(category), JSON.stringify(newOrder));
  }, [category]);

  return { order, updateOrder };
}

/**
 * Hook for managing category display order with localStorage persistence
 *
 * @returns Object with current order and update function
 */
export function useCategoryOrder(): PlaybookOrderState {
  const [order, setOrder] = useState<string[]>(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.CATEGORY_ORDER);
    return stored ? JSON.parse(stored) : [];
  });

  const updateOrder = useCallback((newOrder: string[]) => {
    setOrder(newOrder);
    localStorage.setItem(STORAGE_KEYS.CATEGORY_ORDER, JSON.stringify(newOrder));
  }, []);

  return { order, updateOrder };
}

interface ExpandedState {
  [key: string]: boolean;
}

interface ExpandedStateHook {
  expanded: ExpandedState;
  setExpanded: (key: string, isExpanded: boolean) => void;
  toggleExpanded: (key: string) => void;
}

/**
 * Hook for managing category expanded/collapsed state with localStorage persistence
 *
 * @returns Object with expanded state and update functions
 */
export function useCategoryExpanded(): ExpandedStateHook {
  const [expanded, setExpandedState] = useState<ExpandedState>(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.CATEGORY_EXPANDED);
    return stored ? JSON.parse(stored) : {};
  });

  const setExpanded = useCallback((key: string, isExpanded: boolean) => {
    setExpandedState(prev => {
      const newState = { ...prev, [key]: isExpanded };
      localStorage.setItem(STORAGE_KEYS.CATEGORY_EXPANDED, JSON.stringify(newState));
      return newState;
    });
  }, []);

  const toggleExpanded = useCallback((key: string) => {
    setExpandedState(prev => {
      const newState = { ...prev, [key]: !prev[key] };
      localStorage.setItem(STORAGE_KEYS.CATEGORY_EXPANDED, JSON.stringify(newState));
      return newState;
    });
  }, []);

  return { expanded, setExpanded, toggleExpanded };
}

/**
 * Hook for managing group expanded/collapsed state with localStorage persistence
 *
 * @returns Object with expanded state and update functions
 */
export function useGroupExpanded(): ExpandedStateHook {
  const [expanded, setExpandedState] = useState<ExpandedState>(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.GROUP_EXPANDED);
    return stored ? JSON.parse(stored) : {};
  });

  const setExpanded = useCallback((key: string, isExpanded: boolean) => {
    setExpandedState(prev => {
      const newState = { ...prev, [key]: isExpanded };
      localStorage.setItem(STORAGE_KEYS.GROUP_EXPANDED, JSON.stringify(newState));
      return newState;
    });
  }, []);

  const toggleExpanded = useCallback((key: string) => {
    setExpandedState(prev => {
      const newState = { ...prev, [key]: !prev[key] };
      localStorage.setItem(STORAGE_KEYS.GROUP_EXPANDED, JSON.stringify(newState));
      return newState;
    });
  }, []);

  return { expanded, setExpanded, toggleExpanded };
}
