# Salon Booking App — PRD

## Original Problem Statement
Salon Booking App divided into 3 phases.
- Phase 1: Customer booking page — service, stylist, date/time picker, booking confirmation.
- Phase 2: Stylist availability toggle — stylist login, weekly calendar, mark availability/blocks; stylist daily schedule view with chronological appointments and status updates.
- Phase 3: Owner dashboard, customer lookup/reschedule, scheduled WhatsApp reminders.

Product requirements: elegant minimal design, fast/simple customer flow without login, WhatsApp confirmation messages.

## User Choices / Constraints
- Customer booking must remain public with no customer login.
- All frontend time displays use 12-hour format, e.g. `9:00 AM`; backend stores `HH:MM`.
- All pricing displays use INR `₹`.
- Design language: elegant minimal salon aesthetic using Cormorant Garamond + Outfit, off-white #FAF9F6, charcoal/stones, thin borders.
- Stylists and owner use simple PIN sign-in, not complex account management.
- WhatsApp is powered by Twilio using environment-provided credentials/templates.

## Architecture
- **Backend**: FastAPI + MongoDB (Motor). All routes live under `/api` in `/app/backend/server.py`.
- **Frontend**: React + Tailwind + shadcn/ui components in `/app/frontend/src`.
- **Database**: MongoDB from `MONGO_URL` and `DB_NAME` env keys.
- **Scheduling**: APScheduler sends WhatsApp reminders at configured offsets.
- **Auth**: Stylist PIN flow; owner PIN flow returns signed bearer token. Owner APIs require `Authorization: Bearer <token>`.
- **Twilio**: WhatsApp confirmation/reminder/no-show follow-up is best-effort and records status metadata where relevant.

## Key Data Models
- `services`: `{id, name, category, duration_min, price, description, icon}`
- `stylists`: `{id, name, title, bio, photo, services, pin, working_hours}`
- `bookings`: `{id, service_id, stylist_id, date, start_time, end_time, duration_min, customer_name, customer_phone, status, reminders_sent, whatsapp_*}`
- `stylist_blocks`: `{id, stylist_id, date, start_time, end_time, status}`

## Implemented Features

### Phase 1 — Customer Booking
- Public 4-step booking flow: Service → Stylist → Date & Time → Details → Confirmation.
- Availability endpoint with working-hours and overlap checks.
- Grouped Morning/Afternoon/Evening time slots in 12-hour format.
- Booking confirmation with reference number and INR pricing.

### Phase 2 — Stylist Portal
- Stylist PIN login.
- Daily roster with chronological appointments and status updates: upcoming, done, no-show, cancelled.
- Weekly availability grid with busy/leave blocks.
- Working-hours editor per stylist.
- Selectable stylist day view with previous/today/next controls.
- Daily booking cards show full booking context: customer, phone, service, duration, time, notes, status, reference, price, and WhatsApp status.
- Weekly availability now supports one-time breaks and recurring weekly lunch/break blocks.
- Weekly calendar displays long bookings as single vertical duration-spanning blocks, with click-to-open booking detail modal.

### Phase 3 — Owner + Customer Operations
- Owner PIN login and protected owner dashboard APIs.
- Owner daily bookings view with cancel/done/no-show actions.
- Owner summary and 7-day revenue trend.
- Customer lookup by phone/reference, self-cancel, and reschedule endpoints.
- Twilio WhatsApp booking confirmations, reminders, inbound confirm/cancel handling.

### P0 Completed — 2026-06-28
- Owner **No-shows** tab with monthly no-show report, log, no-show rate, and repeat no-show flag at 3+ lifetime no-shows.
- No-show follow-up WhatsApp message when a booking is marked no-show and WhatsApp opt-in is enabled.
- Owner **Insights** tab with today/week/month revenue, average booking value, revenue per stylist, revenue per service, status counts, and revenue-by-weekday bar chart.
- Owner API protection added: `/api/owner/*` routes now reject missing/invalid bearer tokens; `/api/owner/login` remains public.

