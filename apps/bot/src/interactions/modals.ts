import {
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle,
  ActionRowBuilder,
} from 'discord.js';

/**
 * Build the nomination modal form.
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

  const linkInput = new TextInputBuilder()
    .setCustomId('link')
    .setLabel('Link (Spotify, Bandcamp, etc.)')
    .setPlaceholder('https://open.spotify.com/album/...')
    .setStyle(TextInputStyle.Short)
    .setRequired(false)
    .setMaxLength(500);

  const pitchInput = new TextInputBuilder()
    .setCustomId('pitch')
    .setLabel('Why should we listen? (Pitch)')
    .setPlaceholder('A brief pitch for why the club should check this out...')
    .setStyle(TextInputStyle.Paragraph)
    .setRequired(true)
    .setMaxLength(500);

  const tagsInput = new TextInputBuilder()
    .setCustomId('tags')
    .setLabel('Tags (Genre / Decade / Country)')
    .setPlaceholder('e.g., rock / 90s / UK')
    .setStyle(TextInputStyle.Short)
    .setRequired(false)
    .setMaxLength(100);

  modal.addComponents(
    new ActionRowBuilder<TextInputBuilder>().addComponents(albumInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(artistInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(pitchInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(linkInput),
    new ActionRowBuilder<TextInputBuilder>().addComponents(tagsInput),
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
