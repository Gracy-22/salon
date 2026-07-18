# Owner Auth Testing Notes

This app uses a simple owner PIN flow, not full email/password accounts.

## Expected behavior
- `POST /api/owner/login` with owner PIN `9999` returns a signed bearer token.
- The returned token is stored by the frontend in `sessionStorage.owner_token`.
- All `/api/owner/*` routes except `/api/owner/login` require `Authorization: Bearer <token>`.
- Missing, invalid, or expired owner tokens return `401`.

## Quick checks
```bash
BASE=$(grep '^REACT_APP_BACKEND_URL=' /app/frontend/.env | cut -d= -f2-)
curl -i "$BASE/api/owner/bookings?date=2026-06-28"
TOKEN=$(curl -sS -X POST "$BASE/api/owner/login" -H 'Content-Type: application/json' -d '{"pin":"9999"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')
curl -i "$BASE/api/owner/revenue-insights?days=30" -H "Authorization: Bearer $TOKEN"
```

## Regression file
Run:
```bash
pytest -q /app/backend/tests/test_owner_dashboard_p0.py
```