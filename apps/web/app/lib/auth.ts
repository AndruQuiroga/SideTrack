import type { AuthOptions } from 'next-auth';
import DiscordProvider from 'next-auth/providers/discord';

import { readSecret, serverApiBaseUrl, serverApiHeaders } from './server-env';

const apiBase = serverApiBaseUrl;
const apiHeaders = serverApiHeaders;

export const authOptions: AuthOptions = {
  providers: [
    DiscordProvider({
      clientId: process.env.DISCORD_CLIENT_ID!,
      clientSecret: readSecret('DISCORD_CLIENT_SECRET')!,
    }),
  ],
  secret: readSecret('NEXTAUTH_SECRET'),
  session: { strategy: 'jwt' },
  pages: { signIn: '/login' },
  callbacks: {
    async jwt({ token, account }) {
      // Only runs on first sign-in when account is present
      if (account?.provider === 'discord') {
        const discordId = account.providerAccountId;
        const base = apiBase();
        const headers = apiHeaders();

        try {
          // Try to find existing user by Discord ID
          const lookup = await fetch(`${base}/users/lookup/by-provider/discord/${discordId}`, {
            headers,
          });

          if (lookup.ok) {
            const existing = await lookup.json();
            token.userId = existing.id;
            token.handle = existing.handle;
          } else if (lookup.status === 404) {
            // Create new user
            const rawName = (token.name ?? `discord_${discordId}`) as string;
            const handle = rawName
              .toLowerCase()
              .replace(/[^a-z0-9_]/g, '_')
              .slice(0, 32);
            const created = await fetch(`${base}/users/`, {
              method: 'POST',
              headers,
              body: JSON.stringify({ handle, display_name: rawName }),
            });
            if (created.ok) {
              const newUser = await created.json();
              // Link the Discord account
              await fetch(`${base}/users/${newUser.id}/linked-accounts`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                  provider: 'discord',
                  provider_user_id: discordId,
                  username: token.name ?? undefined,
                  avatar_url: token.picture ?? undefined,
                }),
              });
              token.userId = newUser.id;
              token.handle = newUser.handle;
            }
          }
        } catch {
          // Non-fatal — user can still be signed in but won't have userId
        }
      }
      return token;
    },

    async session({ session, token }) {
      if (token.userId) session.user.id = token.userId as string;
      if (token.handle) session.user.handle = token.handle as string;
      return session;
    },
  },
};
