/**
 * A published website.
 *
 * Rendered from the site spec — never from generated markup. That is what
 * makes it safe to serve on our own domain and fast enough to cache.
 */

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { runtimeApi } from '../lib/api';
import { Card, Loading } from '../components/ui';

/** Each theme is a background, a text colour and one accent. */
const THEMES = {
  slate: { page: 'bg-white text-slate-900', muted: 'text-slate-600', accent: 'bg-slate-900 text-white', rule: 'border-slate-200' },
  ink: { page: 'bg-slate-950 text-slate-50', muted: 'text-slate-400', accent: 'bg-white text-slate-900', rule: 'border-slate-800' },
  forest: { page: 'bg-emerald-50 text-emerald-950', muted: 'text-emerald-800', accent: 'bg-emerald-800 text-white', rule: 'border-emerald-200' },
  clay: { page: 'bg-orange-50 text-stone-900', muted: 'text-stone-600', accent: 'bg-orange-700 text-white', rule: 'border-orange-200' },
  indigo: { page: 'bg-indigo-50 text-indigo-950', muted: 'text-indigo-800', accent: 'bg-indigo-700 text-white', rule: 'border-indigo-200' },
  sand: { page: 'bg-amber-50 text-stone-900', muted: 'text-stone-600', accent: 'bg-stone-800 text-white', rule: 'border-amber-200' },
};

export default function PublishedSite() {
  const { slug } = useParams();
  const [site, setSite] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    runtimeApi
      .site(slug)
      .then(setSite)
      .catch((err) => setError(err.message));
  }, [slug]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <Card className="max-w-md p-8 text-center">
          <p className="text-lg font-medium text-slate-900">Nothing here</p>
          <p className="mt-2 text-sm text-slate-600">{error}</p>
        </Card>
      </div>
    );
  }

  if (!site) return <Loading />;

  const spec = site.spec;
  const theme = THEMES[spec.theme] || THEMES.slate;

  // Templates differ in emphasis rather than structure: a portfolio leads with
  // the work, a business page leads with where to find it.
  const centred = spec.template === 'personal' || spec.template === 'event';

  return (
    <div className={`min-h-screen ${theme.page}`}>
      <header className={`mx-auto max-w-3xl px-6 pb-12 pt-20 ${centred ? 'text-center' : ''}`}>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          {spec.site_name}
        </h1>
        <p className={`mt-3 text-xl ${theme.muted}`}>{spec.tagline}</p>
        {spec.hero_body && (
          <p className={`mt-6 text-lg leading-relaxed ${theme.muted}`}>{spec.hero_body}</p>
        )}
        {spec.cta_label && spec.contact_email && (
          <a
            href={`mailto:${spec.contact_email}`}
            className={`mt-8 inline-block rounded-lg px-5 py-2.5 font-medium ${theme.accent}`}
          >
            {spec.cta_label}
          </a>
        )}
      </header>

      <main className="mx-auto max-w-3xl px-6 pb-20">
        {spec.sections?.map((section) => (
          <section key={section.key} className={`border-t py-10 ${theme.rule}`}>
            <h2 className="text-2xl font-semibold tracking-tight">{section.heading}</h2>
            {section.body && (
              <p className={`mt-3 leading-relaxed ${theme.muted}`}>{section.body}</p>
            )}
            {section.items?.length > 0 && (
              <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                {section.items.map((item) => (
                  <li key={item} className={`flex gap-2 ${theme.muted}`}>
                    <span aria-hidden>·</span>
                    {item}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}

        {(spec.contact_email || spec.contact_phone || spec.location) && (
          <section className={`border-t py-10 ${theme.rule}`}>
            <h2 className="text-2xl font-semibold tracking-tight">Get in touch</h2>
            <div className={`mt-3 space-y-1 ${theme.muted}`}>
              {spec.contact_email && (
                <p>
                  <a href={`mailto:${spec.contact_email}`} className="underline">
                    {spec.contact_email}
                  </a>
                </p>
              )}
              {spec.contact_phone && <p>{spec.contact_phone}</p>}
              {spec.location && <p>{spec.location}</p>}
            </div>
            {Object.keys(spec.links || {}).length > 0 && (
              <div className="mt-4 flex flex-wrap gap-4">
                {Object.entries(spec.links).map(([name, url]) => (
                  <a key={name} href={url} className={`underline ${theme.muted}`}>
                    {name}
                  </a>
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      <footer className={`border-t py-6 ${theme.rule}`}>
        <p className={`mx-auto max-w-3xl px-6 text-sm ${theme.muted}`}>
          Made with Sequence
        </p>
      </footer>
    </div>
  );
}
