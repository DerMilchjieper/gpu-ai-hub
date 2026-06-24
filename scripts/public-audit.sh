#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
failed=0
if rg -n --hidden --glob '!.git/**' --glob '!scripts/public-audit.sh' '192\.168\.2\.41|/home/wizzard|C:\\Users\\|/Users/[^/]+/' .; then
  echo "Machine-specific path or address found." >&2; failed=1
fi
if rg -n --hidden --glob '!.git/**' --glob '!scripts/public-audit.sh' 'BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|github_pat_[A-Za-z0-9_]+|gh[opsu]_[A-Za-z0-9]+' .; then
  echo "Potential credential found." >&2; failed=1
fi
for file in $(git ls-files); do
  [ -f "$file" ] || continue
  size=$(wc -c < "$file")
  if [ "$size" -gt 52428800 ]; then echo "Tracked file exceeds 50 MiB: $file" >&2; failed=1; fi
done
[ "$failed" -eq 0 ]
echo "Public repository audit passed."
