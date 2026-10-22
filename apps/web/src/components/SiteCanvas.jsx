/** A safe, reusable website renderer. It renders SiteSpec data, never user HTML. */

const palettes = {
  slate: ['#0a0a0c', '#f8fafc', '#a1a1aa', '#a78bfa'],
  ink: ['#09090b', '#fafafa', '#a1a1aa', '#22d3ee'],
  forest: ['#071611', '#ecfdf5', '#9ad5c0', '#34d399'],
  clay: ['#20110d', '#fff7ed', '#f1bda0', '#fb923c'],
  indigo: ['#0e1024', '#eef2ff', '#bac5ff', '#818cf8'],
  sand: ['#18150f', '#fffbeb', '#e2d3b0', '#fbbf24'],
};
const themes = {
  portfolio: { eyebrow: 'Selected work', wrap: 'max-w-6xl' },
  freelancer: { eyebrow: 'Independent practice', wrap: 'max-w-5xl' },
  business: { eyebrow: 'A little closer to home', wrap: 'max-w-6xl' },
  event: { eyebrow: 'Join us', wrap: 'max-w-5xl' },
  personal: { eyebrow: 'A little about me', wrap: 'max-w-4xl' },
};
function Contact({ spec, muted }) {
  if (!spec.contact_email && !spec.contact_phone && !spec.location) return null;
  return <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-sm" style={{ color: muted }}>
    {spec.contact_email && <a className="hover:underline" href={`mailto:${spec.contact_email}`}>{spec.contact_email}</a>}
    {spec.contact_phone && <a className="hover:underline" href={`tel:${spec.contact_phone}`}>{spec.contact_phone}</a>}
    {spec.location && <span>{spec.location}</span>}
  </div>;
}
function Section({ section, text, muted, accent, card }) {
  return <section className={card}>
    <span className="text-xs font-semibold uppercase tracking-[.17em]" style={{ color: accent }}>{section.kicker || 'Explore'}</span>
    <h2 className="mt-3 text-xl font-semibold tracking-tight sm:text-2xl" style={{ color: text }}>{section.heading}</h2>
    {section.body && <p className="mt-3 text-sm leading-6 sm:text-base" style={{ color: muted }}>{section.body}</p>}
    {section.items?.length > 0 && <div className="mt-5 flex flex-wrap gap-2">{section.items.map((item) => <span key={item} className="rounded-full border border-white/10 bg-black/10 px-3 py-1.5 text-sm" style={{ color: accent }}>{item}</span>)}</div>}
  </section>;
}
export default function SiteCanvas({ spec, compact = false }) {
  const [background, text, muted, accent] = palettes[spec.theme] || palettes.slate;
  const template = themes[spec.template] || themes.portfolio;
  const card = spec.section_style === 'minimal' ? 'border-t border-white/10 py-7' : spec.section_style === 'soft' ? 'rounded-[1.5rem] bg-white/[.07] p-6 sm:p-8' : 'rounded-[1.5rem] border border-white/10 bg-white/[.025] p-6 sm:p-8';
  const sections = spec.sections || [];
  const isEvent = spec.template === 'event';
  const isBusiness = spec.template === 'business';
  const isPersonal = spec.template === 'personal';
  const isFreelancer = spec.template === 'freelancer';
  const isPortfolio = spec.template === 'portfolio';
  const compactClass = compact ? 'p-7 sm:p-9' : 'px-6 py-8 sm:px-10 sm:py-10';
  const buttonStyle = { background: accent, color: background };
  const cta = spec.cta_label || (isEvent ? 'Reserve your place' : 'Get in touch');
  return <div style={{ background, color: text, minHeight: compact ? 600 : '100vh', '--site-accent': accent }} className={`${compactClass} relative overflow-hidden`}>
    <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-36 h-96 w-96 rounded-full opacity-10 blur-3xl" style={{ background: accent }} />
    <div className={`relative mx-auto ${template.wrap}`}>
      {spec.show_header !== false && <header className="flex items-center justify-between border-b border-white/10 pb-5">
        <a href="#top" className="flex items-center gap-2 text-sm font-semibold tracking-tight"><span className="h-2 w-2 rounded-full" style={{ background: accent }} />{spec.site_name}</a>
        <nav className="hidden items-center gap-5 text-xs sm:flex" style={{ color: muted }}>
          {sections.slice(0, 3).map((s) => <a key={s.key} className="hover:opacity-100" href={`#${s.key}`}>{s.heading}</a>)}
          {spec.show_contact !== false && (spec.contact_email || spec.contact_phone) && <a href="#contact">Contact</a>}
        </nav>
      </header>}
      <main id="top">
        <section className={`relative ${isEvent ? 'py-16 text-center sm:py-24' : isPersonal ? 'py-14 sm:py-20' : 'grid gap-9 py-12 sm:py-16 md:grid-cols-[1.15fr_.85fr] md:items-center'}`}>
          <div className={isEvent ? 'mx-auto max-w-3xl' : ''}>
            <p className="text-xs font-semibold uppercase tracking-[.2em]" style={{ color: accent }}>{spec.hero_eyebrow || template.eyebrow}</p>
            <h1 className={`mt-5 font-semibold tracking-[-.055em] ${isEvent ? 'text-5xl leading-[.98] sm:text-7xl' : 'max-w-3xl text-5xl leading-[1.02] sm:text-6xl lg:text-7xl'}`}>{spec.site_name}</h1>
            <p className={`mt-5 font-medium leading-relaxed ${isEvent ? 'mx-auto max-w-2xl text-xl sm:text-2xl' : 'max-w-2xl text-lg sm:text-xl'}`} style={{ color: muted }}>{spec.tagline}</p>
            {spec.hero_body && <p className={`mt-4 leading-7 ${isEvent ? 'mx-auto max-w-xl' : 'max-w-xl'}`} style={{ color: muted }}>{spec.hero_body}</p>}
            {(spec.show_cta !== false) && <div className={`mt-7 flex flex-wrap items-center gap-4 ${isEvent ? 'justify-center' : ''}`}>
              <a href={spec.contact_email ? `mailto:${spec.contact_email}` : '#contact'} className="rounded-full px-5 py-3 text-sm font-semibold transition hover:brightness-110" style={buttonStyle}>{cta} <span aria-hidden="true">↗</span></a>
              {!isEvent && <span className="text-xs" style={{ color: muted }}>{isFreelancer ? 'Available for select projects' : isBusiness ? (spec.location || 'Thoughtfully made, every day') : isPersonal ? 'Curious by nature · open to conversation' : 'A small selection of recent work'}</span>}
            </div>}
          </div>
          {!isEvent && !isPersonal && <div className="relative min-h-52 overflow-hidden rounded-[1.75rem] border border-white/10 bg-white/[.035] p-5 sm:min-h-64 sm:p-7">
            <div className="absolute inset-0 opacity-20" style={{ background: `radial-gradient(circle at 75% 20%, ${accent}, transparent 52%)` }} />
            <div className="relative flex h-full min-h-44 flex-col justify-between sm:min-h-52">
              {isBusiness ? <><div className="flex items-start justify-between"><span className="text-xs uppercase tracking-[.16em]" style={{ color: muted }}>A note from your neighborhood</span><span className="text-3xl" style={{ color: accent }}>⌖</span></div><div><p className="text-2xl font-medium leading-snug tracking-tight">Personal service, done properly.</p><p className="mt-3 text-sm" style={{ color: muted }}>{spec.location || 'Locally rooted · Always welcoming'}</p></div><div className="border-t border-white/10 pt-4 text-xs" style={{ color: muted }}>Visit us · Reach out · We’re here to help</div></>
                : isFreelancer ? <><div className="flex items-start justify-between"><span className="text-xs uppercase tracking-[.16em]" style={{ color: muted }}>The right partner for</span><span className="text-3xl" style={{ color: accent }}>↗</span></div><div><p className="text-2xl font-medium leading-snug tracking-tight">{sections[0]?.heading || 'Thoughtful work, start to finish.'}</p><p className="mt-3 line-clamp-2 text-sm leading-6" style={{ color: muted }}>{sections[0]?.body || 'A clear, collaborative process that gets you to the right result.'}</p></div><div className="border-t border-white/10 pt-4 text-xs" style={{ color: muted }}>Independent · Available for select projects</div></>
                  : <><div className="flex items-start justify-between"><span className="text-xs uppercase tracking-[.16em]" style={{ color: muted }}>{isPortfolio ? 'A few recent favorites' : 'A note to self'}</span><span className="text-3xl" style={{ color: accent }}>✳</span></div><p className="max-w-sm text-2xl font-medium leading-snug tracking-tight">{sections[0]?.heading || spec.tagline}</p><div className="flex items-center justify-between border-t border-white/10 pt-4 text-xs" style={{ color: muted }}><span>{isPortfolio ? 'Selected projects · latest edition' : 'Good work, shared with care.'}</span><span style={{ color: accent }}>01 / 04</span></div></>}
            </div>
          </div>}
        </section>
        {isBusiness && spec.show_contact !== false && <div className="mb-10 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/[.025] p-5"><div><p className="text-xs uppercase tracking-widest" style={{ color: accent }}>Come by</p><Contact spec={spec} muted={muted} /></div><span className="text-sm" style={{ color: muted }}>{spec.location || 'A warm welcome is waiting.'}</span></div>}
        <section className="grid gap-4 sm:grid-cols-2">{sections.map((s) => <div id={s.key} key={s.key}><Section section={s} text={text} muted={muted} accent={accent} card={card} /></div>)}</section>
        {spec.show_contact !== false && !isBusiness && <section id="contact" className="mt-12 flex flex-col justify-between gap-5 rounded-2xl border border-white/10 bg-white/[.025] p-6 sm:flex-row sm:items-center sm:p-8"><div><p className="text-xs font-semibold uppercase tracking-[.18em]" style={{ color: accent }}>Next step</p><h2 className="mt-2 text-2xl font-semibold tracking-tight">Have something in mind?</h2><Contact spec={spec} muted={muted} /></div>{spec.contact_email && <a className="text-sm font-medium hover:underline" style={{ color: accent }} href={`mailto:${spec.contact_email}`}>Write a note ↗</a>}</section>}
      </main>
      {spec.show_footer !== false && <footer className="mt-14 flex flex-col gap-3 border-t border-white/10 pt-5 text-xs sm:flex-row sm:items-center sm:justify-between" style={{ color: muted }}><span>© {new Date().getFullYear()} {spec.site_name}. {spec.footer_text || 'Made with care.'}</span><div className="flex gap-4">{Object.entries(spec.links || {}).map(([name, url]) => <a key={name} href={url} className="hover:underline">{name}</a>)}</div></footer>}
    </div>
  </div>;
}
