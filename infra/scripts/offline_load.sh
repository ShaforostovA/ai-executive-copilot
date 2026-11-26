#!/usr/bin/env bash
set -euo pipefail

VERSION=${1:?Usage: offline_load.sh 0.1.0-rc2}
cd /tmp
sha256sum -c "copilot-images-${VERSION}.tar.sha256"
sha256sum -c "copilot-release-${VERSION}.tar.gz.sha256"

install -m 755 -d /opt/copilot-staging/app /opt/copilot-staging/images
install -m 700 -d /etc/copilot-staging /var/backups/copilot-staging
tar -xzf "/tmp/copilot-release-${VERSION}.tar.gz" -C /opt/copilot-staging/app
install -m 644 "/tmp/copilot-images-${VERSION}.tar" "/opt/copilot-staging/images/copilot-images-${VERSION}.tar"
install -m 644 "/tmp/copilot-images-${VERSION}.tar.sha256" "/opt/copilot-staging/images/copilot-images-${VERSION}.tar.sha256"
docker load -i "/opt/copilot-staging/images/copilot-images-${VERSION}.tar"
docker image inspect --format '{{.RepoTags}} {{.Os}}/{{.Architecture}}' \
  "copilot-api:${VERSION}" \
  "copilot-frontend:${VERSION}" \
  postgres:17-alpine \
  caddy:2-alpine
printf 'Offline images and release files are ready: %s\n' "$VERSION"
