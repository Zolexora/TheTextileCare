FROM node:20-alpine AS deps
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY apps/driver-mobile/package.json  ./apps/driver-mobile/
COPY packages/api-client/package.json ./packages/api-client/
COPY packages/config/package.json     ./packages/config/
RUN pnpm install --frozen-lockfile

FROM deps AS dev
WORKDIR /app
COPY . .
ENV EXPO_PUBLIC_API_BASE_URL=${EXPO_PUBLIC_API_BASE_URL:-http://localhost:8000} \
    EXPO_NO_DOTENV=1
EXPOSE 8083 19000 19001 19002
WORKDIR /app/apps/driver-mobile
CMD ["pnpm", "start", "--", "--host", "lan", "--port", "8083"]

FROM reactnativecommunity/react-native-android:latest AS android-base
RUN corepack enable && corepack prepare pnpm@latest --activate && \
    npm install -g eas-cli@latest
WORKDIR /app
COPY --from=deps /app/node_modules             ./node_modules
COPY --from=deps /app/apps/driver-mobile/node_modules \
                                               ./apps/driver-mobile/node_modules
COPY . .
ARG EXPO_PUBLIC_API_BASE_URL=https://api.thetextilecare.com
ENV EXPO_PUBLIC_API_BASE_URL=$EXPO_PUBLIC_API_BASE_URL \
    GRADLE_OPTS="-Dorg.gradle.daemon=false -Dorg.gradle.parallel=false"
WORKDIR /app/apps/driver-mobile
RUN npx expo prebuild --platform android --clean
RUN cd android && ./gradlew --version

FROM android-base AS android-apk
RUN cd android && ./gradlew assembleRelease --no-daemon
RUN mkdir -p /output && \
    find android/app/build/outputs/apk/release -name "*.apk" \
         -exec cp {} /output/driver-mobile-release.apk \;
CMD ["echo", "APK ready at /output/driver-mobile-release.apk"]

FROM android-base AS android-aab
RUN cd android && ./gradlew bundleRelease --no-daemon
RUN mkdir -p /output && \
    find android/app/build/outputs/bundle/release -name "*.aab" \
         -exec cp {} /output/driver-mobile-release.aab \;
CMD ["echo", "AAB ready at /output/driver-mobile-release.aab"]
