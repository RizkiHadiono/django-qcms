#!/bin/sh
set -e

echo "Menunggu database siap..."
python - <<'PY'
import os
import time

import psycopg

url = os.environ.get("DATABASE_URL", "")
if url:
    for attempt in range(30):
        try:
            with psycopg.connect(url, connect_timeout=3) as conn:
                print("Database siap.")
                break
        except Exception as exc:  # noqa: BLE001
            print(f"Belum siap ({attempt + 1}/30): {exc}")
            time.sleep(2)
    else:
        raise SystemExit("Database tidak dapat dihubungi.")
PY

python manage.py migrate --noinput

if [ "$SEED_DEMO" = "1" ]; then
    python manage.py seed_demo --days "${SEED_DAYS:-30}" || true
fi

exec "$@"
