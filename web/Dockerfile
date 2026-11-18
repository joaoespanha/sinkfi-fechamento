# Estágio 1: build da tela. O api.d.ts está no repositório, então não precisa do backend aqui.
FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Estágio 2: só os arquivos estáticos e o nginx, sem Node.
FROM nginx:1.28-alpine
# Template: na subida, vira /etc/nginx/conf.d/default.conf com as variáveis SINKFI_* trocadas.
# O filtro deixa $host, $uri e as outras variáveis do nginx em paz.
ENV NGINX_ENVSUBST_FILTER=^SINKFI_
# Sem proxy na frente (o compose explica quando mudar).
ENV SINKFI_PROXY_CONFIAVEL=127.0.0.1/32
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /web/dist /usr/share/nginx/html
