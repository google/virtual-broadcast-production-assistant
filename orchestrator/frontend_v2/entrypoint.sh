#!/bin/sh

# Substitute environment variables in the nginx configuration
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Replace the placeholder in the config.json file
sed -i "s|__VITE_WEBSOCKET_URL__|${VITE_WEBSOCKET_URL}|g" /usr/share/nginx/html/config.json

# Start nginx
nginx -g 'daemon off;'