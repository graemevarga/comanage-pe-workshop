#!/bin/bash
# (Re)generate the workshop's self-signed localhost certificate in registry/tls/.
# RSA 2048, SHA-256, SAN localhost + 127.0.0.1, serverAuth, 825 days: the limits macOS and iOS
# require before they let you click through the warning. Demo only: the private key is public.
set -euo pipefail
dir="$(cd "$(dirname "$0")/.." && pwd)/registry/tls"
cfg=$(mktemp)
trap 'rm -f "${cfg}"' EXIT
printf '%s\n' '[req]' 'prompt = no' 'distinguished_name = dn' 'x509_extensions = v3' \
  '[dn]' 'CN = localhost' 'O = COmanage Registry workshop (demo only)' \
  '[v3]' 'subjectAltName = DNS:localhost, IP:127.0.0.1' 'extendedKeyUsage = serverAuth' \
  'keyUsage = critical, digitalSignature, keyEncipherment' 'basicConstraints = critical, CA:FALSE' \
  'subjectKeyIdentifier = hash' > "${cfg}"
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 825 -config "${cfg}" \
  -keyout "${dir}/privkey.pem" -out "${dir}/cert.pem" 2> /dev/null
chmod 0644 "${dir}/cert.pem" "${dir}/privkey.pem"
openssl x509 -in "${dir}/cert.pem" -noout -subject -enddate
