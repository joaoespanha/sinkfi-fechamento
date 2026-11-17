# Estágio 1: build da tela. O api.d.ts está no repositório, então não precisa do backend aqui.
FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Estágio 2: só os arquivos estáticos e o nginx, sem Node.
FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
