# Stage 1: build the Vite bundle. Pinned to Node 24 LTS (matches the lockfile's toolchain).
FROM node:24.18.0-alpine3.23 AS build
WORKDIR /app
# Manifests first so the install layer is cached across source edits.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
# Runs after the install; ui/.dockerignore keeps the host node_modules from overwriting it.
COPY . .
RUN npm run build

# Stage 2: serve the static build with nginx, proxying /api/ to the api service.
FROM nginx:1.30.3-alpine3.23
# conf.d (not templates/) so the stock default server is replaced and no envsubst runs.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
