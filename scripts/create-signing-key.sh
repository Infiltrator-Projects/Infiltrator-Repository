#!/usr/bin/env bash
set -euo pipefail

OUTDIR="${1:-$PWD/infiltrator-apt-signing-key}"
if [[ -e "$OUTDIR" ]]; then
  echo "Refusing to overwrite existing path: $OUTDIR" >&2
  exit 1
fi

mkdir -m 700 -p "$OUTDIR/gnupg"
export GNUPGHOME="$OUTDIR/gnupg"

cat >"$OUTDIR/key-params" <<'EOF'
Key-Type: RSA
Key-Length: 3072
Key-Usage: sign
Name-Real: Infiltrator APT Repository
Name-Email: repository-signing@the-first-infiltrator.invalid
Expire-Date: 2y
%no-protection
%commit
EOF

gpg --batch --generate-key "$OUTDIR/key-params"
FINGERPRINT="$(gpg --batch --with-colons --list-secret-keys | awk -F: '/^fpr:/ {print $10; exit}')"
if [[ -z "$FINGERPRINT" ]]; then
  echo "Unable to determine generated signing-key fingerprint" >&2
  exit 1
fi

printf '%s\n' "$FINGERPRINT" >"$OUTDIR/APT_SIGNING_KEY_FINGERPRINT.txt"
gpg --batch --export-secret-keys "$FINGERPRINT" | base64 -w0 >"$OUTDIR/APT_SIGNING_KEY_B64.txt"
printf '\n' >>"$OUTDIR/APT_SIGNING_KEY_B64.txt"
gpg --batch --armor --export "$FINGERPRINT" >"$OUTDIR/repository-key.asc"
rm -f "$OUTDIR/key-params"

cat <<EOF
Created a dedicated Infiltrator APT signing key.

Fingerprint:
$FINGERPRINT

GitHub Actions secrets to create in Infiltrator-Repository:
  APT_SIGNING_KEY_FINGERPRINT = contents of:
    $OUTDIR/APT_SIGNING_KEY_FINGERPRINT.txt

  APT_SIGNING_KEY_B64 = contents of:
    $OUTDIR/APT_SIGNING_KEY_B64.txt

Keep this entire directory private and backed up securely.
Do not commit it to Git.
EOF
