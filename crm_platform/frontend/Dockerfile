# Step 1: Build the app
FROM node:20-alpine as build
WORKDIR /app

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./
# Use 'install' to make sure all devDependencies (like vite) are included
RUN npm install 

COPY . .
# Use npx to bypass the package.json "tsc" script
RUN npx vite build

# Step 2: Serve the app with Nginx
FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
