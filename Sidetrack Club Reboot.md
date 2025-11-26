# Sidetrack Club Reboot: Integrated Music Club & Social Tracker

**Project Overview:** We’re merging the weekly **Sidetrack music club** with a personal **music taste tracker**, relaunching as a unified platform. The vision is an ecosystem with a Discord bot automating the club events, a sleek web app showcasing club archives, and a social music tracking site that analyzes tastes and lets users connect. Below we break down the plan into three major components, with additional features and integration details.

## Discord Bot for Weekly Album Club Automation

The Discord bot will manage the entire weekly album club on our server, reducing manual effort and adding interactivity. Key features include:

* **Automated Thread Management:** On a set schedule, the bot creates forum threads for each stage (Nominations, Poll, Winner Announcement, and Ratings). It can post the formatted “mini-form” templates (for nominations and ratings) and pin them for easy copying. This ensures each week’s channels are consistently structured.

* **Scheduled Reminders & Deadlines:** The bot tracks the club’s timeline. It sends reminder messages (e.g. “❗ Nominations close in 1 hour”) and automatically closes stages:

* Closes the nomination thread at the deadline and immediately opens the voting poll.

* Closes the poll after \~24 hours and announces the winner.

* Schedules the discussion event reminder (e.g. day/time for listening party).

* Opens the rating thread at discussion time.

* **Custom Poll System (Ranked Voting):** Implement a voting mechanism for first and second choice ranking. This could be two poll messages or interactive buttons where members submit their \#1 and \#2 picks. The bot tallies votes with the scoring system (first choice \= 2 points, second \= 1\) and determines the winner (tie-break by most first-place votes). If Discord’s native polls are used, the bot ensures each user only votes once per poll and not for their own nomination (enforcing the “can’t pick yourself” rule).

* **Rich Embeds and Integrations:** The bot can enhance posts with album info:

* When someone nominates an album, the bot could fetch album details (cover art, artist, year) from the music database and embed a thumbnail for a polished look.

* The poll post can list nominees with hyperlinks (e.g. to Spotify or YouTube) for quick reference.

* The winner announcement thread will include the album cover, a Spotify album link, and the final poll ranking in an embedded format for at-a-glance readability.

* **Rating Collection and Tracking:** In the ratings thread, users will post their 1.0–5.0 star ratings (with optional comments). The bot listens for these posts:

* It validates the format (ensuring a numeric rating in range).

* Automatically tallies ratings in real-time or after the discussion (e.g. compute average rating, count of participants).

* It could react to a valid rating post to confirm it’s logged. At the end, the bot can post a summary (average score, maybe a star distribution).

* **Integration with Web Backend:** The bot will push all club data to the central database or API:

* New nominations (album, who nominated, their pitch, tags) get saved.

* Poll results and winner info saved once voting concludes.

* Ratings and reviews from members saved as well. This ensures the website can display up-to-date club information. The bot will use either direct DB access or secure API calls to send this data as events happen.

* **User Identification:** To connect Discord activity to website profiles, the bot should record Discord user IDs. We’ll allow users to link their Discord to their site account (e.g. via OAuth or a one-time code). This way, the site can display who (which profile) nominated or commented, and possibly allow Discord sign-in on the site. However, **the website will remain public** for viewing, so non-members can browse the club’s archive without login.

* **Admin Controls:** Provide commands for moderators:

* e.g. /startweek to initialize new week threads if not automated, or to handle special cases.

* /endpoll to force-close voting if needed, etc.

* These ensure flexibility in case schedules shift.

Overall, the Discord bot will serve as the orchestrator for the club, handling the routine tasks and capturing all interactions, while providing a fun, seamless experience for members with embeds and timely prompts. This frees the organizers from manual tallying and post creation, and feeds the website with structured data about each week.

## Web Archive for Weekly Album Club

One part of the new site will be a **beautiful, modern archive** for the Sidetrack club’s activities. This lets both members and the public explore what the club has been up to. Key elements of this archive section:

* **Weekly Winners Gallery:** A dedicated page will list each week’s winning album in reverse chronological order. This can be a visual grid or list, showing the album cover, title, artist, and the week/date it was featured. Users can scroll through the history of the club and see all past Album-of-the-Week winners at a glance.

* **Detailed Week Pages:** Clicking a specific week will show a rich page of details for that session:

* **Album and Meta:** Prominently display the album cover, title, artist, and year. Include the member who nominated it (and perhaps their original pitch text to showcase why it was chosen).

