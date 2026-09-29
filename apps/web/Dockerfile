FROM node:22-alpine AS build
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web apps/web
COPY packages packages
RUN pnpm install --frozen-lockfile && pnpm --filter @satquery/web build
EXPOSE 3000
CMD ["pnpm", "--filter", "@satquery/web", "start"]
