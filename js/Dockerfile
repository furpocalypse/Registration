FROM node:20.1.0-alpine3.17 AS node
WORKDIR /build
# TODO: remove these when they are no longer submodules...
COPY interview/ interview/
COPY package.json package-lock.json ./
RUN npm ci
RUN cd interview/js && npm run -ws build
COPY .babelrc.json webpack.config.cjs ./
COPY src/ src/
# TODO: get from args?
COPY config.json ./
RUN npm run build


FROM nginx:1.24.0-alpine3.17-slim AS nginx
COPY --chown=root:nginx extra/nginx.conf /etc/nginx/nginx.conf
RUN chmod u=rw,g=r,o= /etc/nginx/nginx.conf \
    && mkdir /var/run/nginx \
    && chown nginx:nginx /var/run/nginx /var/cache/nginx
COPY --from=node /build/dist/ /usr/share/nginx/html/
USER nginx
EXPOSE 9000
