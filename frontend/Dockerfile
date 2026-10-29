# Multi-stage Dockerfile for AgriDirect Frontend

# Stage 1: Build the static bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency definitions
COPY package*.json ./

# Install dependencies cleanly
RUN npm ci

# Copy application source
COPY . .

# Run production build
RUN npm run build

# Stage 2: Serve static assets with lightweight Nginx
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose standard web port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
