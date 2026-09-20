# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — shared deps
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app

COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY apps/marketplace-mobile/package.json   ./apps/marketplace-mobile/
COPY packages/api-client/package.json       ./packages/api-client/
COPY packages/config/package.json           ./packages/config/
RUN pnpm install --frozen-lockfile

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — dev server (Metro bundler)
# Exposes Metro (8081) + Expo DevTools ports (19000-19002)
# Phones/emulators connect to this container over LAN or tunnel
# ─────────────────────────────────────────────────────────────────────────────
FROM deps AS dev
WORKDIR /app
COPY . .

ENV EXPO_PUBLIC_API_BASE_URL=${EXPO_PUBLIC_API_BASE_URL:-http://localhost:8000} \
    EXPO_NO_DOTENV=1

EXPOSE 8081 19000 19001 19002

WORKDIR /app/apps/marketplace-mobile
CMD ["pnpm", "start", "--", "--host", "lan", "--port", "8081"]

# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — Android build
# Produces a release .apk / .aab artefact at /output
# Based on the official React Native Android image (JDK 17 + Android SDK)
# ─────────────────────────────────────────────────────────────────────────────
FROM reactnativecommunity/react-native-android:latest AS android-builder

RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app

COPY --from=deps /app/node_modules              ./node_modules
COPY --from=deps /app/apps/marketplace-mobile/node_modules \
                                                ./apps/marketplace-mobile/node_modules
COPY . .

ARG EXPO_PUBLIC_API_BASE_URL=https://api.thetextilecare.com
ENV EXPO_PUBLIC_API_BASE_URL=$EXPO_PUBLIC_API_BASE_URL \
    GRADLE_OPTS="-Dorg.gradle.daemon=false -Dorg.gradle.parallel=false"

WORKDIR /app/apps/marketplace-mobile

# Install EAS CLI then run a local Android build
RUN npm install -g eas-cli@latest && \
    npx expo prebuild --platform android --clean && \
    cd android && ./gradlew assembleRelease --no-daemon

# Copy the APK to /output so it can be extracted via docker cp
RUN mkdir -p /output && \
    find /app/apps/marketplace-mobile/android/app/build/outputs/apk/release \
         -name "*.apk" -exec cp {} /output/marketplace-mobile.apk \;

CMD ["echo", "Build complete. Copy /output/marketplace-mobile.apk"]
