# Stage 1: Build React static assets
FROM node:20-alpine AS build

WORKDIR /workspace/frontend

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve static files with Nginx
FROM nginx:alpine

COPY --from=build /workspace/frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
