import { Message, ChannelType, Client } from 'discord.js';
import { NominationCreate, RatingCreate, AlbumRead, WeekDetail } from '@sidetrack/api-client';

import { ClubSyncService } from '../clubService';
import { BotConfig } from '../config';
import { Logger } from '../logger';
import {
  buildNominationEmbed,
  buildNominationButtons,
  formatWeekLabel,
  BRAND_COLORS,
} from '../embeds';
import { extractDominantColor } from '../utils/color';
import { updateNominationsEmbed } from './handlers';

export function registerMessageHandlers(
  client: Client,
  service: ClubSyncService,
  config: BotConfig,
  logger: Logger,
): void {
  client.on('messageCreate', async (message: Message) => {
    if (message.author.bot) return;
    if (!message.channel.isThread()) return;
    if (message.channel.parent?.type !== ChannelType.GuildForum) return;

    const threadId = message.channel.id;

    const nominationWeek = service.getWeekForNominationsThread(threadId);
    const ratingWeek = service.getWeekForRatingsThread(threadId);

    if (!nominationWeek && !ratingWeek) return;

    if (nominationWeek) {
      await handleNominationMessage(message, nominationWeek, service, logger);
    } else if (ratingWeek) {
      await handleRatingMessage(message, ratingWeek, service, logger);
    }
  });
}

// ============ NOMINATION HANDLER ============

async function handleNominationMessage(
  message: Message,
  week: WeekDetail,
  service: ClubSyncService,
  logger: Logger,
): Promise<void> {
  if (!message.channel.isThread()) return;
  const thread = message.channel;

  const parsed = parseNominationForm(message.content);
  if (!parsed.ok) {
    await safeReply(
      message,
      parsed.error ?? 'Nomination appears invalid. Please paste the mini-form.',
      logger,
    );
    return;
  }

  try {
    const user = await service.ensureDiscordUser(
      message.author.id,
      message.member?.displayName ?? message.author.globalName ?? message.author.username,
    );

    let album: AlbumRead | undefined;
    let albumId = parsed.albumId;
    if (!albumId) {
      if (!parsed.title || !parsed.artist) {
        await safeReply(
          message,
          'Please format as `Album — Artist` to help me find the album.',
          logger,
        );
        return;
      }
      // Use enrichment pipeline: MusicBrainz → Cover Art Archive → Spotify
      try {
        album = await service.getClient().resolveAlbum({
          title: parsed.title,
          artist: parsed.artist,
        });
      } catch (resolveError) {
        logger.warn('Album enrichment failed, falling back to basic creation.', {
          error: resolveError instanceof Error ? resolveError.message : String(resolveError),
        });
        album = await service.ensureAlbumFromForm({
          title: parsed.title,
          artist_name: parsed.artist,
          release_year: parsed.releaseYear ?? undefined,
        });
      }
      albumId = album.id;
    } else {
      album = await service
        .getClient()
        .getAlbum(albumId)
        .catch(() => undefined);
    }

    // Extract dominant color from album cover art
    let accentColor = BRAND_COLORS.nomination;
    if (album?.cover_url) {
      try {
        accentColor = await extractDominantColor(album.cover_url);
      } catch {
        // Fall back silently
      }
    }

    // Auto-populate genre from enrichment data
    const genre = album?.genres?.length ? album.genres[0] : undefined;

    const nomination: NominationCreate = {
      week_id: week.id,
      user_id: user.id,
      album_id: albumId,
      pitch: parsed.pitch ?? undefined,
      pitch_track_url: parsed.pitchTrack ?? undefined,
      genre,
    };

    const created = await service.recordNomination(week.id, nomination, {
      week_id: week.id,
      user_id: user.id,
      album_id: albumId,
    });
    logger.info('Nomination recorded from Discord thread.', {
      nomination_id: created.id,
      week_id: week.id,
      enriched: !!album?.musicbrainz_id || !!album?.spotify_id,
    });

    // Delete the raw mini-form message and replace with a rich embed card
    await message.delete().catch((error) =>
      logger.warn('Failed to delete original nomination message.', {
        error: error instanceof Error ? error.message : String(error),
      }),
    );

    // Count existing nominations to determine index
    const freshWeek = await service.getClient().getWeek(week.id);
    const nominationIndex = freshWeek.nominations.findIndex((n) => n.id === created.id) + 1;

    const weekLabel = formatWeekLabel(week.label, week.week_number);
    const nominationEmbed = buildNominationEmbed({
      nomination: created,
      album,
      nominatorName:
        message.member?.displayName ?? message.author.globalName ?? message.author.username,
      nominatorAvatarURL: message.author.avatarURL() ?? undefined,
      weekLabel,
      nominationIndex: nominationIndex || undefined,
      accentColor,
    });
    const buttons = buildNominationButtons(created.id);
    await thread.send({ embeds: [nominationEmbed], components: [buttons] });

    // Update nominations count in the starter embed
    await updateNominationsEmbed(thread, week.id, service, logger);
  } catch (error) {
    logger.error('Failed to record nomination.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await safeReply(
      message,
      'Sorry, I could not save that nomination. Please check the format or try again.',
      logger,
    );
  }
}

// ============ RATING HANDLER ============

