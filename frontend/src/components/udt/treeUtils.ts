/**
 * Immutable helpers for editing the composition's member tree.
 *
 * Members are addressed by a `Path` — an array of indices into nested
 * `.members` arrays, e.g. `[0, 2]` = the third child of the first
 * top-level member (which must be a folder). Paths are recomputed from
 * scratch on every render (the tree is small — a handful to a few dozen
 * members) so there's no separate id bookkeeping to keep in sync with the
 * wire contract.
 */

import type { UdtCompositionMember, UdtCompositionTag } from '../../types/api';

export type Path = number[];

export function getMemberAt(members: UdtCompositionMember[], path: Path): UdtCompositionMember | null {
  if (path.length === 0) return null;
  const [head, ...rest] = path;
  const member = members[head];
  if (!member) return null;
  if (rest.length === 0) return member;
  if (member.kind !== 'folder') return null;
  return getMemberAt(member.members, rest);
}

/** Replace the member at `path` by applying `updater` to it. Returns a new tree. */
export function updateMemberAt(
  members: UdtCompositionMember[],
  path: Path,
  updater: (member: UdtCompositionMember) => UdtCompositionMember
): UdtCompositionMember[] {
  const [head, ...rest] = path;
  return members.map((member, index) => {
    if (index !== head) return member;
    if (rest.length === 0) return updater(member);
    if (member.kind !== 'folder') return member;
    return { ...member, members: updateMemberAt(member.members, rest, updater) };
  });
}

/** Remove the member at `path`. Returns a new tree. */
export function removeMemberAt(members: UdtCompositionMember[], path: Path): UdtCompositionMember[] {
  const [head, ...rest] = path;
  if (rest.length === 0) {
    return members.filter((_, index) => index !== head);
  }
  return members.map((member, index) => {
    if (index !== head || member.kind !== 'folder') return member;
    return { ...member, members: removeMemberAt(member.members, rest) };
  });
}

/**
 * Add `newMember` as the last child of the folder at `parentPath` (or to
 * the root members list when `parentPath` is empty).
 */
export function addChildAt(
  members: UdtCompositionMember[],
  parentPath: Path,
  newMember: UdtCompositionMember
): UdtCompositionMember[] {
  if (parentPath.length === 0) {
    return [...members, newMember];
  }
  const [head, ...rest] = parentPath;
  return members.map((member, index) => {
    if (index !== head || member.kind !== 'folder') return member;
    return { ...member, members: addChildAt(member.members, rest, newMember) };
  });
}

export interface FlattenedTag {
  path: Path;
  location: string;
  tag: UdtCompositionTag;
}

/** Walk the tree and return every tag leaf with its path and slash-joined location (matches finding.location). */
export function flattenTags(members: UdtCompositionMember[], prefix: string[] = [], path: Path = []): FlattenedTag[] {
  const result: FlattenedTag[] = [];
  members.forEach((member, index) => {
    const memberPath = [...path, index];
    const memberPrefix = [...prefix, member.name];
    if (member.kind === 'tag') {
      result.push({ path: memberPath, location: memberPrefix.join('/'), tag: member });
    } else {
      result.push(...flattenTags(member.members, memberPrefix, memberPath));
    }
  });
  return result;
}

/** Sibling names at `parentPath` (used to flag/avoid duplicate names while editing). */
export function siblingNamesAt(members: UdtCompositionMember[], parentPath: Path): string[] {
  if (parentPath.length === 0) return members.map((m) => m.name);
  const parent = getMemberAt(members, parentPath);
  if (!parent || parent.kind !== 'folder') return [];
  return parent.members.map((m) => m.name);
}

export function blankTag(name: string): UdtCompositionTag {
  return {
    kind: 'tag',
    name,
    value_source: 'opc',
    data_type: 'Float4',
    opc_item_path: '',
    opc_server: 'Ignition OPC UA Server',
    documentation: '',
    tooltip: '',
  };
}

export function blankFolder(name: string): UdtCompositionMember {
  return { kind: 'folder', name, members: [] };
}
