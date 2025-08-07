# Stage 1: Build the frontend assets
FROM node:20-alpine as builder
WORKDIR /app
# Copy package.json and package-lock.json
COPY package*.json ./
# Install dependencies
RUN npm install
# Copy the rest of the application source code
COPY . .
# Build the application (assumes output is in /app/dist)
RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:1.25-alpine
# Install gettext for envsubst
RUN apk add --no-cache gettext
# Copy the built assets from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html
# Copy the nginx configuration template and entrypoint script
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run the entrypoint script when the container starts
CMD ["/entrypoint.sh"]
