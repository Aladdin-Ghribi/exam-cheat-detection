FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY --from=build /app/public/_redirects /usr/share/nginx/html/_redirects
COPY --from=build /app/public/.htaccess /usr/share/nginx/html/.htaccess

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]