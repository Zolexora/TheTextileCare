# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — JS deps
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
# Stage 2 — Dev server (Metro bundler)
# Connect phones/emulators via Expo Go → exp://<host-ip>:8081
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
# Stage 3 — Android base (shared by APK + AAB stages)
# Runs expo prebuild and installs Gradle dependencies once
# ─────────────────────────────────────────────────────────────────────────────
FROM reactnativecommunity/react-native-android:latest AS android-base
RUN corepack enable && corepack prepare pnpm@latest --activate && \
    npm install -g eas-cli@latest
WORKDIR /app
COPY --from=deps /app/node_modules              ./node_modules
COPY --from=deps /app/apps/marketplace-mobile/node_modules \
                                                ./apps/marketplace-mobile/node_modules
COPY . .
ARG EXPO_PUBLIC_API_BASE_URL=https://api.thetextilecare.com
ENV EXPO_PUBLIC_API_BASE_URL=$EXPO_PUBLIC_API_BASE_URL \
    GRADLE_OPTS="-Dorg.gradle.daemon=false -Dorg.gradle.parallel=false"
WORKDIR /app/apps/marketplace-mobile
# Prebuild generates the native android/ folder
RUN npx expo prebuild --platform android --clean
# Pre-download Gradle wrapper so both APK and AAB stages hit cache
RUN cd android && ./gradlew --version

# ─────────────────────────────────────────────────────────────────────────────
# Stage 4a — APK build (direct install / testing)
# Output: /output/marketplace-mobile-release.apk
# ─────────────────────────────────────────────────────────────────────────────
FROM android-base AS android-apk
RUN cd android && ./gradlew assembleRelease --no-daemon
RUN mkdir -p /output && \
    find android/app/build/outputs/apk/release -name "*.apk" \
         -exec cp {} /output/marketplace-mobile-release.apk \;
CMD ["echo", "APK ready at /output/marketplace-mobile-release.apk"]

# ─────────────────────────────────────────────────────────────────────────────
# Stage 4b — AAB build (Google Play Store submission)
# Output: /output/marketplace-mobile-release.aab
# ─────────────────────────────────────────────────────────────────────────────
FROM android-base AS android-aab
RUN cd android && ./gradlew bundleRelease --no-daemon
RUN mkdir -p /output && \
    find android/app/build/outputs/bundle/release -name "*.aab" \
         -exec cp {} /output/marketplace-mobile-release.aab \;
CMD ["echo", "AAB ready at /output/marketplace-mobile-release.aab"]