async function handleRatingMessage(
  message: Message,
  week: { id: string; winner_album_id?: string | null },
  service: ClubSyncService,
  logger: Logger,
): Promise<void> {
  if (!week.winner_album_id) {
    await safeReply(
      message,
      'Ratings are not open yet — no winner album is set for this week.',
      logger,
    );
    return;
  }

  const parsed = parseRatingForm(message.content);
  if (!parsed.ok) {
    await safeReply(
      message,
      parsed.error ??
        'Rating format not recognized. Use:\n```\nRating: 4.5\nFavorite track: <name>\nThoughts: <review>\n```',
      logger,
    );
    return;
  }

  try {
    const user = await service.ensureDiscordUser(
      message.author.id,
      message.member?.displayName ?? message.author.globalName ?? message.author.username,
    );

    const rating: RatingCreate = {
      week_id: week.id,
      user_id: user.id,
      album_id: week.winner_album_id,
      value: parsed.value,
      favorite_track: parsed.favoriteTrack ?? undefined,
      review: parsed.review ?? undefined,
    };

    const created = await service.recordRating(week.id, rating, {
      week_id: week.id,
      user_id: user.id,
    });
    logger.info('Rating recorded from Discord thread.', {
      rating_id: created.id,
      week_id: week.id,
    });
    await message.react('⭐');
  } catch (error) {
    logger.error('Failed to record rating.', {
      error: error instanceof Error ? error.message : String(error),
    });
    await safeReply(
      message,
      'Sorry, I could not save that rating. Please check the format or try again.',
      logger,
    );
  }
}

// ============ HELPERS ============

function safeReply(message: Message, content: string, logger: Logger): Promise<void> {
  return message
    .reply({ content, allowedMentions: { repliedUser: false } })
    .then(() => undefined)
    .catch((error) => {
      logger.warn('Failed to reply to message.', {
        error: error instanceof Error ? error.message : String(error),
      });
    });
}

// ============ NOMINATION PARSER ============

interface ParsedNomination {
  ok: boolean;
  error?: string;
  albumId?: string;
  title?: string | null;
  artist?: string | null;
  releaseYear?: number | null;
  pitch?: string | null;
  pitchTrack?: string | null;
}

function parseNominationForm(content: string): ParsedNomination {
  const lines = content
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length === 0) {
    return { ok: false, error: 'Nomination appears to be empty. Paste the mini-form to submit.' };
  }

  const albumLine = lines[0];
  const albumId = extractAlbumId(lines.join(' '));

  const whyLine = lines.find((line) => line.toLowerCase().startsWith('why'));
  const pitchTrackLine = lines.find((line) => line.toLowerCase().startsWith('pitch track'));

  const pitch = whyLine ? whyLine.split(':').slice(1).join(':').trim() : null;
  const pitchTrack = pitchTrackLine ? pitchTrackLine.split(':').slice(1).join(':').trim() : null;

  if (!albumLine) {
    return { ok: false, error: 'Missing album line. Format: Album — Artist' };
  }

  const parsedAlbum = parseAlbumLine(albumLine);

  return {
    ok: true,
    albumId,
    title: parsedAlbum?.title ?? null,
    artist: parsedAlbum?.artist ?? null,
    releaseYear: parsedAlbum?.year ?? null,
    pitch,
    pitchTrack,
  };
}

function extractAlbumId(input: string): string | undefined {
  const uuidRegex = /album:\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i;
  const match = input.match(uuidRegex);
  return match ? match[1] : undefined;
}

function parseAlbumLine(
  line: string,
): { title: string; artist: string; year: number | null } | undefined {
  const parts = line
    .split(/—|-/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length < 2) return undefined;

  const artistPart = parts.pop() || '';
  const title = parts.join(' - ').trim();

  const yearMatch = artistPart.match(/\((\d{4})\)$/);
  const year = yearMatch ? Number(yearMatch[1]) : null;
  const artist = artistPart.replace(/\(\d{4}\)$/, '').trim();

  if (!title || !artist) return undefined;

  return { title, artist, year };
}

// ============ RATING PARSER ============

interface ParsedRating {
  ok: boolean;
  error?: string;
  value: number;
  favoriteTrack?: string | null;
  review?: string | null;
}

function parseRatingForm(content: string): ParsedRating {
  const lines = content
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  const ratingLine = lines.find((line) => /^rating\s*:/i.test(line));
  if (!ratingLine) {
    return {
      ok: false,
      value: 0,
      error: 'Missing `Rating:` line. Format: `Rating: 4.5` (values 1.0–5.0 in 0.5 steps).',
    };
  }

  const rawValue = ratingLine.split(':').slice(1).join(':').trim();
  const value = parseFloat(rawValue);

  if (Number.isNaN(value) || value < 1.0 || value > 5.0) {
    return {
      ok: false,
      error: `Invalid rating "${rawValue}". Must be between 1.0 and 5.0.`,
      value: 0,
    };
  }

  // Enforce 0.5 increments
  const rounded = Math.round(value * 2) / 2;
  if (Math.abs(rounded - value) > 0.01) {
    return {
      ok: false,
      error: `Rating must be in 0.5 increments (e.g. 3.0, 3.5, 4.0). Got ${value}.`,
      value: 0,
    };
  }

  const trackLine = lines.find((line) => /^favorite\s+track\s*:/i.test(line));
  const thoughtsLine = lines.find((line) => /^thoughts\s*:/i.test(line));

  const favoriteTrack = trackLine ? trackLine.split(':').slice(1).join(':').trim() || null : null;
  const review = thoughtsLine ? thoughtsLine.split(':').slice(1).join(':').trim() || null : null;

  return { ok: true, value: rounded, favoriteTrack, review };
}
