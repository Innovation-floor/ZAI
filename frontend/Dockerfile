# =============================================================================
# ZAI Frontend — React + TypeScript
# Multi-stage: Node builds, nginx serves
# =============================================================================

# --- Build stage ---
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies first (cached unless package.json changes)
COPY package.json package-lock.json* ./
RUN npm install --no-audit

# Copy source and build
COPY . .
RUN npm run build

# --- Production stage ---
FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our config
COPY nginx.conf /etc/nginx/conf.d/zai.conf

# Copy built assets from build stage
# Vite automatically copies public/ into dist/ during build,
# so avatar.glb and avatar.svg are already included
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
