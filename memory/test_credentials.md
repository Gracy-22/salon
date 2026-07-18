# Test Credentials

## Owner — WhatsApp OTP (primary)
- Route: /owner
- Phone: 8511111593 (country: India +91)
- OTP: Use `POST /api/login/request-otp` with `{"phone": "8511111593"}` — response includes `mock_otp` for testing.
- After verify, sessionStorage key `owner_token` holds the JWT.

## Owner — PIN (backend fallback only, hidden from UI)
- API: `POST /api/owner/login` with `{"pin": "9999"}`
- PIN: 9999

## Customer — WhatsApp OTP
- Route: /login (unified) or /manage (self-serve)
- Any phone with bookings can sign in via OTP; `mock_otp` is returned in the API response.
- Example phone in seed data: 9876543210

## Stylist — WhatsApp OTP (after Staff Management onboarding) / PIN fallback
- Stylist must have `login_phone` set via Owner > Staff & Treatments before OTP login resolves to stylist role.
- Legacy PINs (still valid via direct API):
  - Elena Hart: 1234
  - Sarah Lin: 2345
  - Michael Voss: 3456
