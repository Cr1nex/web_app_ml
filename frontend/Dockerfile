FROM node:20-alpine AS builder

ENV CI=true

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:1.27-alpine

RUN addgroup -g 10001 appgroup && \
    adduser -u 10001 -G appgroup -S -D appuser

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
