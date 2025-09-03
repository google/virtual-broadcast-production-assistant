#!/bin/sh

# Substitute environment variables in the nginx configuration
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Find all JavaScript files in the dist directory and its subdirectories
find /usr/share/nginx/html -type f -name "*.js" -print0 | while IFS= read -r -d '\0' file
do
  # Use sed to replace the placeholder with the environment variable value
  sed -i "s|__VITE_WEBSOCKET_URL__|${VITE_WEBSOCKET_URL}|g" "$file"
  echo "Processed $file"
done

# Start nginx
nginx -g 'daemon off;'
