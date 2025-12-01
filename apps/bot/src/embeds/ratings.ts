import { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } from 'discord.js';
import { RatingSummary, AlbumRead, WeekDetail } from '@sidetrack/shared';
import { createBaseEmbed, BRAND_COLORS, formatWeekLabel, formatStarRating, createProgressBar } from './common';

export interface RatingsCallOptions {
  week: WeekDetail;
  album?: AlbumRead | null;
}

/**
 * Build a Ratings Call embed asking users to rate the winning album.
 */
export function buildRatingsCallEmbed(options: RatingsCallOptions): EmbedBuilder {
  const { week, album } = options;
  const weekLabel = formatWeekLabel(week.label, week.week_number);

  const title = album?.title ?? 'Unknown Album';
  const artist = album?.artist_name ?? 'Unknown Artist';
  const coverUrl = album?.cover_url;

  const embed = createBaseEmbed()
    .setColor(BRAND_COLORS.rating)
    .setTitle(`⭐ Rate: ${title} — ${artist}`)
    .setDescription(
      `It's time to rate this week's album!\n\n` +
        `• Rate from **1.0 to 5.0** (half-stars allowed)\n` +
        `• Share your favorite track\n` +
        `• Add a short review\n\n` +
        `Click the button below to submit your rating.`,
    );

  if (coverUrl) {
    embed.setThumbnail(coverUrl);
  }

  embed.setFooter({ text: weekLabel });

  return embed;
}

/**
 * Build Rate Album button.
 */
export function buildRateAlbumButton(weekId: string): ActionRowBuilder<ButtonBuilder> {
  return new ActionRowBuilder<ButtonBuilder>().addComponents(
    new ButtonBuilder()
      .setCustomId(`ratings:rate:${weekId}`)
      .setLabel('⭐ Rate This Album')
      .setStyle(ButtonStyle.Primary),
  );
}

export interface RatingsSummaryOptions {
  week: WeekDetail;
  summary: RatingSummary;
  album?: AlbumRead | null;
  sampleReviews?: { userName: string; score: number; review: string }[];
}

/**
 * Build a Ratings Summary embed with average, histogram, and sample reviews.
 */
export function buildRatingsSummaryEmbed(options: RatingsSummaryOptions): EmbedBuilder {
  const { week, summary, album, sampleReviews } = options;
  const weekLabel = formatWeekLabel(week.label, week.week_number);

  const title = album?.title ?? 'Unknown Album';
  const artist = album?.artist_name ?? 'Unknown Artist';
  const coverUrl = album?.cover_url;

  const embed = createBaseEmbed()
    .setColor(BRAND_COLORS.rating)
    .setTitle(`📊 ${weekLabel} — Ratings Summary`);

  if (coverUrl) {
    embed.setThumbnail(coverUrl);
  }

  const fields: { name: string; value: string; inline: boolean }[] = [];

  // Average rating
  if (summary.average !== null) {
    const avg = summary.average.toFixed(2);
    fields.push({
      name: '⭐ Average Rating',
      value: `**${avg}** ${formatStarRating(summary.average)}`,
      inline: true,
    });
  }

  // Count
  fields.push({
    name: '👥 Total Ratings',
    value: `${summary.count} rating${summary.count !== 1 ? 's' : ''}`,
    inline: true,
  });

  // Histogram
  if (summary.histogram && summary.histogram.length > 0) {
    const maxCount = Math.max(...summary.histogram.map((bin) => bin.count));
    const histogramLines = summary.histogram
      .sort((a, b) => b.value - a.value) // 5.0 at top
      .map((bin) => {
        const stars = formatStarRating(bin.value).slice(0, 5);
        const bar = createProgressBar(bin.count, maxCount, 8);
        return `${bin.value.toFixed(1)} ${stars} ${bar} (${bin.count})`;
      })
      .join('\n');

    fields.push({
      name: '📈 Distribution',
      value: '```\n' + histogramLines + '\n```',
      inline: false,
    });
  }

  // Sample reviews
  if (sampleReviews && sampleReviews.length > 0) {
    const reviewsText = sampleReviews
      .slice(0, 3)
      .map((r) => `**${r.userName}** (${r.score.toFixed(1)}): "${r.review.slice(0, 100)}${r.review.length > 100 ? '...' : ''}"`)
      .join('\n\n');

    fields.push({
      name: '💬 What People Said',
      value: reviewsText,
      inline: false,
    });
  }

  embed.addFields(fields);
  embed.setDescription(`**${title}** by **${artist}**`);
  embed.setFooter({ text: weekLabel });

  return embed;
}

/**
 * Build a rating confirmation embed for ephemeral response.
 */
export function buildRatingConfirmEmbed(score: number, albumTitle: string): EmbedBuilder {
  return createBaseEmbed()
    .setColor(BRAND_COLORS.success)
    .setTitle('✅ Rating Submitted!')
    .setDescription(
      `Your rating of **${score.toFixed(1)}** ${formatStarRating(score)} for **${albumTitle}** has been recorded.`,
    )
    .addFields({
      name: 'Thanks!',
      value: 'Your rating helps the club track our collective taste.',
      inline: false,
    });
}
