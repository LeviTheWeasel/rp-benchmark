FROM node:22-alpine AS base

FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --production=false

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
RUN mkdir -p /app/data && chown nextjs:nodejs /app/data
# Persistence is provided by a Railway volume mounted at /app/data.
# The VOLUME keyword is intentionally omitted — Railway disallows it and
# relies on its own volume config instead. See:
# https://docs.railway.com/reference/volumes
#
# Run as root: the Railway volume is mounted owned by root at runtime,
# which prevents the non-root `nextjs` user from writing to /app/data.
# The attack surface is small (Next.js server with JSON endpoints, no
# shell exposure) and the container is sandboxed by Railway. If we ever
# need privilege separation back, switch to an entrypoint script that
# chowns the mount as root and drops to `nextjs` via su-exec.
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