## Current Test Status
- Backend lint: passed.
- Frontend lint for owner dashboard: passed.
- API self-tests: protected owner endpoint returns 401 unauthenticated; signed owner token can access insights.
- Browser smoke test: owner login, No-shows tab, and Insights tab render successfully.
- Testing agent regression: owner P0 features passed functionally; critical auth issue found and fixed.
- Local regression file after fix: `/app/backend/tests/test_owner_dashboard_p0.py` — 8/8 passed.
- Testing agent iteration 9: passed owner auth regression and P0 owner flows; added stable booking calendar date test IDs afterward.
- Booking calendar smoke test: stable `date-day-YYYY-MM-DD` selector verified.
- Bug fix — 2026-06-28: Owner dashboard no-show navigation made prominent after user could not see the tab. Replaced subtle text tab with a large visible `No show tracker` tab card. Testing agent iteration 10 verified the tab is visibly present and prominent.
- Feature addition — 2026-06-28: Stylist day/weekly scheduling improvements completed. Testing agent iteration 11 verified day navigation, detailed booking cards, one-time breaks, recurring breaks, long booking vertical spans, weekly booking detail modal, and regressions.
- Feature addition — 2026-06-30: Owner "Staff & Treatments" management UI shipped. Owner sidebar gained a new tab where treatments (services) and staff (stylists) can be added, edited, and archived. Treatments support name/category/duration/price/icon/description/active. Staff support name/title/mobile/login_phone/bio/active + multi-select treatment assignment. Archive-only — never hard delete — so booking history stays intact. Public booking flow and stylist assignments filter out archived items. Backend tests: 9/9. Frontend tests (iteration_12): 11/11.
- Bug fix — 2026-06-30: Unified OTP login now correctly routes stylists to `/stylist/portal`. UnifiedLogin previously stored `sessionStorage.stylist` while StylistPortal expected `stylist_id`/`stylist_name`, bouncing OTP-logged-in stylists back to the login page. Also added active-stylist filter and `pin` field exclusion in the backend `/api/login/verify-otp` lookup.
- Bug fix — 2026-06-30: `/api/owner/bookings` endpoint accidentally had its `@api_router.get` decorator detached from its handler (it was decorating `_slug_id` instead due to blank lines), causing two non-blocking 422 console errors on every owner dashboard boot and a "Could not load" toast. Restored the decorator on the correct function.
- Refactor — 2026-06-30: `OwnerDashboard.jsx` slimmed from ~770 → 153 lines. Inner managers extracted into `/app/frontend/src/pages/owner/`: `utils.js` (constants + helpers), `ui.jsx` (ProfileStat / ProfileInput / MetricCard / RankedList / RevenuePieChart), `OwnerSideMenu.jsx`, `DailyBook.jsx` (+RevenueTrend), `NoShowTracker.jsx`, `InsightsDashboard.jsx`, `OwnerCustomerDirectory.jsx` (+OwnerCustomerProfilePanel), `StaffTreatmentsManager.jsx` (+TreatmentManager / StylistManager / MultiServicePicker / StylistAvatar / StylistPhotoPicker). Each sub-file <260 lines.
- Feature — 2026-06-30: Stylist photo upload added to Staff & Treatments form. File upload (≤1 MB, image only, base64 data-URL) or paste-URL mode, with 128px preview and Remove. Existing seeded stylists' photos render as small avatars in the stylist list rows; new staff without a photo fall back to initials. Frontend tests (iteration_13): 12/12 passed.
- Feature — 2026-06-30: Stylist photos moved off MongoDB to Emergent object storage. New backend endpoints `POST /api/owner/uploads/image` (owner auth, multipart, 2 MB cap, JPEG/PNG/WebP/GIF) and `GET /api/files/{path}` (public, cached 24h, returns 404 for missing/invalid prefix). Stylist photo picker now uploads the file and stores the public URL on `stylists.photo` instead of a base64 data URL. `/api/stylists` payload dropped to ~3.5 KB (verified by tests).
- Feature — 2026-06-30: Booking flow stylist selection step now gracefully handles stylists with no photo by rendering a tasteful large-initials fallback inside the existing 3:4 hero card, preserving layout consistency. Stylists with photos continue to use their hero image.

