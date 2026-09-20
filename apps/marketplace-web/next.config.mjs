/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**' },
    ],
  },
  experimental: {
    // Enable server actions for form handling
    serverActions: { allowedOrigins: ['localhost:3001'] },
  },
};

export default nextConfig;
