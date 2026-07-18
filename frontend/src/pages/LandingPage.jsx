import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { getValidToken } from "../lib/authStore";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Curated imagery bundled locally (served from /app/frontend/public/landing/)
// This avoids any dependency on external CDNs (Unsplash outages, blocked networks, etc.)
const HERO_IMAGE = "/landing/hero.jpg";
const PHILOSOPHY_IMAGE = "/landing/hair.jpg";
// Treatment fallbacks — salon / spa / hair specific
const TREATMENT_FALLBACK = [
  "/landing/t1.jpg", // hair cut in salon chair
  "/landing/t2.jpg", // barber / beard
  "/landing/t3.jpg", // gentleman scissor finish
  "/landing/t4.jpg", // spa facial massage
  "/landing/t5.jpg", // salon interior
  "/landing/t6.jpg", // face mask ritual
];
// Location fallbacks — salon interior architecture
const LOCATION_FALLBACK = [
  "/landing/loc1.jpg",
  "/landing/loc2.jpg",
  "/landing/loc3.jpg",
  "/landing/loc4.jpg",
];
// Branch overrides — first three sanctuary cards use uploaded interiors
// regardless of what image_url the salon document may carry from the DB.
const BRANCH_OVERRIDES = [
  "/landing/branch1.jpg",
  "/landing/branch2.jpg",
  "/landing/branch3.jpg",
];
// Stylist portrait fallbacks
const STYLIST_FALLBACK = [
  "/landing/s1.jpg",
  "/landing/s2.jpg",
  "/landing/s3.jpg",
  "/landing/s4.jpg",
];

// Static content — Our Sanctuaries (branch names & addresses only; booking CTA
// still routes to /book — no salon_id is passed because the DB may not have
// matching salon documents. The booking flow will let customers pick a salon.)
const BRANCHES = [
  {
    city: "Rajkot",
    name: "The Gentlemen's Room — Kalawad Road",
    address: "Kalawad Road, Rajkot, Gujarat",
    image: "/landing/branch1.jpg",
  },
  {
    city: "Rajkot",
    name: "The Gentlemen's Room — University Road",
    address: "University Road, Rajkot, Gujarat",
    image: "/landing/branch2.jpg",
  },
  {
    city: "Rajkot",
    name: "The Gentlemen's Room — Mavdi",
    address: "Mavdi, Rajkot, Gujarat",
    image: "/landing/branch3.jpg",
  },
  {
    city: "Rajkot",
    name: "The Gentlemen's Room — 150 Feet Ring Road",
    address: "150 Feet Ring Road, Rajkot, Gujarat",
    image: "/landing/loc4.jpg",
  },
];

const BRAND = "The Gentlemen's Room";

