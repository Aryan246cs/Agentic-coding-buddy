/** A safe, reusable website renderer. It renders SiteSpec data, never user HTML. */

const palettes = {
  slate: ['#0a0a0c', '#f8fafc', '#a1a1aa', '#a78bfa'],
  ink: ['#09090b', '#fafafa', '#a1a1aa', '#22d3ee'],
  forest: ['#071611', '#ecfdf5', '#9ad5c0', '#34d399'],
  clay: ['#20110d', '#fff7ed', '#f1bda0', '#fb923c'],
  indigo: ['#0e1024', '#eef2ff', '#bac5ff', '#818cf8'],
  sand: ['#18150f', '#fffbeb', '#e2d3b0', '#fbbf24'],
};

function Contact({ spec, muted }) {
  if (!spec.contact_email && !spec.contact_phone && !spec.location) return null;
  return <div className="mt-10 flex flex-wrap gap-x-5 gap-y-2 text-sm" style={{ color: muted }}>
    {spec.contact_email && <a href={`mailto:${spec.contact_email}`}>{spec.contact_email}</a>}
    {spec.contact_phone && <span>{spec.contact_phone}</span>}
    {spec.location && <span>{spec.location}</span>}
  </div>;
}

function Section({ section, text, muted, accent, style = 'list' }) {
  return <section className={style === 'card' ? 'rounded-2xl border border-white/10 p-5' : 'border-t border-white/10 py-7'}>
    <h2 className="text-xl font-semibold" style={{ color: text }}>{section.heading}</h2>
    {section.body && <p className="mt-2 text-sm leading-6" style={{ color: muted }}>{section.body}</p>}
    {section.items?.length > 0 && <div className={style === 'card' ? 'mt-5 grid gap-3 sm:grid-cols-2' : 'mt-4 flex flex-wrap gap-2'}>
      {section.items.map((item) => <span key={item} className="rounded-full border border-white/10 px-3 py-1.5 text-sm" style={{ color: accent }}>{item}</span>)}
    </div>}
  </section>;
}

export default function SiteCanvas({ spec, compact = false }) {
  const [background, text, muted, accent] = palettes[spec.theme] || palettes.slate;
  const sections = spec.sections || [];
  const root = { background, color: text, minHeight: compact ? 520 : '100vh' };
  const wrap = compact ? 'p-7 sm:p-10' : 'px-6 py-16 sm:px-10 sm:py-24';
  const isPortfolio = spec.template === 'portfolio';
  const isEvent = spec.template === 'event';
  const isBusiness = spec.template === 'business';
  const isPersonal = spec.template === 'personal';
  const isFreelancer = spec.template === 'freelancer';

  return <div style={root} className={`${wrap} overflow-hidden`}>
    <div className="mx-auto max-w-5xl">
      {isPortfolio && <>
        <p className="text-xs font-semibold uppercase tracking-[.24em]" style={{ color: accent }}>Selected work · 2026</p>
        <h1 className="mt-6 max-w-3xl text-4xl font-semibold leading-[.98] tracking-tight sm:text-6xl">{spec.site_name}</h1>
        <p className="mt-5 max-w-xl text-lg" style={{ color: muted }}>{spec.tagline}</p>
        <div className="mt-12 grid gap-4 sm:grid-cols-2">{sections.map((s) => <Section key={s.key} section={s} text={text} muted={muted} accent={accent} style="card" />)}</div>
      </>}

      {isEvent && <div className="text-center">
        <p className="text-sm font-medium uppercase tracking-[.2em]" style={{ color: accent }}>Save your spot</p>
        <h1 className="mx-auto mt-5 max-w-3xl text-5xl font-semibold leading-none tracking-tight sm:text-7xl">{spec.site_name}</h1>
        <p className="mx-auto mt-6 max-w-xl text-xl" style={{ color: muted }}>{spec.tagline}</p>
        <button className="mt-9 rounded-full px-6 py-3 text-sm font-semibold" style={{ background: accent, color: background }}>{spec.cta_label || 'Reserve a place'}</button>
        <div className="mx-auto mt-14 max-w-3xl text-left">{sections.map((s) => <Section key={s.key} section={s} text={text} muted={muted} accent={accent} />)}</div>
      </div>}

      {isBusiness && <>
        <div className="flex items-center justify-between border-b border-white/10 pb-5 text-sm"><strong>{spec.site_name}</strong><span style={{ color: accent }}>Open today</span></div>
        <div className="grid gap-12 py-14 md:grid-cols-[1.2fr_.8fr] md:items-end">
          <div><p className="text-sm font-medium" style={{ color: accent }}>LOCAL, PERSONAL, HERE FOR YOU</p><h1 className="mt-4 text-5xl font-semibold leading-none tracking-tight">{spec.tagline}</h1><p className="mt-6 max-w-lg leading-7" style={{ color: muted }}>{spec.hero_body}</p></div>
          <div className="rounded-3xl border border-white/10 p-6"><p className="text-sm" style={{ color: muted }}>Visit or get in touch</p><Contact spec={spec} muted={text} /></div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">{sections.map((s) => <Section key={s.key} section={s} text={text} muted={muted} accent={accent} style="card" />)}</div>
      </>}

      {isPersonal && <div className="mx-auto max-w-2xl py-8 sm:py-16">
        <p className="text-sm font-medium" style={{ color: accent }}>HELLO, I’M</p><h1 className="mt-3 text-5xl font-semibold tracking-tight sm:text-7xl">{spec.site_name}</h1><p className="mt-6 text-xl" style={{ color: muted }}>{spec.tagline}</p><p className="mt-8 leading-7" style={{ color: muted }}>{spec.hero_body}</p>
        <div className="mt-12">{sections.map((s) => <Section key={s.key} section={s} text={text} muted={muted} accent={accent} />)}</div><Contact spec={spec} muted={muted} />
      </div>}

      {isFreelancer && <>
        <div className="grid gap-10 border-b border-white/10 pb-12 md:grid-cols-[1.25fr_.75fr] md:items-end"><div><p className="text-sm font-semibold uppercase tracking-[.18em]" style={{ color: accent }}>Independent · Available</p><h1 className="mt-5 text-5xl font-semibold leading-none tracking-tight sm:text-6xl">{spec.site_name}</h1><p className="mt-5 max-w-xl text-xl" style={{ color: muted }}>{spec.tagline}</p></div><div className="rounded-2xl border border-white/10 p-5"><p className="text-sm leading-6" style={{ color: muted }}>{spec.hero_body}</p><button className="mt-5 w-full rounded-xl py-3 text-sm font-semibold" style={{ background: accent, color: background }}>{spec.cta_label || 'Start a conversation'}</button></div></div>
        <div className="mt-10 grid gap-4 md:grid-cols-2">{sections.map((s) => <Section key={s.key} section={s} text={text} muted={muted} accent={accent} style="card" />)}</div>
      </>}

      {!isPortfolio && !isEvent && !isBusiness && !isPersonal && !isFreelancer && <>
        <h1>{spec.site_name}</h1><p>{spec.tagline}</p>
      </>}
      {isPortfolio && <Contact spec={spec} muted={muted} />}
      {spec.links && <footer className="mt-12 flex gap-4 text-xs" style={{ color: muted }}>{Object.entries(spec.links).map(([name, url]) => <a key={name} href={url}>{name}</a>)}</footer>}
    </div>
  </div>;
}