* **Nominees and Poll Results:** List all nominated albums for that week, with who nominated each. Show the poll ranking and point totals (e.g., winner got X points, second place Y points, etc.). This provides context on how close the vote was and what other albums were in contention.

* **Tags/Genres:** Display the tags (Genre, Decade, Country) that were assigned to the winning album. These tags can be clickable to find other sessions with the same tag.

* **Ratings Summary:** Show the average rating the club gave the album (e.g. “Average Rating: 4.1 ★★★★☆”). Possibly include a breakdown (number of 5-star votes, 4.5-star, etc., maybe a small bar chart). Individual ratings can be listed or at least the count of participants.

* **Member Reviews/Comments:** Optionally, display the comments from the Discord rating thread. For example, show each member’s rating and their brief “final thoughts” if they provided any. This effectively curates the discussion highlights into a readable review section. (If a user has a site profile, their name could link to it.)

* **Club Statistics and Fun Extras:** The archive could also have an overview page with interesting stats across all weeks:

* Which genres or decades are most often winners (since tags are added, we can tally genre counts).

* A list of members with most nominations won or highest average album ratings, etc., to encourage friendly competition.

* Perhaps a “Hall of Fame” for albums or artists that got exceptionally high club ratings.

* **Public Accessibility:** This archive is publicly viewable. Even people not in the Discord can browse the albums and see the community’s thoughts. It acts as a showcase of the club’s taste and activity.

* **Responsive & Sleek Design:** The archive pages will be visually engaging – album art is a key element of design (we can pull high-quality cover images via Spotify or a music database). The layout will be clean and modern, easy to navigate by week or filter by tag. Mobile-friendly design is important so users can scroll through albums on their phones comfortably.

* **Search and Filtering:** A search bar or filters might be included:

* Search by album or artist to see if it was ever featured.

* Filter by genre tag, or by year/decade (find all albums from the 90s, etc.).

* Filter by who nominated (if users want to see all of one person’s picks).

By providing this rich web archive, we create a lasting **“digital gallery”** of the club’s journey. It not only honors the weekly efforts (people will love seeing their nominations and comments memorialized on the site) but also attracts new users who can explore and perhaps be enticed to join the club.

## Social Music Tracking Platform (Profiles, Friends & Listening Habits)

The core of the new project is a social music tracking website – essentially a platform for users to log and analyze their music listening, compare tastes, and engage with each other’s musical journey. We want to incorporate features from the original Sidetrack idea (mood/taste analysis) and expand with social connectivity. Major features include:

* **User Profiles & Dashboards:** Each user gets a profile page that showcases their musical taste and stats:

* **Listening History Stats:** Display data like top artists, top genres, favorite albums, and total songs listened. This can be time-filtered (e.g. last 7 days, last month, all-time) similar to Last.fm’s charts.

* **Taste Metrics:** Include more novel analytics – for example, mood or energy averages, tempo preferences, etc. If we analyze songs for features (energy, valence, danceability, etc.), we can show fun info like “Your music is 70% happy and 30% melancholic on average” or “Favorite Mood: Energetic and Upbeat”.

* **Visualizations:** Generate charts or graphs that are easy to read. This could be bar charts of genre breakdown, or even unique visuals like an “audio fingerprint” of the user’s taste. (The system might create an image representing their taste profile).

* **Listening Timeline:** A chronological feed or calendar of what they listened to recently. For example, a timeline showing recent albums or a calendar heatmap of listening activity by day.

* **Music Tracking & Scrobbling Integration:** We will integrate with **Last.fm and Spotify** to pull in users’ listening data automatically:

