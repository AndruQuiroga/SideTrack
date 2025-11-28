import { Message, ChannelType, Client } from 'discord.js';
import { NominationCreate } from '@sidetrack/shared';

import { ClubSyncService } from '../clubService';
import { BotConfig } from '../config';
import { Logger } from '../logger';

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

    const nominationsForumId = config.club.nominationsForumId;
    if (nominationsForumId && message.channel.parentId !== nominationsForumId) return;

    const week = service.getWeekForNominationsThread(message.channel.id);
    if (!week) return;

    const parsed = parseNominationForm(message.content);
    if (!parsed.ok) {
      await safeReply(message, parsed.error ?? 'Nomination appears invalid. Please paste the mini-form.', logger);
      return;
    }

    try {
      const user = await service.ensureDiscordUser(
        message.author.id,
        message.member?.displayName ?? message.author.globalName ?? message.author.username,
      );

      let albumId = parsed.albumId;
      if (!albumId) {
        if (!parsed.title || !parsed.artist) {
          await safeReply(
            message,
            'Please format as `Album — Artist (Year)` or include `[album:<uuid>]` to help me find the album.',
            logger,
          );
          return;
        }
        const album = await service.ensureAlbumFromForm({
          title: parsed.title,
          artist_name: parsed.artist,
          release_year: parsed.releaseYear ?? undefined,
        });
        albumId = album.id;
      }

      const nomination: NominationCreate = {
        week_id: week.id,
        user_id: user.id,
        album_id: albumId,
        pitch: parsed.pitch ?? undefined,
        pitch_track_url: parsed.pitchTrack ?? undefined,
        genre: parsed.genre ?? undefined,
        decade: parsed.decade ?? undefined,
        country: parsed.country ?? undefined,
      };

      const created = await service.recordNomination(
        week.id,
        nomination,
        { week_id: week.id, user_id: user.id, album_id: parsed.albumId },
      );
      logger.info('Nomination recorded from Discord thread.', { nomination_id: created.id, week_id: week.id });
      await message.react('✅');
    } catch (error) {
      logger.error('Failed to record nomination.', { error: error instanceof Error ? error.message : String(error) });
      await safeReply(
        message,
        'Sorry, I could not save that nomination. Please check the format or try again.',
        logger,
      );
    }
  });
}

function safeReply(message: Message, content: string, logger: Logger): Promise<void> {
  return message
    .reply({ content, allowedMentions: { repliedUser: false } })
    .then(() => undefined)
    .catch((error) => {
      logger.warn('Failed to reply to nomination message.', { error: error instanceof Error ? error.message : String(error) });
    });
}

interface ParsedNomination {
  ok: boolean;
  error?: string;
  albumId?: string;
  title?: string | null;
  artist?: string | null;
  releaseYear?: number | null;
  pitch?: string | null;
  pitchTrack?: string | null;
  genre?: string | null;
  decade?: string | null;
  country?: string | null;
}

function parseNominationForm(content: string): ParsedNomination {
  const lines = content.split('\n').map((line) => line.trim()).filter(Boolean);
  if (lines.length === 0) {
    return { ok: false, error: 'Nomination appears to be empty. Paste the mini-form to submit.' };
  }

  const albumLine = lines[0];
  const albumId = extractAlbumId(lines.join(' '));

  const whyLine = lines.find((line) => line.toLowerCase().startsWith('why'));
  const pitchTrackLine = lines.find((line) => line.toLowerCase().startsWith('pitch track'));
  const tagsLine = lines.find((line) => line.toLowerCase().startsWith('tags'));

  const pitch = whyLine ? whyLine.split(':').slice(1).join(':').trim() : null;
  const pitchTrack = pitchTrackLine ? pitchTrackLine.split(':').slice(1).join(':').trim() : null;

  let genre: string | null = null;
  let decade: string | null = null;
  let country: string | null = null;
  if (tagsLine) {
    const tagPayload = tagsLine.split(':').slice(1).join(':').trim();
    const [genrePart, decadePart, countryPart] = tagPayload.split('/').map((part) => part.trim());
    genre = genrePart || null;
    decade = decadePart || null;
    country = countryPart || null;
  }

  if (!albumLine) {
    return { ok: false, error: 'Missing album line. Format: Album — Artist (Year)' };
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
    genre,
    decade,
    country,
  };
}

function extractAlbumId(input: string): string | undefined {
  const uuidRegex =
    /album:\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i;
  const match = input.match(uuidRegex);
  return match ? match[1] : undefined;
}

function parseAlbumLine(line: string):
  | { title: string; artist: string; year: number | null }
  | undefined {
  // Expected formats:
  // Album — Artist (Year)
  // Album - Artist (Year)
  // Album — Artist
  const parts = line.split(/—|-/).map((part) => part.trim()).filter(Boolean);
  if (parts.length < 2) return undefined;

  const artistPart = parts.pop() || '';
  const title = parts.join(' - ').trim();

  const yearMatch = artistPart.match(/\((\d{4})\)$/);
  const year = yearMatch ? Number(yearMatch[1]) : null;
  const artist = artistPart.replace(/\(\d{4}\)$/, '').trim();

  if (!title || !artist) return undefined;

  return { title, artist, year };
}
