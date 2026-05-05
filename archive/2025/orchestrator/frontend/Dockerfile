# This Dockerfile assumes the application has already been built
# and the resulting static assets are in the `dist` directory.
FROM nginx:1.25-alpine

# Install gettext for envsubst
RUN apk add --no-cache gettext

# Copy the pre-built assets from the `dist` directory into the Nginx public folder.
# The `dist` directory is created by the `npm run build` step in cloud-build.yaml.
COPY dist /usr/share/nginx/html

# Copy the nginx configuration template and entrypoint script
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run the entrypoint script when the container starts
CMD ["/entrypoint.sh"]
