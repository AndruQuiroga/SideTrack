/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'i.scdn.co',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'coverartarchive.org',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'lastfm.freetls.fastly.net',
        pathname: '/**',
      },
    ],
  },
};

export default nextConfig;
