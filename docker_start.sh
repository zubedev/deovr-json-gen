#!/usr/bin/env bash

set -e

# generate the deovr json file once on startup then loop
python /deovr-json-gen/main.py /usr/share/nginx/html &

# start nginx
nginx -g 'daemon off;'
