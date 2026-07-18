import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Globe2,
  CalendarCheck,
  Gift,
  Users,
  UserCheck,
  BarChart3,
  Check,
  Sparkles,
} from "lucide-react";

const EMERALD = "#0F766E";
const GOLD = "#C9A227";

const FEATURES = [
  {
    icon: Globe2,
    title: "Branded Website",
    copy: "Every salon gets its own premium website.",
  },
  {
    icon: CalendarCheck,
    title: "Online Booking",
    copy: "Customers book appointments 24×7.",
  },
  {
    icon: Gift,
    title: "Packages & Offers",
    copy: "Promote memberships, coupons and seasonal offers.",
  },
  {
    icon: Users,
    title: "Staff Management",
    copy: "Manage artists, schedules and availability.",
  },
  {
    icon: UserCheck,
    title: "Customer Management",
    copy: "Track customer history and appointments.",
  },
  {
    icon: BarChart3,
    title: "Business Insights",
    copy: "Monitor bookings and business growth.",
  },
];

const TRUST = ["White-label", "Mobile Friendly", "Modern Dashboard", "Quick Setup"];

const STEPS = [
  { n: "01", title: "We build your branded website.", copy: "Your identity. Your colors. Your services." },
  { n: "02", title: "You manage your business.", copy: "Staff, offers, packages and memberships." },
  { n: "03", title: "Customers book online.", copy: "24×7 appointments — from any device." },
];

