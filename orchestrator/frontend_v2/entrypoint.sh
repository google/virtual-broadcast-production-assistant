#!/bin/sh

# Set a default for PORT if it's not set (for local testing).
PORT=${PORT:-8080}

# Substitute the PORT variable in the nginx config template.
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Start nginx in the foreground.
nginx -g 'daemon off;'
