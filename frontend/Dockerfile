# Frontend (Next.js) image — multi-stage, uses Next "standalone" output.
# Built from the frontend/ context:
#   docker build -f frontend/Dockerfile -t umraa-frontend ./frontend
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Baked into the client bundle at build time — set to the deployed backend URL.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=8080
# Next standalone server + assets only (small runtime image).
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 8080
# server.js (from output:'standalone') honors $PORT, which Cloud Run injects.
CMD ["node", "server.js"]