export default function BeautexaLanding() {
  return (
    <div
      className="min-h-screen bg-[#FAFAF8] text-[#111827] font-sans antialiased"
      data-testid="beautexa-landing"
      style={{ fontFamily: "'Inter', 'Outfit', system-ui, sans-serif" }}
    >
      {/* NAV */}
      <header className="sticky top-0 z-50 bg-[#FAFAF8]/85 backdrop-blur-xl border-b border-[#E5E7EB]/70">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5" data-testid="beautexa-brand">
            <img
              src="/beautexa/logo.png"
              alt="Beutxai"
              className="h-9 w-9 rounded-lg object-cover shadow-sm"
            />
            <span className="font-semibold tracking-tight text-lg">Beutxai</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm text-[#6B7280]">
            <a href="#features" className="hover:text-[#111827] transition-colors">Features</a>
            <a href="#client" className="hover:text-[#111827] transition-colors">Live Client</a>
            <a href="#how" className="hover:text-[#111827] transition-colors">How it works</a>
          </nav>
          <div className="flex items-center gap-3">
            <a
              href="/salon"
              target="_blank"
              rel="noreferrer"
              data-testid="nav-explore-salon"
              className="hidden sm:inline-flex items-center gap-1.5 text-sm text-[#111827] hover:text-[#0F766E] transition-colors"
            >
              Explore Live Salon <ArrowUpRight className="h-3.5 w-3.5" />
            </a>
            <a
              href="https://calendar.google.com/appointments/schedules/AcZssZ2HUMNHTPZYddim8Va4yA7F3YvIMbpjKee-tjgfTZWla5SbIUv4Ae47uDdV5ruEVqKvySKkEeKi"
              target="_blank"
              rel="noreferrer"
              data-testid="nav-book-demo"
              className="rounded-full bg-[#0F766E] hover:bg-[#0b5f58] text-white text-sm font-medium px-4 py-2 transition-colors shadow-sm"
            >
              Book a Demo
            </a>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="relative overflow-hidden">
        {/* soft ambient background */}
        <div className="absolute inset-0 -z-10 pointer-events-none">
          <div className="absolute top-[-10%] left-[-10%] h-[500px] w-[500px] rounded-full bg-[#0F766E]/8 blur-3xl" />
          <div className="absolute top-[10%] right-[-10%] h-[400px] w-[400px] rounded-full bg-[#C9A227]/8 blur-3xl" />
        </div>

        <div className="max-w-7xl mx-auto px-6 lg:px-10 pt-16 md:pt-24 pb-16 md:pb-24">
          <div className="max-w-4xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#E5E7EB] bg-white px-3 py-1 mb-8 text-xs font-medium text-[#0F766E]">
              <Sparkles className="h-3.5 w-3.5" style={{ color: GOLD }} />
              A white-label platform for beauty businesses
            </div>
            <h1 className="font-semibold tracking-[-0.03em] text-4xl sm:text-5xl md:text-6xl lg:text-7xl leading-[1.05] mb-6">
              Launch Your Salon&apos;s <br className="hidden sm:block" />
              <span className="relative inline-block">
                <span style={{ color: EMERALD }}>Digital Experience.</span>
              </span>
            </h1>
            <p className="text-base md:text-lg text-[#6B7280] max-w-2xl mx-auto leading-relaxed mb-10">
              Build your own branded salon website with online appointments, offers,
              memberships, customer management and more — all powered by Beutxai.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-8">
              <a
                href="/salon"
                target="_blank"
                rel="noreferrer"
                data-testid="hero-explore-salon"
                className="inline-flex items-center gap-2 rounded-full bg-[#0F766E] hover:bg-[#0b5f58] text-white text-sm md:text-base font-medium px-6 py-3.5 transition-all shadow-lg shadow-[#0F766E]/20 hover:shadow-xl hover:shadow-[#0F766E]/25 hover:-translate-y-0.5"
              >
                Explore Live Salon <ArrowUpRight className="h-4 w-4" />
              </a>
              <a
                href="https://calendar.google.com/appointments/schedules/AcZssZ2HUMNHTPZYddim8Va4yA7F3YvIMbpjKee-tjgfTZWla5SbIUv4Ae47uDdV5ruEVqKvySKkEeKi"
                target="_blank"
                rel="noreferrer"
                data-testid="hero-book-demo"
                className="inline-flex items-center gap-2 rounded-full border border-[#E5E7EB] bg-white hover:border-[#111827] text-[#111827] text-sm md:text-base font-medium px-6 py-3.5 transition-all"
              >
                Book a Demo
              </a>
            </div>

            <ul className="flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-xs md:text-sm text-[#6B7280]">
              {TRUST.map((t) => (
                <li key={t} className="inline-flex items-center gap-1.5">
                  <Check className="h-4 w-4 text-[#10B981]" />
                  {t}
                </li>
              ))}
            </ul>
          </div>

          {/* Live product preview card */}
          <div className="mt-16 md:mt-20 max-w-5xl mx-auto">
            <div className="relative rounded-2xl bg-white border border-[#E5E7EB] shadow-2xl shadow-[#0F766E]/5 overflow-hidden">
              <div className="flex items-center gap-2 border-b border-[#E5E7EB] bg-[#FAFAF8] px-4 py-2.5">
                <span className="h-2.5 w-2.5 rounded-full bg-[#FF5F57]" />
                <span className="h-2.5 w-2.5 rounded-full bg-[#FEBC2E]" />
                <span className="h-2.5 w-2.5 rounded-full bg-[#28C840]" />
                <span className="ml-3 text-xs text-[#6B7280] truncate">
                  thegentlemensroom.Beutxai.app
                </span>
              </div>
              <div className="aspect-[16/9] relative">
                <img
                  src="/landing/hero.jpg"
                  alt="Preview of a client salon website built with Beutxai"
                  className="absolute inset-0 h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />
                <div className="absolute bottom-6 left-6 right-6 text-white">
                  <p className="text-[11px] uppercase tracking-[0.3em] opacity-80 mb-1.5">
                    Client · The Gentlemen&apos;s Room
                  </p>
                  <p className="font-semibold text-xl md:text-2xl">
                    Their website. Their brand. Our platform.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="py-20 md:py-28 border-t border-[#E5E7EB]/60">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <div className="max-w-2xl mb-14">
            <p className="text-xs font-medium tracking-[0.2em] uppercase text-[#0F766E] mb-3">
              — Platform
            </p>
            <h2 className="font-semibold tracking-[-0.02em] text-3xl md:text-4xl lg:text-5xl leading-[1.1] mb-4">
              Everything a modern salon needs, in one place.
            </h2>
            <p className="text-[#6B7280] text-base md:text-lg leading-relaxed">
              Beutxai gives beauty businesses a beautiful, branded digital home — with the tools
              that actually move the needle.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <article
                  key={f.title}
                  className="group rounded-2xl bg-white border border-[#E5E7EB] p-6 md:p-7 hover:border-[#0F766E]/30 hover:shadow-lg hover:shadow-[#0F766E]/5 transition-all"
                  data-testid="feature-card"
                >
                  <div className="h-11 w-11 rounded-xl bg-[#0F766E]/8 border border-[#0F766E]/10 flex items-center justify-center mb-5 group-hover:bg-[#0F766E] group-hover:border-[#0F766E] transition-colors">
                    <Icon className="h-5 w-5 text-[#0F766E] group-hover:text-white transition-colors" />
                  </div>
                  <h3 className="font-semibold text-lg tracking-tight mb-1.5">{f.title}</h3>
                  <p className="text-sm text-[#6B7280] leading-relaxed">{f.copy}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* LIVE CLIENT */}
      <section id="client" className="py-20 md:py-28 bg-white border-t border-[#E5E7EB]/60">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 items-center">
            <div className="lg:col-span-5">
              <p className="text-xs font-medium tracking-[0.2em] uppercase text-[#0F766E] mb-3">
                — Live Client
              </p>
              <h2 className="font-semibold tracking-[-0.02em] text-3xl md:text-4xl lg:text-5xl leading-[1.1] mb-5">
                Built for real businesses.
              </h2>
              <p className="text-[#6B7280] text-base md:text-lg leading-relaxed mb-8">
                Beutxai isn&apos;t a concept. It&apos;s already helping real salons manage appointments
                and grow their online presence.
              </p>
              <div className="flex flex-wrap gap-3">
                <a
                  href="/salon"
                  target="_blank"
                  rel="noreferrer"
                  data-testid="client-explore-salon"
                  className="inline-flex items-center gap-2 rounded-full bg-[#0F766E] hover:bg-[#0b5f58] text-white text-sm font-medium px-5 py-3 transition-colors shadow-sm"
                >
                  Explore Live Salon <ArrowUpRight className="h-4 w-4" />
                </a>
                <a
                  href="/salon"
                  target="_blank"
                  rel="noreferrer"
                  data-testid="client-book-appointment"
                  className="inline-flex items-center gap-2 rounded-full border border-[#E5E7EB] hover:border-[#111827] text-[#111827] text-sm font-medium px-5 py-3 transition-colors bg-white"
                >
                  Book Appointment
                </a>
              </div>
            </div>

            <div className="lg:col-span-7">
              <div className="relative rounded-2xl bg-[#FAFAF8] border border-[#E5E7EB] p-6 md:p-8">
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-center gap-4">
                    <div
                      className="h-14 w-14 rounded-xl flex items-center justify-center font-semibold text-white text-xl shrink-0"
                      style={{
                        background: `linear-gradient(135deg, ${EMERALD}, #134e4a)`,
                      }}
                    >
                      G
                    </div>
                    <div>
                      <h3 className="font-semibold text-xl tracking-tight">The Gentlemen&apos;s Room</h3>
                      <p className="text-sm text-[#6B7280] mt-0.5">
                        Premium Hair · Beard · Grooming
                      </p>
                    </div>
                  </div>
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-[#10B981]/10 text-[#10B981] text-xs font-medium px-2.5 py-1 border border-[#10B981]/20">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#10B981] animate-pulse" />
                    Live
                  </span>
                </div>

                <div className="rounded-xl overflow-hidden border border-[#E5E7EB] bg-white">
                  <div className="flex items-center gap-1.5 border-b border-[#E5E7EB] px-3 py-2 bg-[#FAFAF8]">
                    <span className="h-2 w-2 rounded-full bg-[#FF5F57]" />
                    <span className="h-2 w-2 rounded-full bg-[#FEBC2E]" />
                    <span className="h-2 w-2 rounded-full bg-[#28C840]" />
                  </div>
                  <div className="aspect-[16/10] overflow-hidden">
                    <img
                      src="/landing/loc2.jpg"
                      alt="The Gentlemen's Room salon website preview"
                      className="h-full w-full object-cover hover:scale-105 transition-transform duration-700"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 mt-6">
                  {[
                    { k: "Online Booking", v: "24×7" },
                    { k: "Website", v: "Branded" },
                    { k: "Powered by", v: "Beutxai" },
                  ].map((s) => (
                    <div
                      key={s.k}
                      className="rounded-lg bg-white border border-[#E5E7EB] px-3 py-2.5"
                    >
                      <p className="text-[10px] uppercase tracking-wider text-[#6B7280]">
                        {s.k}
                      </p>
                      <p className="text-sm font-medium text-[#111827] mt-0.5">{s.v}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="py-20 md:py-28 border-t border-[#E5E7EB]/60">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <p className="text-xs font-medium tracking-[0.2em] uppercase text-[#0F766E] mb-3">
              — How it works
            </p>
            <h2 className="font-semibold tracking-[-0.02em] text-3xl md:text-4xl lg:text-5xl leading-[1.1]">
              From zero to booking, in three steps.
            </h2>
          </div>

          <div className="relative grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
            {/* connecting dotted line */}
            <div className="hidden md:block absolute top-6 left-[16.66%] right-[16.66%] border-t border-dashed border-[#E5E7EB]" />
            {STEPS.map((s, i) => (
              <div
                key={s.n}
                className="relative rounded-2xl bg-white border border-[#E5E7EB] p-6 md:p-7 text-center"
                data-testid="how-step"
              >
                <div
                  className="mx-auto h-12 w-12 rounded-full bg-white border-2 flex items-center justify-center font-semibold text-sm mb-5"
                  style={{ borderColor: EMERALD, color: EMERALD }}
                >
                  {s.n}
                </div>
                <h3 className="font-semibold text-lg tracking-tight mb-2">{s.title}</h3>
                <p className="text-sm text-[#6B7280] leading-relaxed">{s.copy}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="py-20 md:py-28">
        <div className="max-w-5xl mx-auto px-6 lg:px-10">
          <div
            className="rounded-3xl overflow-hidden relative p-10 md:p-16 text-center text-white"
            style={{
              background: `linear-gradient(135deg, ${EMERALD} 0%, #0b5f58 100%)`,
            }}
          >
            {/* subtle gold accent */}
            <div
              className="absolute inset-0 opacity-20 pointer-events-none"
              style={{
                background: `radial-gradient(circle at 80% 20%, ${GOLD} 0%, transparent 40%)`,
              }}
            />
            <div className="relative">
              <h2 className="font-semibold tracking-[-0.02em] text-3xl md:text-4xl lg:text-5xl leading-[1.1] mb-5">
                Ready to modernize your salon?
              </h2>
              <p className="text-white/80 text-base md:text-lg max-w-xl mx-auto mb-9">
                Launch your own branded beauty business platform with Beutxai.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <a
                  href="https://calendar.google.com/appointments/schedules/AcZssZ2HUMNHTPZYddim8Va4yA7F3YvIMbpjKee-tjgfTZWla5SbIUv4Ae47uDdV5ruEVqKvySKkEeKi"
                  target="_blank"
                  rel="noreferrer"
                  data-testid="final-book-demo"
                  className="inline-flex items-center gap-2 rounded-full bg-white text-[#0F766E] hover:bg-[#FAFAF8] text-sm md:text-base font-medium px-6 py-3.5 transition-colors shadow-lg"
                >
                  Book a Demo
                </a>
                <a
                  href="/salon"
                  target="_blank"
                  rel="noreferrer"
                  data-testid="final-explore-salon"
                  className="inline-flex items-center gap-2 rounded-full border border-white/40 hover:bg-white/10 text-white text-sm md:text-base font-medium px-6 py-3.5 transition-colors"
                >
                  Explore Live Salon <ArrowUpRight className="h-4 w-4" />
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-[#E5E7EB]/60 bg-white">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-12">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-8 md:gap-6">
            <div className="md:col-span-6">
              <div className="flex items-center gap-2.5 mb-4">
                <img
                  src="/beautexa/logo.png"
                  alt="Beutxai"
                  className="h-10 w-10 rounded-lg object-cover shadow-sm"
                />
                <span className="font-semibold tracking-tight text-lg">Beutxai</span>
              </div>
              <p className="text-sm text-[#6B7280] max-w-md leading-relaxed">
                Empowering beauty businesses, digitally.
              </p>
            </div>
            <div className="md:col-span-3">
              <p className="text-xs uppercase tracking-wider text-[#6B7280] mb-3">
                Quick Links
              </p>
              <ul className="space-y-2 text-sm">
                <li>
                  <a
                    href="/salon"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[#111827] hover:text-[#0F766E] transition-colors"
                  >
                    Explore Live Salon
                  </a>
                </li>
                <li>
                  <a href="#features" className="text-[#111827] hover:text-[#0F766E] transition-colors">
                    Features
                  </a>
                </li>
                <li>
                  <a href="#how" className="text-[#111827] hover:text-[#0F766E] transition-colors">
                    How it works
                  </a>
                </li>
              </ul>
            </div>
            <div className="md:col-span-3">
              <p className="text-xs uppercase tracking-wider text-[#6B7280] mb-3">Legal</p>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link
                    to="/privacy"
                    data-testid="footer-privacy-link"
                    className="text-[#111827] hover:text-[#0F766E] transition-colors"
                  >
                    Privacy &amp; Policy
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-10 pt-6 border-t border-[#E5E7EB] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-[#6B7280]">
            <p>© {new Date().getFullYear()} Beutxai. All rights reserved.</p>
            <p>
              Powered by <span className="text-[#111827] font-medium">Parsh Technologies</span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
