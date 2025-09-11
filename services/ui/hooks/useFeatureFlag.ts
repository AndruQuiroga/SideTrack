'use client';

export default function useFeatureFlag(flag?: string | null) {
  const flags = (process.env.NEXT_PUBLIC_FEATURE_FLAGS || '')
    .split(',')
    .map((f) => f.trim())
    .filter(Boolean);
  if (!flag) return true;
  return flags.includes(flag);
}
