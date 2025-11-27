// Sample static data to sketch the UI. Replace with real API calls later.
export type WeekSummary = {
  id: string;
  label: string;
  date: string;
  winner: {
    album: string;
    artist: string;
    year: number;
    coverUrl?: string;
  };
  avgRating: number;
  ratingsCount: number;
  participants: number;
  tags: string[];
};

export type NomineeSummary = {
  id: string;
  album: string;
  artist: string;
  year: number;
  nominator: string;
  pitch: string;
  score: number;
  rank: 1 | 2 | 3 | 4 | 5;
};

export type RatingSummary = {
  user: string;
  value: number;
  favoriteTrack?: string;
  highlight?: string;
};

export type WeekDetail = {
  id: string;
  label: string;
  date: string;
  winner: WeekSummary["winner"];
  avgRating: number;
  ratingsCount: number;
  participants: number;
  tags: string[];
  nominees: NomineeSummary[];
  ratings: RatingSummary[];
};

export type ProfileOverview = {
  handle: string;
  displayName: string;
  avatarUrl?: string;
  tagline?: string;
  stats: {
    albumsRated: number;
    weeksJoined: number;
    avgRating: number;
  };
  topGenres: string[];
  recentAlbums: {
    album: string;
    artist: string;
    rating?: number;
  }[];
};

export const weeks: WeekSummary[] = [
  {
    id: "week-003",
    label: "WEEK 003 · Dusk to Dawn",
    date: "2025-11-24",
    winner: {
      album: "DUSK to DAWN",
      artist: "Boslen",
      year: 2021,
      coverUrl: "https://images.pexels.com/photos/164745/pexels-photo-164745.jpeg?auto=compress&cs=tinysrgb&w=400",
    },
    avgRating: 4.1,
    ratingsCount: 7,
    participants: 8,
    tags: ["Hip-Hop", "2020s", "Canada"],
  },
  {
    id: "week-002",
    label: "WEEK 002 · Gawk",
    date: "2025-11-17",
    winner: {
      album: "Gawk",
      artist: "Vundabar",
      year: 2015,
    },
    avgRating: 3.8,
    ratingsCount: 6,
    participants: 7,
    tags: ["Indie Rock", "2010s", "USA"],
  },
  {
    id: "week-001",
    label: "WEEK 001 · Singles Night",
    date: "2025-11-10",
    winner: {
      album: "Singles Night Playlist",
      artist: "Sidetrack Club",
      year: 2025,
    },
    avgRating: 4.3,
    ratingsCount: 6,
    participants: 6,
    tags: ["Mixed", "Varied", "Club Special"],
  },
];

export const weekDetails: Record<string, WeekDetail> = {
  "week-003": {
    id: "week-003",
    label: "WEEK 003 [2025-11-24] · DUSK to DAWN — Boslen",
    date: "2025-11-24",
    winner: weeks[0].winner,
    avgRating: weeks[0].avgRating,
    ratingsCount: weeks[0].ratingsCount,
    participants: weeks[0].participants,
    tags: weeks[0].tags,
    nominees: [
      {
        id: "nom-1",
        album: "DUSK to DAWN",
        artist: "Boslen",
        year: 2021,
        nominator: "Dreski",
        pitch: "Moody, nocturnal hip-hop with cinematic production and a strong sense of atmosphere.",
        score: 5,
        rank: 1,
      },
      {
        id: "nom-2",
        album: "Gawk",
        artist: "Vundabar",
        year: 2015,
        nominator: "User2",
        pitch: "Crunchy, off-kilter indie rock that still feels surprisingly catchy.",
        score: 4,
        rank: 2,
      },
      {
        id: "nom-3",
        album: "SMITHEREENS",
        artist: "Joji",
        year: 2022,
        nominator: "User3",
        pitch: "Sadboy pop with some beautiful production and compact runtime.",
        score: 4,
        rank: 3,
      },
    ],
    ratings: [
      {
        user: "Dreski",
        value: 4.5,
        favoriteTrack: "DUSK to DAWN",
        highlight: "Loved how cohesive the front half feels as a nighttime drive record.",
      },
      {
        user: "User1",
        value: 4.0,
        favoriteTrack: "LEVELS",
        highlight: "Production goes hard, a couple tracks in the middle sag a bit for me.",
      },
      {
        user: "User2",
        value: 3.5,
        favoriteTrack: "TURBO",
        highlight: "Good energy, not fully my lane but the curated mood is on point.",
      },
    ],
  },
};

export const profiles: Record<string, ProfileOverview> = {
  dreski: {
    handle: "dreski",
    displayName: "Dreski",
    tagline: "Organizer of chaos · Hip-hop / alt-head",
    stats: {
      albumsRated: 127,
      weeksJoined: 14,
      avgRating: 3.9,
    },
    topGenres: ["Alternative R&B", "Indie Rock", "Trap", "Alt-Pop"],
    recentAlbums: [
      { album: "DUSK to DAWN", artist: "Boslen", rating: 4.5 },
      { album: "Gawk", artist: "Vundabar", rating: 4.0 },
      { album: "SMITHEREENS", artist: "Joji", rating: 3.5 },
    ],
  },
};
