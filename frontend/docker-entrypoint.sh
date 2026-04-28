#!/bin/sh
set -e

# Substitute environment variables in config files
envsubst '${VITE_API_BACKEND_URL}' < /usr/share/nginx/html/config.js.template > /usr/share/nginx/html/config.js
envsubst '${VITE_API_BACKEND_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Start nginx
exec nginx -g "daemon off;"
