FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@latest --activate

# ── deps ──────────────────────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY apps/marketplace-web/package.json ./apps/marketplace-web/
COPY packages/ui/package.json           ./packages/ui/
COPY packages/types/package.json        ./packages/types/
COPY packages/config/package.json       ./packages/config/
COPY packages/auth/package.json         ./packages/auth/
COPY packages/tenant/package.json       ./packages/tenant/
COPY packages/api-client/package.json   ./packages/api-client/
RUN pnpm install --frozen-lockfile

# ── builder ───────────────────────────────────────────────────────────────────
FROM deps AS builder
WORKDIR /app
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN pnpm --filter @ttc/marketplace-web build

# ── runner ────────────────────────────────────────────────────────────────────
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

COPY --from=builder /app/apps/marketplace-web/public          ./public
COPY --from=builder --chown=nextjs:nodejs \
     /app/apps/marketplace-web/.next/standalone               ./
COPY --from=builder --chown=nextjs:nodejs \
     /app/apps/marketplace-web/.next/static                   ./.next/static

USER nextjs
EXPOSE 3001
ENV PORT=3001 HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