* Users can connect their Last.fm account (or Spotify directly) to import their scrobbles (song play history). This populates their profile with all the music they’ve been listening to[\[1\]](https://fm.bot/#:~:text=The%20bot%20connects%20to%20a,in%20the%20bot%20afterwards).

* Real-time or periodic updates: if the user is currently playing a song on Spotify, the site can show “Now Playing” on their profile (via Spotify’s API, if authorized). This creates a live feel where friends can see what each other are listening to at the moment[\[2\]](https://fm.bot/#:~:text=,info%20for%20your%20favorite%20artists).

* If the user doesn’t use Last.fm, we can use the Spotify Web API’s “recently played” endpoints to get their listens. We might combine both sources to ensure completeness.

* **Manual logging option:** Additionally, allow users to manually log or rate music they’ve listened to (similar to Goodreads/Anilist style “I completed this album”). This is useful for those who want to track specific listens or retroactively add things from before they connected their accounts.

* **Rating and Review System:** Taking inspiration from AniList’s approach to media tracking, let users **rate albums/songs** they’ve listened to and write short reviews or notes:

* A user could mark an album as “listened” and give it a star rating (or a 10-point scale, but star 5-point with halves is consistent with the club).

* They can write a brief review or tag it with moods/genres they felt.

* These ratings can be private or public; if public, friends can see each other’s ratings and reviews. This adds a dimension beyond just play count – it captures qualitative preference.

* **Social Networking Features:** The platform will encourage social interaction around music:

* **Friends/Follow System:** Users can follow each other’s profiles. This could be a mutual friend model or a one-way follow (like Twitter/Letterboxd) so you can see someone’s musical updates without requiring permission.

* **Feed of Activity:** A personalized news feed shows updates from friends – e.g. “Alex just rated *OK Computer* ★★★★★” or “Jordan is now listening to *Boslen – DUSK to DAWN*”. This keeps users engaged and discovering music through friends.

* **Compare Tastes:** Provide a feature to compare two users’ musical compatibility[\[3\]](https://fm.bot/#:~:text=,bot%20with%20our%20global%20commands). For example, on a friend’s profile you might see a “Taste Match: 82%” and click to see overlapping top artists or a Venn diagram of favorite albums. This could be computed from genre overlap, common artists listened, and rating similarities. We can even gamify it with “compatibility scores” and fun badges (“You and Sam both love Pop Punk\!”).

* **Global Community Stats:** Beyond friends, users can explore overall trends – e.g. a page showing most popular artists or albums among all users of the platform (or trending music this week). This leverages the aggregated data we collect.

* **Listening Along & Real-Time Features:** We want to capture the feeling of sharing music in real time:

* The site could show which friends are “Currently Listening” and what track it is, updating live. Perhaps a user can click a friend’s current track and get a 30-second preview or a link to open it on Spotify to listen along.

* We might integrate Spotify’s playback or a group listening session (if Spotify offers group sessions via API) so a group of friends can sync up an album listen virtually. Even if not at launch, this is a future avenue for “listen parties” outside the official club events.

* **Recommendations and Playlists:** To make the platform truly engaging, we add ways to discover music:

* **Personalized Recommendations:** Use the user’s listening history and ratings to suggest new music they might like. This could tie into the “mood/taste analysis” engine (e.g., “You seem to enjoy atmospheric, mellow tracks, how about this new album in that vibe?”). Also, leverage similar listeners – “Users with similar taste to you loved this album you haven’t heard yet.”

* **Friend Recommendations:** A feature where you can directly recommend a song/album to a friend. For example, a “Suggest a Song” button on a friend’s profile lets you pick a track (search our music database) and maybe include a note. The friend receives the recommendation and can acknowledge or listen.

* **Auto-Generated Playlists:** The system can create playlists based on data:

  * “Friend Blend”: a playlist of tracks combining you and a friend’s recent favorites.

  * “Top Weekly Picks”: songs that are trending among your friends or the whole userbase this week.

  * “Throwback Friday”: an automatic mix of songs you loved in the past but haven’t heard recently.

  * These playlists could be exported to Spotify via API so the user can play them easily.

* **Community Integration (Club & Beyond):** Since this platform also hosts the album club archive, we can connect the two:

* Users in the club can have a badge or indicator on their profile (e.g. “Sidetrack Club Member”) and their contributions to club (like number of nominations, avg rating given) could show on their profile.

* The broader userbase can see the club’s top-rated albums or participate in open polls if we ever open certain events to everyone.

* Perhaps host other music challenges or listening events on the site for any user, not just the private club. For example, a “global album of the week” poll open to all site members as a fun engagement.

All these features center around making music listening a **social, interactive experience** rather than a solitary one. By combining automated tracking (from Spotify/Last.fm) with user input (ratings, friends, posts), we’ll create a platform that not only logs data but builds a community around it, much like Last.fm plus the review features of anilist/Goodreads. The emphasis is on sleek design, ease of use, and interactive discovery.

## Data Integration & Music Analysis Engine

To power the above features, we need robust data integration and a specialized analysis component for music characteristics:

* **Music Metadata Database (MusicBrainz):** We will utilize the open-source MusicBrainz database to have a comprehensive catalog of songs, albums, and artists. By running a local MusicBrainz mirror or using their library, we can quickly look up any album or track by name. This gives us details like release year, track listings, album art, genres, etc. Having a local database keeps searches fast and avoids rate limits[\[4\]](https://musicbrainz.org/doc/MusicBrainz_Database#:~:text=Consumers%20of%20our%20database%20may,at%20the%20MetaBrainz%20Foundation%20site). It also allows advanced queries (like finding all albums in a genre or from a certain country if we store those tags). MusicBrainz data (and possibly its genre tags) will be the backbone for identifying music across the platform.

* **Spotify API Integration:** Spotify’s API will be heavily leveraged:

* **OAuth & Playback:** Users can connect their Spotify account to enable features. With permissions, we can get their currently playing track, recently played tracks, and even control playback or queue songs (if we do a listen-along feature).

* **Audio Features:** Spotify provides audio feature data for tracks (energy, valence/happiness, tempo, danceability, etc.). We will fetch these for tracks the user listens to. This gives a quick basis for our mood analysis – for example, a track’s “valence” and “energy” can indicate how upbeat or calm it is.

* **Cover Art and Previews:** We can use Spotify to fetch high-quality album covers and 30-second preview clips for songs, enriching both the Discord bot’s embeds and the website’s UI.

* **Playlist Integration:** If we generate playlists (e.g. recommendation mixes or friend blends), the Spotify API allows us to create a playlist on the user’s account for convenience.

* **Last.fm & ListenBrainz Integration:** Not all users will have Spotify or want to share it, so:

* **Last.fm:** We’ll support Last.fm scrobble importing. By entering their Last.fm username (and possibly an API key auth), we can regularly fetch their recent scrobbles. Last.fm might also provide top artist/album charts and tags from the user’s profile which we can use.

* **ListenBrainz:** ListenBrainz is an open alternative to Last.fm. If a user prefers, they can provide their ListenBrainz user/token and we can retrieve similar listening data from there (our previous Sidetrack code already had a client for this).

* Using these sources means the platform can stay updated with what users listen to, regardless of platform. We will likely set up background jobs that poll these APIs periodically (e.g. every few minutes fetch new listens) and update our database.

* **Mood & Taste Analysis Service:** A core unique feature from the original project is analyzing the “mood” or “taste fingerprint” of music. This will be handled by a dedicated service or module:

* **Audio Feature Extraction:** For comprehensive analysis, we might go beyond Spotify’s features and extract our own. For example, using a DSP library or ML model to analyze a track’s audio waveform for characteristics (spectral features, mood classification, etc.). This could involve a heavy computation (hence separate from the main web app). If needed, we can queue analysis jobs for tracks that aren’t in Spotify’s database (or to compute custom metrics like “pumpiness” as in the old project).

* **Mood Axes and Scoring:** We can define a set of axes or dimensions for musical mood/taste – e.g. Energy, Happiness, Aggressiveness, Danceability, Acoustic vs Electronic. Each track can be scored on these axes either using Spotify data or a neural network that generates an embedding[\[5\]](https://github.com/AndruQuiroga/SideTrack/blob/7c93179ecedab40592161e2544630ea7f54e789f/sidetrack/api/main.py#L8-L17). The user’s aggregate listening can then be represented in these dimensions (like showing which moods they gravitate towards).

* **Machine Learning & Recommendations:** With a library of track features and user listening data, we can apply ML for recommendation or clustering:

  * Cluster songs or artists into “mood clusters” and show the user which clusters they listen to most.

  * A recommendation engine that finds songs with similar feature vectors to what the user loves, or identifies outliers to suggest for variety.

  * Possibly a “mood prediction” – if the user inputs their current mood, the system could recommend music from their library (or new music) to match or alter that mood.

* This service will likely use frameworks like TensorFlow/PyTorch for any heavy ML and could require a GPU for tasks like audio analysis. To keep things scalable, these tasks will run asynchronously (e.g. in background workers). The web frontend can show partial data (recent songs) immediately and fill in analysis results as they come.

* **Data Storage & Security:** All this integration means handling a lot of data:

* We’ll have a central database (likely PostgreSQL) storing users, their linked accounts (Discord, Spotify, Last.fm), and all listening records, ratings, etc. Tables for tracks, artists, albums will link to the MusicBrainz IDs so everything is normalized.

* User credentials like API tokens (Spotify refresh tokens, Last.fm session keys) will be stored securely (encrypted at rest) since they grant access to sensitive data. We’ll also respect privacy settings – for example, allow a user to mark their listening history private or anonymize data in global stats if they opt out.

* Caching will be important for performance. Recently played tracks or frequently accessed stats can be cached in memory/Redis so that the site feels snappy, even though a lot of computation (like generating charts) might be done offline or periodically.

* The MusicBrainz mirror (if used) would likely be another PostgreSQL database with its own update feed. We might also use Elasticsearch or a similar search engine on top of it for faster full-text search on song/artist names.

By integrating these data sources and analysis tools, the platform will have a rich foundation of musical knowledge. Users will benefit from accurate metadata, insightful analytics, and real-time updates from their streaming services. This combination of **social data (from friends)** and **musical data (from APIs and analysis)** is what will make our platform powerful and unique.

## Architecture and Component Breakdown

Given the scope, the project will be organized into multiple components (services) that work in concert. This modular approach ensures each piece can be developed and maintained somewhat independently, and we can scale or upgrade parts as needed:

* **1\. Discord Bot Service:** A standalone service (likely built with discord.py or a similar library) that runs continuously. It will be configured with the Discord server and channel IDs for the club, and the schedule for weekly events. The bot will have its own connection to the central database or via an internal API. It essentially bridges Discord interactions to our system:

* When users nominate or vote or rate, the bot processes it and sends it to the backend.

* It also pulls data from the backend (e.g., the album cover or tags for an album) to enrich its Discord messages.

* Running this separately means we could restart the web app without affecting the bot’s uptime, etc.

* **2\. Backend API Server:** This will be the core of the platform, handling all business logic and data storage. We can use a framework like FastAPI (as in the original project) or Django/Express – but FastAPI worked well in Sidetrack before. Key responsibilities:

* Expose REST/GraphQL endpoints for the frontend to fetch data (e.g. user profile info, list of weekly winners, search results).

* Endpoints for the Discord bot to post club data (secured with a bot token).

* Implement all the logic for accounts, friend relationships, computing stats from the database, and so on.

* This service will talk to the database (Postgres) and perhaps to a cache (Redis) for rate limiting and caching.

* **3\. Frontend Web App:** A modern single-page application (SPA) or server-rendered app for the website. We want a **sleek, modern UI** with dynamic content. Likely choices are React (maybe Next.js for SSR) or Vue, with a strong design system (could use Tailwind CSS or Material UI for polish, but maybe a custom design given the emphasis on sleekness).

* The frontend will consume the API to display user profiles, club archives, etc. It should handle routing for different pages (Home feed, Profile, Archive, Week detail, etc.).

* Real-time aspects (like showing currently playing songs or live updates of now-playing) might use WebSockets or polling. We could integrate a WebSocket service for push updates (the backend can push “user X is now playing Y” to their friends).

* Since visual appeal is key, we might spend effort on custom CSS and interactive charts (using libraries like D3.js or Chart.js for the stats visualizations).

* Ensure mobile responsiveness and a good UX for both heavy users (who might browse lots of stats) and casual visitors (who might just see the club archive or a friend’s profile).

* **4\. Background Workers (Analysis & Sync Jobs):** A separate worker process (or set of processes) will handle tasks that are periodic or intensive:

* Polling tasks: e.g., every 5 minutes fetch new listens from connected Spotify/Lastfm accounts and update the DB.

* Analysis tasks: when a new track is encountered that we have no analysis for, enqueue a job to compute its features (this might involve calling external APIs or running an audio analysis). As noted, using a queue system like RQ (Redis Queue) or Celery will help manage these asynchronously.

* Batch computations: e.g., aggregating weekly mood scores or updating the “trending songs” daily.

* These workers ensure the API server and bot remain fast and responsive, offloading heavy lifting to the background.

* **5\. Database and Storage:** We will use a relational database (PostgreSQL) for core data (users, tracks, listens, club posts). If needed, we might have additional specialized storage:

* Time-series DB or OLAP for analytical queries (though Postgres with proper indexing might suffice, or we can use something like ClickHouse if the data gets huge and we need fast analytic queries on listening data).

* A separate database for MusicBrainz (if we go the local mirror route) as mentioned.

* We should also consider storage for user-uploaded content, though here most content is external (album art from Spotify, etc.). Maybe store user profile avatars or custom images if any (or just use their Spotify/Discord avatars via integration).

* **6\. Integration Modules:** Modules or micro-services to handle third-party integration securely:

* For example, a small service or module for Spotify that can handle OAuth callback, refresh tokens, and make API calls (so that the logic to interact with Spotify is encapsulated).

* Similarly for Last.fm – handle authentication and API calls in one place.

* This separation means if an API changes or we add Apple Music support later, we can do so without touching core logic.

All components will be containerized (e.g., using Docker) to ease deployment. In development, we can run everything via docker-compose (one container for web, one for bot, one for workers, one for DB, etc.). In production, services can be scaled individually (e.g., run multiple web app instances behind a load balancer if traffic grows, or multiple workers for more concurrent jobs if the user base and data volume increases).

**Integration of Components:** The Discord bot and frontend both rely on the backend API and database, so designing clear API contracts is crucial. For instance, when the bot creates a new week, it might call POST /api/club/weeks to create a new entry, then the backend returns an ID which the bot can store and use for linking messages to the database record. The web frontend then simply fetches /api/club/weeks to display all weeks, etc. Using consistent IDs (like a Discord thread ID stored in the DB) could allow deep-linking from the site to the Discord (e.g., “View Discussion on Discord” link).

**Security & Access Control:** The site will allow public reading but certain actions (like viewing a private profile or the raw listening history) require login. We’ll implement an authentication system (JWT or session cookies) for the web users. Users can sign up with email/password or OAuth (Google/Spotify/Discord). Given many might prefer convenience, enabling “Login with Discord” or “Login with Spotify” could simplify onboarding. We’ll just need to merge that with connecting their other accounts (e.g., if they log in with Discord, they still might connect Spotify to actually track music).

**Potential Future Extensions:** By laying out this architecture, we also keep it extensible: \- We could later add a mobile app that uses the same backend API. \- Other music data sources (Apple Music, YouTube Music) if demand arises – just add connectors and ingest their data similarly. \- Community features like forums or groups beyond the Sidetrack club (maybe allow users to create their own listening clubs on the platform). \- But initially, focusing on the Sidetrack club and individual tracking will provide a strong foundation.

---

**Thinking Between the Lines:** This plan tries to anticipate needs and missing pieces: \- We’ve included things like tag filtering, moderation controls, privacy settings, and data security which weren’t explicitly asked, but are important for a smooth, real-world application. \- The design and UX will be critical (the user emphasized sleek and modern), so we might allocate time for user testing the interface. \- Using proven systems (Discord bot for engagement, Last.fm/Spotify for data, MusicBrainz for info) means we’re not reinventing the wheel for basics, allowing us to focus on the unique combination of these elements.

By building these components, we will deliver a platform that **runs the Sidetrack club seamlessly via Discord, showcases its outcomes on a beautiful site, and offers a full-fledged social music tracking experience** for all music enthusiasts. This unified project will not only streamline the club operations but also create a space where people can bond over music, track their listening habits, and discover new tunes together.

**Sources:**

* Discord .fmbot inspiration for music social features[\[2\]](https://fm.bot/#:~:text=,info%20for%20your%20favorite%20artists)[\[3\]](https://fm.bot/#:~:text=,bot%20with%20our%20global%20commands) (shows the feasibility of sharing now-playing info and comparing tastes among friends using Last.fm data).

* MusicBrainz documentation on running a local mirror[\[4\]](https://musicbrainz.org/doc/MusicBrainz_Database#:~:text=Consumers%20of%20our%20database%20may,at%20the%20MetaBrainz%20Foundation%20site) (for a reliable, up-to-date music metadata database to power search and tagging).

---

[\[1\]](https://fm.bot/#:~:text=The%20bot%20connects%20to%20a,in%20the%20bot%20afterwards) [\[2\]](https://fm.bot/#:~:text=,info%20for%20your%20favorite%20artists) [\[3\]](https://fm.bot/#:~:text=,bot%20with%20our%20global%20commands) .fmbot

[https://fm.bot/](https://fm.bot/)

[\[4\]](https://musicbrainz.org/doc/MusicBrainz_Database#:~:text=Consumers%20of%20our%20database%20may,at%20the%20MetaBrainz%20Foundation%20site) MusicBrainz Database \- MusicBrainz

[https://musicbrainz.org/doc/MusicBrainz\_Database](https://musicbrainz.org/doc/MusicBrainz_Database)

[\[5\]](https://github.com/AndruQuiroga/SideTrack/blob/7c93179ecedab40592161e2544630ea7f54e789f/sidetrack/api/main.py#L8-L17) main.py

[https://github.com/AndruQuiroga/SideTrack/blob/7c93179ecedab40592161e2544630ea7f54e789f/sidetrack/api/main.py](https://github.com/AndruQuiroga/SideTrack/blob/7c93179ecedab40592161e2544630ea7f54e789f/sidetrack/api/main.py)