FROM node:24.22.2-alpine3.24@sha256:8a32c8cf649a49915a66e81e7a609223c708d0adabf288ee3f4077d765542f85 AS deps
WORKDIR /app
COPY apps/web/package.json /app/apps/web/package.json
COPY apps/web/package-lock.json /app/apps/web/package-lock.json
WORKDIR /app/apps/web
RUN npm ci --no-audit --no-fund

FROM node:24.22.2-alpine3.24@sha256:8a32c8cf649a49915a66e81e7a609223c708d0adabf288ee3f4077d765542f85 AS builder
WORKDIR /app
COPY --from=deps /app/apps/web/node_modules /app/apps/web/node_modules
COPY apps/web /app/apps/web
ARG NEXT_PUBLIC_API_BASE_URL=/api
ARG SERVER_API_BASE_URL=http://api:8000
ARG NEXT_PUBLIC_APP_VERSION=dev
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV SERVER_API_BASE_URL=${SERVER_API_BASE_URL}
ENV NEXT_PUBLIC_APP_VERSION=${NEXT_PUBLIC_APP_VERSION}
WORKDIR /app/apps/web
RUN npm run build

FROM node:24.22.2-alpine3.24@sha256:8a32c8cf649a49915a66e81e7a609223c708d0adabf288ee3f4077d765542f85 AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN rm -rf /usr/local/lib/node_modules/npm /opt/yarn-v* \
    /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/yarn /usr/local/bin/yarnpkg
COPY --from=builder /app/apps/web/.next /app/apps/web/.next
COPY --from=builder /app/apps/web/public /app/apps/web/public
COPY --from=builder /app/apps/web/package.json /app/apps/web/package.json
COPY --from=builder /app/apps/web/node_modules /app/apps/web/node_modules
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start", "-H", "0.0.0.0", "-p", "3000"]
