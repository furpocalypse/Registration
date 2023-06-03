FROM node:20.1.0-alpine3.17 AS node
RUN mkdir /build
WORKDIR /build
COPY interview/ interview/
COPY package.json package-lock.json ./
RUN npm ci
COPY .babelrc.json webpack.config.cjs ./
COPY src/ src/
# TODO: get from args?
COPY config.json ./
RUN npm run build

FROM nginx:1.24.0-alpine3.17-slim AS nginx
COPY extra/nginx-default.conf /etc/nginx/conf.d/default.conf
COPY --from=node /build/dist/ /usr/share/nginx/html/
