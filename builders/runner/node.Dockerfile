FROM node:22-bookworm-slim

ENV npm_config_audit=false \
    npm_config_fund=false \
    npm_config_update_notifier=false

WORKDIR /src
