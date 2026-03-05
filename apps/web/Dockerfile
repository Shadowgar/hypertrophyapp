FROM node:20-alpine AS deps
WORKDIR /app
COPY apps/web/package.json /app/apps/web/package.json
COPY apps/web/package-lock.json /app/apps/web/package-lock.json
WORKDIR /app/apps/web
RUN npm ci --no-audit --no-fund

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/apps/web/node_modules /app/apps/web/node_modules
COPY apps/web /app/apps/web
ARG NEXT_PUBLIC_API_BASE_URL=/api
ARG SERVER_API_BASE_URL=http://api:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV SERVER_API_BASE_URL=${SERVER_API_BASE_URL}
WORKDIR /app/apps/web
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/apps/web/.next /app/apps/web/.next
COPY --from=builder /app/apps/web/public /app/apps/web/public
COPY --from=builder /app/apps/web/package.json /app/apps/web/package.json
COPY --from=builder /app/apps/web/node_modules /app/apps/web/node_modules
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["npm", "run", "start"]
