# Stage 1: build Vue 3 frontend
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --prefer-offline
COPY frontend/ ./

# Vite bakes these as static strings into the bundle.
# VITE_BASE_URL: path prefix the app is served under (/ for dev, /linnet for cloud)
# VITE_API_BASE: prefix for all /session/* fetch calls (empty for direct, /linnet for cloud)
ARG VITE_BASE_URL=/
ARG VITE_API_BASE=
ENV VITE_BASE_URL=$VITE_BASE_URL
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build

# Stage 2: serve via nginx
FROM nginx:alpine
COPY docker/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
