#!/usr/bin/env bash
# Read-only Ubuntu VPS diagnostics. Does not install packages or change configuration.
set -u

section() {
  printf '\n== %s ==\n' "$1"
}

run() {
  printf '\n$ %s\n' "$*"
  "$@" 2>&1 || true
}

printf 'AI Executive Co-pilot VPS diagnostics (read-only)\n'
printf 'Do not publish raw output: it can contain hostnames, IPs and service details.\n'
date -u '+UTC %Y-%m-%dT%H:%M:%SZ'

section 'Ubuntu and architecture'
run cat /etc/os-release
run uname -m
run hostnamectl

section 'CPU, RAM and swap'
run nproc
run lscpu
run free -h
run swapon --show

section 'Disk and Docker storage'
run df -h /
run df -h /opt
if [ -d /var/lib/docker ]; then
  run df -h /var/lib/docker
fi

section 'Ports 22, 80 and 443'
run ss -ltn
run ss -ltnp

section 'Firewall'
if command -v ufw >/dev/null 2>&1; then
  run ufw status verbose
fi
if command -v firewall-cmd >/dev/null 2>&1; then
  run firewall-cmd --state
  run firewall-cmd --list-all
fi
if command -v nft >/dev/null 2>&1; then
  run nft list ruleset
fi

section 'Docker, containerd, Nginx and Caddy'
run docker --version
run docker compose version
run docker info --format 'ServerVersion={{.ServerVersion}} Driver={{.Driver}}'
run docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
run systemctl is-active docker
run systemctl is-active containerd
run systemctl is-active nginx
run systemctl is-active caddy
run dpkg-query -W -f='${Package} ${Version} ${Status}\n' docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin nginx caddy

section 'Network and DNS'
run getent ahosts download.docker.com
run getent ahosts github.com
run curl -I --max-time 15 https://download.docker.com
run curl -I --max-time 15 https://github.com
if [ -n "${DOMAIN:-}" ]; then
  run getent ahosts "$DOMAIN"
else
  printf 'DOMAIN is not set; skipping application DNS lookup.\n'
fi

section 'Result'
printf 'Diagnostics completed without configuration changes.\n'
printf 'Review memory, free disk, port conflicts, firewall, existing services and DNS before install.\n'
