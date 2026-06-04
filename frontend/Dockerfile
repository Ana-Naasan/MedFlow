# MedFlow frontend (Next.js 16) image — multi-stage, uses Next "standalone" output.
# Built from the frontend/ context:
#   docker build -f frontend/Dockerfile -t umraa-frontend ./frontend
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* are baked into the client bundle at build time.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ARG NEXT_PUBLIC_API_TOKEN=
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_API_TOKEN=$NEXT_PUBLIC_API_TOKEN \
    NEXT_TELEMETRY_DISABLED=1 \
    # Placeholder so next-auth never throws during the build; the real secret
    # is injected at runtime by Cloud Run.
    AUTH_SECRET=build-time-placeholder
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=8080 \
    NEXT_TELEMETRY_DISABLED=1
# Next standalone server + assets only (small runtime image).
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 8080
# server.js (from output:'standalone') honors $PORT, which Cloud Run injects.
CMD ["node", "server.js"]
