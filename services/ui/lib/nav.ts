'use client';

import * as Icons from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import nav from '../nav.json';
import useFeatureFlag from '../hooks/useFeatureFlag';

type RawNavItem = {
  path: string;
  label: string;
  icon: keyof typeof Icons;
  featureFlag?: string | null;
};

export type NavItem = {
  path: string;
  label: string;
  icon: LucideIcon;
};

export function useNavItems(): NavItem[] {
  const items = nav as RawNavItem[];

  return items
    .filter((item) => useFeatureFlag(item.featureFlag))
    .map(({ path, label, icon }) => ({
      path,
      label,
      icon: Icons[icon],
    }));
}
