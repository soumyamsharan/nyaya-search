#!/usr/bin/env bash
# One-time hardening of a fresh Ubuntu Arm64 server (Oracle A1 or Hetzner). Run as the default sudo user:
#   scp scripts/server-setup.sh scripts/lib.sh ubuntu@<ip>:~ && ssh ubuntu@<ip> 'sudo bash server-setup.sh'
# Requires that you can already log in with an SSH key (password login is switched off here).
source "$(dirname "$0")/lib.sh"
[[ $EUID -eq 0 ]] || die "run with sudo"
[[ -s /home/${SUDO_USER:-ubuntu}/.ssh/authorized_keys ]] || die "no SSH key installed for ${SUDO_USER:-ubuntu}; refusing to disable passwords"

log "updating packages and enabling unattended security upgrades"
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
DEBIAN_FRONTEND=noninteractive apt-get install -y unattended-upgrades iptables-persistent ca-certificates curl
dpkg-reconfigure -f noninteractive unattended-upgrades

log "SSH: keys only, no root login"
cat >/etc/ssh/sshd_config.d/90-nyaya.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
systemctl reload ssh || systemctl reload sshd

log "host firewall: allow 22, 80, 443 only (the OCI security list must allow the same)"
for port in 80 443; do
  iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null || iptables -I INPUT 5 -p tcp --dport "$port" -j ACCEPT
done
iptables -C INPUT -p udp --dport 443 -j ACCEPT 2>/dev/null || iptables -I INPUT 5 -p udp --dport 443 -j ACCEPT
netfilter-persistent save

log "installing Docker Engine from Docker's apt repository"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  >/etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker "${SUDO_USER:-ubuntu}"

log "done. Log out and back in so the docker group applies."
