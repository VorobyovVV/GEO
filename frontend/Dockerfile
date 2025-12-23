FROM node:20-alpine AS build
WORKDIR /app
# гарантируем установку dev-зависимостей (vite)
ENV NODE_ENV=development
COPY package*.json ./
RUN npm install --include=dev
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