- Feature — 2026-06-30 (Phase 1/4 of multi-location): Salons are now a first-class entity. New `salons` collection with default "Maison Aurelle — Main" seeded; all existing stylists and bookings back-filled to that salon. New backend CRUD: `GET /api/salons` (public), `GET/POST/PATCH /api/owner/salons`, `POST /api/owner/salons/{id}/archive` (default salon protected). `salon_id` added to Stylist and Booking models; booking creation derives `salon_id` from the chosen stylist. Owner endpoints (`/api/owner/bookings`, `/owner/summary`, `/owner/revenue-trend`, `/owner/no-shows`, `/owner/revenue-insights`, `/owner/stylists`) accept optional `?salon_id=` filter. Stylist create/update validate `salon_id` exists. Public `/api/stylists` accepts `?salon_id=` filter for Phase 4 booking flow. Owner dashboard gained a header **salon switcher** ("All salons" default + each active salon) that filters Daily Book / Insights / No-Show / Staff. New **Salons** sidebar tab (CRUD + archive). Stylist form has a required Salon selector. Default salon cannot be archived.
## Test Credentials
See `/app/memory/test_credentials.md`.
- Feature — 2026-07-01 (Phase 2/4 of multi-location): Per-salon service menu. New `salon_services` collection stores per-(salon, service) overrides `{is_offered, price_override}`. Default semantics = "all services offered at base price unless explicitly toggled off." New endpoints: `GET /api/owner/salons/{salon_id}/menu` (master services + overrides joined + effective_price), `PUT /api/owner/salons/{salon_id}/menu` (bulk upsert entries[]). Public `GET /api/services?salon_id=X` now filters out off-services and applies override prices. Booking creation validates the service is offered at the stylist's salon (400 with 'This service is not offered at that salon location') and applies the salon's price_override to the booking's charged amount. New frontend `SalonMenuManager` card in Staff & Treatments tab (spans full width on 2xl): salon dropdown, per-service checkbox + price-override input, dirty-tracking Save Menu button. Verified end-to-end via curl.
- Feature — 2026-07-01 (Phase 3/4 of multi-location): **Manager role** landed. New `managers` collection `{id, name, phone, login_phone, salon_id, is_active}`. Backend endpoints: owner CRUD `GET/POST/PATCH /api/owner/managers` + archive; manager-scoped `/api/manager/me`, `/manager/bookings`, `/manager/revenue-trend`, `/manager/revenue-insights`, `/manager/no-shows`, `/manager/customers/search`, `/manager/customers/{phone}`, `/manager/bookings/{id}/status`, `/manager/bookings/{id}/cancel` — every read/write is auto-filtered to the manager's `salon_id`. Unified OTP login (`/api/login/verify-otp`) now checks the managers collection between owner and stylist and returns `{role:'manager', token, manager, salon}`. Auth hardening: reject `login_phone` == owner phone, reject duplicates against active managers AND active stylists. Extracted `_no_show_report` and `_revenue_insights_from_bookings` as shared helpers so owner and manager endpoints share the exact same reporting logic.
- Feature — 2026-07-01: New **Manager Dashboard** at `/manager/dashboard` with 4 tabs (Daily Book, Customer Tracker, No Show Tracker, Insights) — every panel scoped to the manager's salon, no Salons/Staff/Menu tabs, no salon switcher (visually clarifies the smaller privilege scope). `UnifiedLogin` routes `role=manager` phones there; `sessionStorage.manager_token` is the auth key. Owner gains a new **Managers** sub-section inside the Salons tab (add/edit/archive with salon dropdown, phone conflict warnings surfaced from the API).
- Feature — 2026-07-01 (Phase 4/4 · **multi-location series complete**): Customer booking flow reworked to a 4-step location-aware experience.
  - **Backend**: new endpoints `GET /api/salons?service_id=X` (filters to salons that actually offer the service), `GET /api/availability/salon-slots?salon_id&service_id&date` (union of available time slots across all stylists at a salon), `GET /api/availability/by-slot?salon_id&service_id&date&start_time` (list of stylists free at a given slot). Extracted `_compute_stylist_slots` helper so per-stylist availability, salon-slot union, and slot-first stylist filter all share the same source of truth.
  - **Frontend `BookingFlow`**: step order **Service → Location → Stylist → Date & Time** (default `stylist_first` mode). Location step has a mode toggle "Pick stylist first" (default) vs "Pick slot first"; slot-first flips step order to **Service → Location → Date & Time → Stylist**, showing only stylists free at the chosen slot. Header replaces the hard-coded "IST +5:30" line with a salon-aware label (e.g., "MAISON AURELLE — MAIN · ASIA/KOLKATA") once the customer picks a location. Stepper labels dynamically switch with the mode. Downstream state resets (salon, stylist, slot, date) fire correctly when upstream selections change to prevent stale bookings.
  - New Lucide `MapPin` icon for salon cards; new `LocationStep` component; `StylistStep` accepts `slotFirstContext` prop that shows "Stylists free at HH:MM on 4 Jul at Bandra Book" hint and an empty-state message when no stylists are free at the chosen slot; `DateTimeStep` accepts `salon`+`slotFirst` props to switch its subtitle.
  - Booking POST unchanged — the backend still derives `salon_id` from the selected stylist (Phase 1), applies per-salon price override (Phase 2), and enforces menu compliance (Phase 2). Booking works in both modes.

