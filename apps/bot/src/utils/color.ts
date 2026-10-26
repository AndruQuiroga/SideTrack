/**
 * Dominant color extraction from album cover images.
 *
 * Uses `sharp` to sample pixels from the album art and compute an
 * average dominant color, which is then used as the Discord embed accent.
 */

import sharp from 'sharp';
import { ColorResolvable } from 'discord.js';
import { BRAND_COLORS } from '../embeds/common';

/** Simple in-memory cache: cover URL → hex color number */
const colorCache = new Map<string, number>();

/**
 * Extract the dominant color from an image URL.
 *
 * Resizes the image to a tiny thumbnail, samples pixel data, and computes
 * a weighted average that favours saturated, non-grey colours.
 *
 * Falls back to `BRAND_COLORS.nomination` on any failure.
 */
export async function extractDominantColor(imageUrl: string): Promise<ColorResolvable> {
  // Check cache first
  const cached = colorCache.get(imageUrl);
  if (cached !== undefined) return cached as ColorResolvable;

  try {
    const response = await fetch(imageUrl);
    if (!response.ok) return BRAND_COLORS.nomination;

    const buffer = Buffer.from(await response.arrayBuffer());

    // Resize to 16x16 — small enough to be fast, large enough for a good average
    const { data, info } = await sharp(buffer)
      .resize(16, 16, { fit: 'cover' })
      .removeAlpha()
      .raw()
      .toBuffer({ resolveWithObject: true });

    const pixels = info.width * info.height;
    let totalR = 0;
    let totalG = 0;
    let totalB = 0;
    let totalWeight = 0;

    for (let i = 0; i < pixels; i++) {
      const r = data[i * 3];
      const g = data[i * 3 + 1];
      const b = data[i * 3 + 2];

      // Compute saturation to weight saturated pixels higher
      const max = Math.max(r, g, b);
      const min = Math.min(r, g, b);
      const luminance = (max + min) / 2;
      const saturation = max === min ? 0 : (max - min) / (1 - Math.abs((2 * luminance) / 255 - 1));

      // Skip very dark or very light pixels (backgrounds, whites)
      if (luminance < 20 || luminance > 240) continue;

      // Weight by saturation — vivid colours matter more
      const weight = 0.3 + saturation * 0.7;
      totalR += r * weight;
      totalG += g * weight;
      totalB += b * weight;
      totalWeight += weight;
    }

    if (totalWeight === 0) {
      colorCache.set(imageUrl, BRAND_COLORS.nomination as number);
      return BRAND_COLORS.nomination;
    }

    const avgR = Math.round(totalR / totalWeight);
    const avgG = Math.round(totalG / totalWeight);
    const avgB = Math.round(totalB / totalWeight);

    // Boost saturation slightly for a punchier embed colour
    const boosted = boostSaturation(avgR, avgG, avgB, 1.3);
    const hex = (boosted.r << 16) | (boosted.g << 8) | boosted.b;

    colorCache.set(imageUrl, hex);
    return hex as ColorResolvable;
  } catch {
    return BRAND_COLORS.nomination;
  }
}

/** Boost the saturation of an RGB colour by a factor. */
function boostSaturation(
  r: number,
  g: number,
  b: number,
  factor: number,
): { r: number; g: number; b: number } {
  // Convert to HSL, boost S, convert back
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;

  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;

  if (max === min) return { r, g, b }; // achromatic

  const d = max - min;
  let s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = 0;

  if (max === rn) h = ((gn - bn) / d + (gn < bn ? 6 : 0)) / 6;
  else if (max === gn) h = ((bn - rn) / d + 2) / 6;
  else h = ((rn - gn) / d + 4) / 6;

  s = Math.min(1, s * factor);

  // HSL → RGB
  const hue2rgb = (p: number, q: number, t: number): number => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };

  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;

  return {
    r: Math.round(hue2rgb(p, q, h + 1 / 3) * 255),
    g: Math.round(hue2rgb(p, q, h) * 255),
    b: Math.round(hue2rgb(p, q, h - 1 / 3) * 255),
  };
}
