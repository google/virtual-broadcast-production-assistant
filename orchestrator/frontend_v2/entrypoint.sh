#!/bin/sh

# Substitute environment variables in the nginx configuration
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Source the appropriate .env file based on APP_ENV
if [ -f ".env.${APP_ENV}" ]; then
  echo "Sourcing .env.${APP_ENV}"
  export $(grep -v '^#' ".env.${APP_ENV}" | xargs)
else
  echo "Warning: .env.${APP_ENV} not found. Using default environment variables."
fi

# Replace the placeholder in the static files
find /usr/share/nginx/html -type f -name "*.js" -print0 | while IFS= read -r -d '\0' file
do
  sed -i "s|__VITE_WEBSOCKET_URL__|${VITE_WEBSOCKET_URL}|g" "$file"
done

# Start nginx
nginx -g 'daemon off;'