- Feature — 2026-07-01: **Animated 6-box OTP input** replaces the single OTP field on `/login`. New reusable component `frontend/src/components/OtpBoxes.jsx` with per-cell entrance micro-animations (pop / slide / flip / blur / rotate / swing), active-cell lift + growing underline + blinking serif caret, completion wave, and horizontal shake + red-tinting on invalid OTP. Auto-advance, backspace navigation, arrow keys, and paste-fill supported. Auto-submits on 6th digit.

- Feature — 2026-07-03: **Landing page (`LandingPage.jsx`) redesigned** in a cinematic luxury-spa aesthetic inspired by `ever.co.id`. Structured per `design_guidelines.json` (theme archetype 5-Luxury, hybrid light/dark alternating sections). Sections: transparent-to-solid sticky nav, full-viewport hero with `Your beauty, quietly celebrated.` serif tagline + dual CTAs (Book / Discover), editorial marquee ribbon (CSS `@keyframes marquee` 45s), asymmetric 2-col Philosophy with Fig. 01 caption, **dark Signature Treatments** with staggered translate-y offsets + large-numeral watermarks + grayscale-hover-to-color reveal (pulls real `/api/services`), **Sanctuaries bento** with asymmetric col-span (8/4, 5/7) grid (pulls real `/api/salons`), Master Stylists portrait grid (only rendered when `/api/stylists` returns data), dark "Your first visit, on the house" incentive banner, and minimal footer with 10rem serif brand mark. All test IDs present (`nav-book-button`, `hero-book-now-cta`, `hero-discover-cta`, `treatment-card-book-cta`, `salon-location-book-cta`, `stylist-book-cta`, etc.). No backend changes required.
- Feature — 2026-07-04: **Beautexa marketing landing shipped at `/`** — new file `frontend/src/pages/BeautexaLanding.jsx` (~450 lines, zero new deps). The existing Maison Aurelle salon site was **preserved unchanged** and simply relocated to `/salon` in `App.js`. All other routes (`/book`, `/login`, `/manage`, `/owner`, etc.) unchanged. Sections: sticky Beautexa nav with `Explore Live Salon` (opens `/salon` in new tab) + `Book a Demo`, hero with tagline `Launch Your Salon's Digital Experience` + emerald primary CTA + 4 trust chips (White-label / Mobile Friendly / Modern Dashboard / Quick Setup) + browser-chrome mockup preview card, 6 feature cards (Branded Website, Online Booking, Packages & Offers, Staff Management, Customer Management, Business Insights) with emerald-icon-in-tile pattern that inverts on hover, Live Client section featuring `Luméa Studio` card with pulsing green "Live" badge + salon interior screenshot + 24×7/Branded/Beautexa stat pills, 3-step "How it works" with 01/02/03 rounded-circle numbering connected via dashed line, emerald→teal gradient final CTA with subtle gold radial accent, and 3-column footer with `Powered by Parsh Technologies`. Design palette: Emerald `#0F766E` (primary), Champagne Gold `#C9A227` (accents), Warm White `#FAFAF8` bg, text `#111827`/`#6B7280`. Beautexa logo asset saved at `/app/frontend/public/beautexa/logo.png`. All test IDs: `beautexa-landing`, `beautexa-brand`, `nav-explore-salon`, `nav-book-demo`, `hero-explore-salon`, `hero-book-demo`, `feature-card`, `client-explore-salon`, `client-book-appointment`, `how-step`, `final-book-demo`, `final-explore-salon`.
- Feature — 2026-07-07: **Final brand polish on Beutxai + login.** Replaced remaining "Sandy Hair Saloon" placeholder in `UnifiedLogin.jsx` with "The Gentlemen's Room" (login page header text). Wired all three "Book a Demo" buttons in `BeautexaLanding.jsx` (nav, hero, and final CTA) to open the Google Calendar appointment scheduling link in a new tab: `https://calendar.google.com/appointments/schedules/AcZssZ2HUMNHTPZYddim8Va4yA7F3YvIMbpjKee-tjgfTZWla5SbIUv4Ae47uDdV5ruEVqKvySKkEeKi`. Buttons converted from `<button>` to `<a target="_blank" rel="noreferrer">` while preserving existing test IDs and styles. Verified via Playwright DOM inspection + screenshots on both `/` and `/login`.
- Feature — 2026-07-07: **Cross-cutting UX polish (5 items).**
- Feature — 2026-07-07: **`/book` step reorder — Location comes before Service.** New order: 1) Location → 2) Service → 3) Stylist → 4) Date & Time. Reasoning: only show the customer services that the chosen branch actually offers, eliminating "unavailable service" dead-ends. Implementation in `BookingFlow.jsx`: swapped `STEPS_STYLIST_FIRST`/`STEPS_SLOT_FIRST` labels; `/api/salons` now loads on mount and `/api/services?salon_id=<id>` loads once a branch is chosen; `canProceed`, sticky footer, URL prefill (`?salon=`, `?service=`, `?stylist=`), and Continue-disabled logic all rewired to the new step indices. Changing the salon on step 0 resets any previously chosen service so the customer can't advance with a service the new branch doesn't offer. All other UI, validation, and booking logic unchanged.

  1. Removed "My Visits" nav + footer link from `/salon` (`LandingPage.jsx`).
  2. Central `frontend/src/lib/phoneValidation.js` helper (sanitizer + validator + shared helper strings). Applied to Login (10-digit strict when +91, else 6+ min), Booking Details (now read-only since OTP-verified), Customer Lookup, Customer Manage, Staff form, Manager form. Real-time inline error messaging + button-disabling for invalid input.
  3. **Removed the separate `Login Phone` field** from Staff and Manager forms. Single field labeled "Phone Number (WhatsApp Number)" with helper text "This number will be used for login, OTP verification, and WhatsApp communication." Frontend now sends the value as both `phone` and `login_phone` in the payload — backend unchanged.
  4. **Owner Insights redesign** (`InsightsDashboard.jsx` rewritten). Added `Custom Range` period (4th option) driven by a two-month range calendar in a Popover. New prominent "Viewing" card highlights: `Monthly → July 2026`, `Weekly → July 2026 • Week 2` (backend week-of-month = 1 + Monday-index within the month), `Daily → 7 July 2026 • Tuesday`, `Custom → 1 Jun 2026 — 30 Jun 2026`. Backend `_revenue_period_bounds` extended to accept `period=custom` + `start_date`/`end_date` (with reasonable 730-day cap and range validation).
  5. **Layout**: Status Counts moved ABOVE the Revenue Trend by Day chart.
  6. **Manager Dashboard** now reuses the same `<InsightsDashboard>` component (parameterized with `endpoint`, `authToken`, `titleMain`, `testidPrefix`) — hits `/api/manager/revenue-insights`, no salon switcher, auto-scoped to the manager's salon by JWT. Backend manager endpoint gained the same `period=custom` support. Zero code duplication between owner and manager insights.


## Prioritized Backlog

### P0
- None currently open after owner no-show + insights implementation and owner API auth fix.

### P1
- Add owner-side customer reschedule controls directly inside daily bookings.
- Add better empty-state guidance and optional filters for no-show/service/stylist views.
- Confirm any dedicated approved Twilio template SID for no-show follow-up if the business wants template-based sends instead of free-text fallback.
- Optionally harden runtime CORS origins instead of wildcard config.
- Add login lockout/rate limiting for stylist and owner PIN login.

### P2 / Future Polish
- 30/60-day chart windows.
- Per-stylist revenue split visuals.
- CSV export for bookings, no-shows, and revenue reports.
- Loyalty/repeat-visit discounts, reviews/ratings, multi-location support.
