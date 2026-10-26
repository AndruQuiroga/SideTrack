import { ModalBuilder, TextInputBuilder, TextInputStyle, ActionRowBuilder } from 'discord.js';

/**
 * Build the nomination modal form.
 *
 * Simplified from the original — tags and year are now auto-filled via
 * MusicBrainz/Spotify enrichment. Pitch track is REQUIRED.
 */
export function buildNominationModal(weekId: string): ModalBuilder {
  const modal = new ModalBuilder()
    .setCustomId(`nomination:submit:${weekId}`)
    .setTitle('Nominate an Album');

  const albumInput = new TextInputBuilder()
    .setCustomId('album')
    .setLabel('Album Title')
    .setPlaceholder('e.g., OK Computer')
    .setStyle(TextInputStyle.Short)
    .setRequired(true)
    .setMaxLength(200);

  const artistInput = new TextInputBuilder()
    .setCustomId('artist')
    .setLabel('Artist')
    .setPlaceholder('e.g., Radiohead')
    .setStyle(TextInputStyle.Short)
    .setRequired(true)
    .setMaxLength(200);

  const pitchInput = new TextInputBuilder()
    .setCustomId('pitch')
    .setLabel('Why should we listen?')
    .setPlaceholder('A brief pitch for why the club should check this out...')
    .setStyle(TextInputStyle.Paragraph)
    .setRequired(true)
    .setMaxLength(500);

  const pitchTrackInput = new TextInputBuilder()
    .setCustomId('pitch_track')
    .setLabel('Pitch Track (Spotify or YouTube link)')
    .setPlaceholder('https://open.spotify.com/track/...')
    .setStyle(TextInputStyle.Short)
    .setRequired(true)
    .setMaxLength(500);

  modal.addComponents(
    new ActionRowBuilder<TextInputBuilder>().addComponents(albumInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(artistInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(pitchInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(pitchTrackInput),
  );

  return modal;
}

/**
 * Build the edit nomination modal — pre-filled with current pitch and track.
 *
 * Only allows editing pitch text and pitch track URL (not the album itself).
 */
export function buildNominationEditModal(
  nominationId: string,
  currentPitch?: string | null,
  currentPitchTrackUrl?: string | null,
): ModalBuilder {
  const modal = new ModalBuilder()
    .setCustomId(`nomination:edit-submit:${nominationId}`)
    .setTitle('Edit Nomination');

  const pitchInput = new TextInputBuilder()
    .setCustomId('pitch')
    .setLabel('Why should we listen?')
    .setPlaceholder('Update your pitch...')
    .setStyle(TextInputStyle.Paragraph)
    .setRequired(true)
    .setMaxLength(500);
  if (currentPitch) pitchInput.setValue(currentPitch);

  const pitchTrackInput = new TextInputBuilder()
    .setCustomId('pitch_track')
    .setLabel('Pitch Track (Spotify or YouTube link)')
    .setPlaceholder('https://open.spotify.com/track/...')
    .setStyle(TextInputStyle.Short)
    .setRequired(true)
    .setMaxLength(500);
  if (currentPitchTrackUrl) pitchTrackInput.setValue(currentPitchTrackUrl);

  modal.addComponents(
    new ActionRowBuilder<TextInputBuilder>().addComponents(pitchInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(pitchTrackInput),
  );

  return modal;
}

/**
 * Build the change-album modal — for switching the entire nominated album.
 *
 * Pre-filled with current album/artist, requires new pitch and pitch track
 * since the album is changing.
 */
export function buildAlbumChangeModal(
  nominationId: string,
  currentAlbumTitle?: string | null,
  currentArtist?: string | null,
  currentPitch?: string | null,
): ModalBuilder {
  const modal = new ModalBuilder()
    .setCustomId(`nomination:change-album-submit:${nominationId}`)
    .setTitle('Change Album');

  const albumInput = new TextInputBuilder()
    .setCustomId('album')
    .setLabel('New Album Title')
    .setPlaceholder('e.g., Kid A')
    .setStyle(TextInputStyle.Short)
    .setRequired(true)
    .setMaxLength(200);
  if (currentAlbumTitle) albumInput.setValue(currentAlbumTitle);

  const artistInput = new TextInputBuilder()
    .setCustomId('artist')
    .setLabel('Artist')
    .setPlaceholder('e.g., Radiohead')
    .setStyle(TextInputStyle.Short)
    .setRequired(true)
    .setMaxLength(200);
  if (currentArtist) artistInput.setValue(currentArtist);

  const pitchInput = new TextInputBuilder()
    .setCustomId('pitch')
    .setLabel('Why should we listen?')
    .setPlaceholder('Update your pitch for the new album...')
    .setStyle(TextInputStyle.Paragraph)
    .setRequired(true)
    .setMaxLength(500);
  if (currentPitch) pitchInput.setValue(currentPitch);

  const pitchTrackInput = new TextInputBuilder()
    .setCustomId('pitch_track')
    .setLabel('Pitch Track (Spotify or YouTube link)')
    .setPlaceholder('https://open.spotify.com/track/...')
    .setStyle(TextInputStyle.Short)
    .setRequired(true)
    .setMaxLength(500);

  modal.addComponents(
    new ActionRowBuilder<TextInputBuilder>().addComponents(albumInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(artistInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(pitchInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(pitchTrackInput),
  );

  return modal;
}

/**
 * Build the rating modal form.
 */
export function buildRatingModal(weekId: string): ModalBuilder {
  const modal = new ModalBuilder()
    .setCustomId(`rating:submit:${weekId}`)
    .setTitle('Rate This Album');

  const scoreInput = new TextInputBuilder()
    .setCustomId('score')
    .setLabel('Score (1.0 - 5.0)')
    .setPlaceholder('e.g., 4.5')
    .setStyle(TextInputStyle.Short)
    .setRequired(true)
    .setMaxLength(5);

  const favoriteTrackInput = new TextInputBuilder()
    .setCustomId('favorite_track')
    .setLabel('Favorite Track (optional)')
    .setPlaceholder('e.g., Paranoid Android')
    .setStyle(TextInputStyle.Short)
    .setRequired(false)
    .setMaxLength(200);

  const reviewInput = new TextInputBuilder()
    .setCustomId('review')
    .setLabel('Thoughts (optional)')
    .setPlaceholder('Share your brief thoughts on the album...')
    .setStyle(TextInputStyle.Paragraph)
    .setRequired(false)
    .setMaxLength(500);

  modal.addComponents(
    new ActionRowBuilder<TextInputBuilder>().addComponents(scoreInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(favoriteTrackInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(reviewInput),
  );

  return modal;
}
