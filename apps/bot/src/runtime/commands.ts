import { SlashCommandBuilder, SlashCommandSubcommandBuilder } from 'discord.js';

// /ping - Basic health check
export const pingCommand = {
  data: new SlashCommandBuilder()
    .setName('ping')
    .setDescription('Check if Sidetrack bot is online'),
};

// /st-week start|overview - Week management
export const stWeekCommand = {
  data: new SlashCommandBuilder()
    .setName('st-week')
    .setDescription('Manage Sidetrack Club weeks')
    .addSubcommand((sub: SlashCommandSubcommandBuilder) =>
      sub
        .setName('start')
        .setDescription('Create a new week and open nominations')
        .addStringOption((option) =>
          option
            .setName('label')
            .setDescription('Week label, e.g., WEEK 003 [2025-11-24]')
            .setRequired(true),
        )
        .addIntegerOption((option) =>
          option
            .setName('week_number')
            .setDescription('Numeric week number (optional)')
            .setRequired(false),
        )
        .addStringOption((option) =>
          option
            .setName('nominations_close_at')
            .setDescription('Nominations close time (ISO timestamp)')
            .setRequired(false),
        )
        .addStringOption((option) =>
          option
            .setName('poll_close_at')
            .setDescription('Poll close time (ISO timestamp)')
            .setRequired(false),
        )
        .addStringOption((option) =>
          option
            .setName('discussion_at')
            .setDescription('Discussion time (ISO timestamp)')
            .setRequired(false),
        ),
    )
    .addSubcommand((sub: SlashCommandSubcommandBuilder) =>
      sub
        .setName('overview')
        .setDescription('Show the current week overview')
        .addStringOption((option) =>
          option
            .setName('week_id')
            .setDescription('Week ID (defaults to latest open week)')
            .setRequired(false),
        ),
    ),
};

// /st-nominate - Submit a nomination
export const stNominateCommand = {
  data: new SlashCommandBuilder()
    .setName('st-nominate')
    .setDescription('Nominate an album for the current week')
    .addStringOption((option) =>
      option
        .setName('week_id')
        .setDescription('Week ID (defaults to current open week)')
        .setRequired(false),
    ),
};

// /st-poll open|close - Poll management
export const stPollCommand = {
  data: new SlashCommandBuilder()
    .setName('st-poll')
    .setDescription('Manage the week poll')
    .addSubcommand((sub: SlashCommandSubcommandBuilder) =>
      sub
        .setName('open')
        .setDescription('Open voting for the current week')
        .addStringOption((option) =>
          option
            .setName('week_id')
            .setDescription('Week ID (defaults to current open week)')
            .setRequired(false),
        ),
    )
    .addSubcommand((sub: SlashCommandSubcommandBuilder) =>
      sub
        .setName('close')
        .setDescription('Close voting and announce the winner')
        .addStringOption((option) =>
          option
            .setName('week_id')
            .setDescription('Week ID (defaults to current open week)')
            .setRequired(false),
        ),
    ),
};

// /st-ratings open|summary - Ratings management
export const stRatingsCommand = {
  data: new SlashCommandBuilder()
    .setName('st-ratings')
    .setDescription('Manage album ratings')
    .addSubcommand((sub: SlashCommandSubcommandBuilder) =>
      sub
        .setName('open')
        .setDescription('Open ratings for the winning album')
        .addStringOption((option) =>
          option
            .setName('week_id')
            .setDescription('Week ID (defaults to current open week)')
            .setRequired(false),
        ),
    )
    .addSubcommand((sub: SlashCommandSubcommandBuilder) =>
      sub
        .setName('summary')
        .setDescription('Show the ratings summary for a week')
        .addStringOption((option) =>
          option
            .setName('week_id')
            .setDescription('Week ID (defaults to current open week)')
            .setRequired(false),
        ),
    ),
};

// /st-help - Help command
export const stHelpCommand = {
  data: new SlashCommandBuilder()
    .setName('st-help')
    .setDescription('Show Sidetrack Club commands and weekly flow'),
};

// Legacy command for backwards compatibility
export const weekStartCommand = {
  data: new SlashCommandBuilder()
    .setName('week-start')
    .setDescription('[DEPRECATED] Use /st-week start instead')
    .addStringOption((option) =>
      option
        .setName('label')
        .setDescription('Week label, e.g., WEEK 003 [2025-11-24]')
        .setRequired(true),
    )
    .addIntegerOption((option) =>
      option.setName('week_number').setDescription('Numeric week number (optional)').setRequired(false),
    )
    .addStringOption((option) =>
      option
        .setName('nominations_close_at')
        .setDescription('Nominations close time (ISO timestamp)')
        .setRequired(false),
    )
    .addStringOption((option) =>
      option
        .setName('poll_close_at')
        .setDescription('Poll close time (ISO timestamp)')
        .setRequired(false),
    )
    .addStringOption((option) =>
      option
        .setName('discussion_at')
        .setDescription('Discussion time (ISO timestamp)')
        .setRequired(false),
    ),
};

// All commands to register
export const allCommands = [
  pingCommand,
  stWeekCommand,
  stNominateCommand,
  stPollCommand,
  stRatingsCommand,
  stHelpCommand,
  weekStartCommand,
];

export type RegisteredCommand =
  | typeof pingCommand
  | typeof stWeekCommand
  | typeof stNominateCommand
  | typeof stPollCommand
  | typeof stRatingsCommand
  | typeof stHelpCommand
  | typeof weekStartCommand;