// Static content — Salon services (grouped by category).
// Duration & pricing are intentionally NOT shown on the landing page.
const SERVICE_CATEGORIES = [
  {
    key: "hair",
    label: "Hair & Beard",
    tagline: "Precision cuts, beard artistry and scalp rituals.",
    image: "/landing/haircutting.jpg",
    items: [
      "Signature Haircut (Wash & Blow-Dry Included)",
      "Haircut + Beard Combo",
      "Beard Trim & Shape",
      "Beard Styling",
      "Beard Spa",
      "Beard Colour",
      "Global Hair Colour",
      "Grey Coverage",
      "Highlights",
      "Dandruff Hair Spa",
      "Hair Fall Treatment",
      "Keratin Smoothening",
      "Scalp Detox",
      "Head Massage (Dry / Hot Oil)",
      "Shoulder & Neck Massage",
    ],
  },
  {
    key: "skin",
    label: "Skin & Facial",
    tagline: "Deep cleanses, brightening rituals and considered skin therapy.",
    image: "/landing/skin.jpg",
    items: [
      "Classic Clean-up",
      "D-Tan Facial",
      "Charcoal Facial",
      "Gold Facial",
      "Oxy Facial",
      "Anti-ageing Facial",
      "Acne-Control Facial",
      "Skin Polishing",
    ],
  },
  {
    key: "wax",
    label: "Waxing & Threading",
    tagline: "Discreet, precise finishes — Regular, Rica or Chocolate wax.",
    image: "/landing/waxing.jpg",
    items: [
      "Eyebrow Threading",
      "Nose Wax",
      "Ear Wax",
      "Half / Full Arms",
      "Half / Full Legs",
      "Chest Wax",
      "Back Wax",
      "Shoulder Wax",
      "Full Body Wax",
    ],
  },
  {
    key: "grooming",
    label: "Grooming",
    tagline: "Manicures, pedicures and the final polish.",
    image: "/landing/grooming.jpg",
    items: [
      "Classic Manicure",
      "Deluxe Manicure",
      "Classic Pedicure",
      "Deluxe Pedicure",
      "Spa Pedicure",
      "Nail Buff & Shine",
    ],
  },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [services, setServices] = useState([]);
  const [salons, setSalons] = useState([]);
  const [stylists, setStylists] = useState([]);
  const [navScrolled, setNavScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setNavScrolled(window.scrollY > 60);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [svc, sal, sty] = await Promise.all([
          axios.get(`${API}/services`).catch(() => ({ data: [] })),
          axios.get(`${API}/salons`).catch(() => ({ data: { salons: [] } })),
          axios.get(`${API}/stylists`).catch(() => ({ data: [] })),
        ]);
        if (!alive) return;
        const svcList = Array.isArray(svc.data) ? svc.data : [];
        const salList = Array.isArray(sal.data?.salons) ? sal.data.salons : [];
        const styList = Array.isArray(sty.data) ? sty.data : [];
        setServices(svcList.slice(0, 6));
        setSalons(salList.slice(0, 4));
        setStylists(styList.slice(0, 4));
      } catch (e) {
        // silent — landing still renders with graceful empty states
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#FAF9F6] text-[#111] font-sans" data-testid="landing-page">
      {/* NAVIGATION */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
          navScrolled
            ? "bg-[#FAF9F6]/90 backdrop-blur-xl border-b border-[#111]/10"
            : "bg-transparent border-b border-transparent"
        }`}
        data-testid="landing-nav"
      >
        <div className="max-w-7xl mx-auto px-6 md:px-12 flex items-center justify-between h-20">
          <Link
            to="/"
            className={`font-serif text-2xl md:text-3xl tracking-tight transition-colors duration-500 ${
              navScrolled ? "text-[#111]" : "text-white"
            }`}
            data-testid="landing-brand"
          >
            {BRAND}
          </Link>
          <div className="hidden md:flex items-center gap-10">
            <a
              href="#philosophy"
              className={`text-[11px] uppercase tracking-[0.24em] transition-colors ${
                navScrolled ? "text-[#111]/70 hover:text-[#111]" : "text-white/80 hover:text-white"
              }`}
            >
              Philosophy
            </a>
            <a
              href="#treatments"
              className={`text-[11px] uppercase tracking-[0.24em] transition-colors ${
                navScrolled ? "text-[#111]/70 hover:text-[#111]" : "text-white/80 hover:text-white"
              }`}
            >
              Treatments
            </a>
            <a
              href="#sanctuaries"
              className={`text-[11px] uppercase tracking-[0.24em] transition-colors ${
                navScrolled ? "text-[#111]/70 hover:text-[#111]" : "text-white/80 hover:text-white"
              }`}
            >
              Sanctuaries
            </a>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(getValidToken("customer") ? "/book" : "/login?next=/book")}
              data-testid="nav-book-button"
              className={`text-[11px] uppercase tracking-[0.24em] px-5 py-3 border transition-all duration-300 ${
                navScrolled
                  ? "border-[#111] text-[#111] hover:bg-[#111] hover:text-white"
                  : "border-white text-white hover:bg-white hover:text-[#111]"
              }`}
            >
              Book Now
            </button>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section className="relative h-[100vh] w-full flex items-end overflow-hidden" data-testid="landing-hero">
        <img
          src={HERO_IMAGE}
          alt="Premium men's grooming studio"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/20 to-black/70" />
        <div className="relative max-w-7xl mx-auto w-full px-6 md:px-12 pb-24 md:pb-32 text-white">
          <p className="text-[11px] uppercase tracking-[0.3em] mb-8 opacity-90 animate-fade-in">
            Premium men&apos;s hair · beard · grooming studio
          </p>
          <h1 className="font-serif font-light text-5xl md:text-7xl lg:text-8xl leading-[0.95] tracking-tight max-w-4xl mb-10">
            The gentleman&apos;s
            <br />
            <em className="italic font-light">chair, refined.</em>
          </h1>
          <p className="text-base md:text-lg max-w-xl opacity-90 leading-relaxed mb-12">
            Precision haircuts, beard artistry, skin therapy, waxing and grooming — under one roof. Every haircut
            includes a complimentary wash and blow-dry.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link
              to="/book"
              data-testid="hero-book-now-cta"
              className="inline-flex items-center justify-center px-8 py-4 bg-white text-[#111] text-[11px] uppercase tracking-[0.28em] hover:bg-transparent hover:text-white border border-white transition-colors duration-300"
            >
              Book an Appointment
            </Link>
            <a
              href="#philosophy"
              data-testid="hero-discover-cta"
              className="inline-flex items-center justify-center px-8 py-4 border border-white/80 text-white text-[11px] uppercase tracking-[0.28em] hover:bg-white hover:text-[#111] transition-colors duration-300"
            >
              Discover the House
            </a>
          </div>
        </div>
        {/* scroll indicator */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-white/70 text-[10px] uppercase tracking-[0.3em] flex flex-col items-center gap-2">
          <span>Scroll</span>
          <span className="h-8 w-px bg-white/40" />
        </div>
      </section>

      {/* MARQUEE RIBBON */}
      <section className="py-8 border-y border-[#111]/10 bg-[#FAF9F6] overflow-hidden">
        <div className="flex whitespace-nowrap animate-marquee">
          {Array.from({ length: 2 }).map((_, gi) => (
            <div key={gi} className="flex items-center gap-16 pr-16 shrink-0">
              {[
                "Precision cuts, considered",
                "Beard artistry",
                "Complimentary wash & blow-dry",
                "Skin therapy for men",
                "Grooming, refined",
                "Every visit remembered",
              ].map((phrase, i) => (
                <span key={`${gi}-${i}`} className="font-serif text-2xl md:text-3xl italic text-[#111]/80">
                  {phrase}
                  <span className="mx-8 text-[#111]/30">•</span>
                </span>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* PHILOSOPHY */}
      <section
        id="philosophy"
        className="py-24 md:py-32 lg:py-40 max-w-7xl mx-auto px-6 md:px-12"
        data-testid="landing-philosophy"
      >
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 md:gap-16 items-center">
          <div className="md:col-span-6 relative">
            <div className="relative overflow-hidden">
              <img
                src={PHILOSOPHY_IMAGE}
                alt="A precision haircut in progress at The Gentlemen's Room"
                className="w-full aspect-[4/5] object-cover hover:scale-105 transition-transform duration-[1200ms] ease-out"
              />
            </div>
            <p className="text-[10px] uppercase tracking-[0.3em] mt-4 text-[#666]">
              Fig. 01 — The Signature Haircut
            </p>
          </div>
          <div className="md:col-span-6 md:pl-8">
            <p className="text-[11px] uppercase tracking-[0.3em] text-[#666] mb-6">Our Philosophy</p>
            <h2 className="font-serif font-light text-4xl md:text-5xl lg:text-6xl leading-[1.05] tracking-tight mb-8">
              Grooming,
              <br />
              <em className="italic">done properly.</em>
            </h2>
            <p className="text-base md:text-lg text-[#555] leading-relaxed mb-6">
              Trained specialists across hair, beard, skin, waxing and grooming — each an expert in their craft.
              Personalised consultation before every service. Hygiene held to hospital standards. No shortcuts, no
              upsell — just the treatment you came for, done with intention.
            </p>
            <p className="text-base md:text-lg text-[#555] leading-relaxed mb-10">
              Every haircut arrives with a complimentary wash and blow-dry. Every profile remembers your past cuts,
              preferences and allergies — so the conversation begins where you left off.
            </p>
            <Link
              to="/book"
              className="inline-flex items-center gap-3 text-[11px] uppercase tracking-[0.28em] text-[#111] border-b border-[#111] pb-2 hover:opacity-60 transition-opacity"
            >
              Book your chair
              <span className="text-lg">→</span>
            </Link>
          </div>
        </div>
      </section>

      {/* TREATMENTS — DARK EDITORIAL */}
      <section
        id="treatments"
        className="py-24 md:py-32 lg:py-40 bg-[#111] text-white overflow-hidden"
        data-testid="landing-treatments"
      >
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-end mb-16 md:mb-24">
            <div className="md:col-span-7">
              <p className="text-[11px] uppercase tracking-[0.3em] text-white/60 mb-6">— Our Services</p>
              <h2 className="font-serif font-light text-4xl md:text-5xl lg:text-6xl leading-[1.05] tracking-tight">
                Four studios,
                <br />
                <em className="italic">one address.</em>
              </h2>
            </div>
            <div className="md:col-span-5 md:pl-8">
              <p className="text-base text-white/70 leading-relaxed">
                Hair, skin, waxing and grooming — each looked after by specialists who do this and nothing else. Book
                any service in under a minute.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-16">
            {SERVICE_CATEGORIES.map((cat, i) => (
              <article
                key={cat.key}
                className={`group ${i % 2 === 1 ? "md:translate-y-16" : ""}`}
                data-testid="treatment-card"
              >
                <div className="relative overflow-hidden mb-6">
                  <img
                    src={cat.image}
                    alt={cat.label}
                    className="w-full aspect-[4/5] object-cover grayscale-[10%] group-hover:scale-105 group-hover:grayscale-0 transition-all duration-[1000ms] ease-out"
                  />
                  <span className="absolute top-4 left-4 font-serif text-6xl md:text-7xl font-light text-white/25">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="font-serif text-2xl md:text-3xl mb-3">{cat.label}</h3>
                <p className="text-sm text-white/60 leading-relaxed mb-5">{cat.tagline}</p>
                <ul className="grid grid-cols-1 sm:grid-cols-2 gap-y-1.5 gap-x-6 text-sm text-white/80 mb-6">
                  {cat.items.map((item) => (
                    <li key={item} className="leading-relaxed">
                      · {item}
                    </li>
                  ))}
                </ul>
                <Link
                  to="/book"
                  data-testid="treatment-card-book-cta"
                  className="inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.28em] text-white/80 hover:text-white border-b border-white/30 hover:border-white pb-1 transition-colors"
                >
                  Book from {cat.label.toLowerCase()} <span className="text-base">|</span>
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* SANCTUARIES / LOCATIONS */}
      <section
        id="sanctuaries"
        className="py-24 md:py-32 lg:py-40 bg-[#FAF9F6]"
        data-testid="landing-locations"
      >
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <div className="text-center max-w-3xl mx-auto mb-16 md:mb-24">
            <p className="text-[11px] uppercase tracking-[0.3em] text-[#666] mb-6">— Our Sanctuaries</p>
            <h2 className="font-serif font-light text-4xl md:text-5xl lg:text-6xl leading-[1.05] tracking-tight">
              Rooms that
              <br />
              <em className="italic">breathe with you.</em>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 md:gap-8">
            {BRANCHES.map((branch, i) => {
              // Bento asymmetric layout
              const spanClass =
                i === 0
                  ? "md:col-span-8"
                  : i === 1
                  ? "md:col-span-4"
                  : i === 2
                  ? "md:col-span-5"
                  : "md:col-span-7";
              const aspect = i === 0 || i === 3 ? "aspect-[16/10]" : "aspect-[4/5]";
              return (
                <article
                  key={branch.name}
                  className={`group ${spanClass}`}
                  data-testid="salon-location-card"
                >
                  <div className="relative overflow-hidden mb-5">
                    <img
                      src={branch.image}
                      alt={branch.name}
                      className={`w-full ${aspect} object-cover group-hover:scale-105 transition-transform duration-[1000ms] ease-out`}
                    />
                  </div>
                  <div className="flex items-start justify-between gap-6">
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.28em] text-[#666] mb-2">
                        {branch.city}
                      </p>
                      <h3 className="font-serif text-2xl md:text-3xl mb-2">{branch.name}</h3>
                      <p className="text-sm text-[#555] leading-relaxed max-w-md">{branch.address}</p>
                    </div>
                    <Link
                      to="/book"
                      data-testid="salon-location-book-cta"
                      className="shrink-0 inline-flex items-center text-[10px] uppercase tracking-[0.28em] text-[#111] border-b border-[#111] pb-1 hover:opacity-60 transition-opacity"
                    >
                      Book →
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* INCENTIVE BANNER */}
      <section className="py-24 md:py-32 lg:py-40 bg-[#111] text-white text-center px-6" data-testid="landing-incentive">
        <div className="max-w-3xl mx-auto">
          <p className="text-[11px] uppercase tracking-[0.3em] text-white/60 mb-8">— Begin your journey</p>
          <h2 className="font-serif font-light text-4xl md:text-5xl lg:text-6xl leading-[1.05] tracking-tight mb-8">
            Your first visit,
            <br />
            <em className="italic">on the house.</em>
          </h2>
          <p className="text-base md:text-lg text-white/70 max-w-xl mx-auto leading-relaxed mb-12">
            A complimentary consultation with your chosen specialist. Bring your reference photos, your questions and
            any old habits worth breaking.
          </p>
          <Link
            to="/book"
            data-testid="incentive-book-cta"
            className="inline-flex items-center justify-center px-10 py-5 bg-white text-[#111] text-[11px] uppercase tracking-[0.3em] hover:bg-transparent hover:text-white border border-white transition-colors duration-300"
          >
            Book an Appointment
          </Link>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-[#FAF9F6] border-t border-[#111]/10">
        <div className="max-w-7xl mx-auto px-6 md:px-12 pt-20 pb-10">
          <h3 className="font-serif font-light text-7xl md:text-9xl lg:text-[10rem] leading-none tracking-tighter mb-16">
            {BRAND}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 md:gap-16 pb-16 border-b border-[#111]/10">
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-[#666] mb-4">Navigate</p>
              <ul className="space-y-3 text-sm">
                <li><a href="#philosophy" className="hover:opacity-60 transition-opacity">Philosophy</a></li>
                <li><a href="#treatments" className="hover:opacity-60 transition-opacity">Treatments</a></li>
                <li><a href="#sanctuaries" className="hover:opacity-60 transition-opacity">Sanctuaries</a></li>
              </ul>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-[#666] mb-4">Account</p>
              <ul className="space-y-3 text-sm">
                <li><Link to="/book" className="hover:opacity-60 transition-opacity">Book</Link></li>
                <li><Link to="/login" className="hover:opacity-60 transition-opacity">Login</Link></li>
              </ul>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-[#666] mb-4">Contact</p>
              <ul className="space-y-3 text-sm text-[#555]">
                <li>hello@thegentlemensroom.com</li>
                <li>Open, 7 days a week</li>
              </ul>
            </div>
          </div>
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center pt-8 gap-4 text-[10px] uppercase tracking-[0.28em] text-[#666]">
            <p>© {new Date().getFullYear()} {BRAND}. All rights reserved.</p>
            <p>Grooming, done properly.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
