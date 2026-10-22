import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import Chrome from '../components/Chrome';
import SiteCanvas from '../components/SiteCanvas';
import { Alert, Button, Card, Input, PageHeader, Textarea } from '../components/ui';

const fallbackSections = {
  portfolio: [{ key: 'work', heading: 'Selected work', body: 'A few things I am proud to have made.', items: ['Brand identity', 'Digital experiences'] }],
  freelancer: [{ key: 'services', heading: 'How I can help', body: 'Clear thinking and thoughtful work for ambitious people.', items: ['Strategy', 'Design', 'Delivery'] }],
  business: [{ key: 'services', heading: 'What we do', body: 'Good work, close to home, from people who care.', items: ['Our services', 'Our approach'] }],
  event: [{ key: 'schedule', heading: 'The day', body: 'A focused room, useful conversations and practical ideas.', items: ['Talks', 'Workshops'] }],
  personal: [{ key: 'about', heading: 'A little about me', body: 'I make things, learn constantly and enjoy good conversations.', items: [] }],
};

function draftFor(template, name = '') {
  return {
    spec_version: 1, template, theme: 'slate', site_name: name || 'Your name or business',
    tagline: template === 'event' ? 'A day worth making space for.' : 'A clear introduction to what you do.',
    hero_eyebrow: template === 'event' ? 'Save your spot' : 'Thoughtfully made, with intention',
    hero_body: 'Start with a strong point of view, then make every detail your own.', sections: fallbackSections[template],
    contact_email: '', contact_phone: '', location: '', links: {}, cta_label: 'Get in touch',
  };
}

export default function NewSite() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [selected, setSelected] = useState('portfolio');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => { api.templates().then((x) => setTemplates(x.sites)).catch((e) => setError(e.message)); }, []);

  async function create(event) {
    event.preventDefault(); setBusy(true); setError(null);
    try {
      let spec = draftFor(selected, name);
      if (description.trim().length >= 10) {
        const result = await api.planSite(description);
        spec = { ...result.spec, template: selected, site_name: name || result.spec.site_name, sections: result.spec.sections?.length ? result.spec.sections : fallbackSections[selected] };
      }
      const project = await api.createProject({ kind: 'site', name: spec.site_name, source_prompt: description || `Started from ${selected}`, spec });
      navigate(`/projects/${project.id}`);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const preview = draftFor(selected, name);
  return <Chrome wide>
    <PageHeader title="Create a website" subtitle="Pick a strong starting point. You can edit every detail before publishing." />
    {error && <div className="mb-5"><Alert onDismiss={() => setError(null)}>{error}</Alert></div>}
    <div className="grid gap-8 lg:grid-cols-[.92fr_1.08fr]">
      <form onSubmit={create} className="space-y-6">
        <div><p className="text-xs font-semibold uppercase tracking-[.16em] text-violet-300">01 · Choose a direction</p><div className="mt-3 grid gap-3 sm:grid-cols-2">
          {templates.map((item, index) => <button type="button" key={item.key} onClick={() => setSelected(item.key)} className={`group relative min-h-28 rounded-2xl border p-4 text-left transition ${selected === item.key ? 'border-violet-400 bg-violet-400/[.09] shadow-lg shadow-violet-950/20' : 'border-white/10 bg-white/[.025] hover:border-white/25 hover:bg-white/[.05]'}`}>
            <span className={`mb-3 grid h-7 w-7 place-items-center rounded-lg text-xs ${selected === item.key ? 'bg-violet-400/20 text-violet-200' : 'bg-white/[.06] text-slate-400'}`}>0{index + 1}</span>
            <p className="font-medium text-white">{item.name}</p><p className="mt-1 text-xs leading-5 text-slate-400">{item.blurb}</p>
          </button>)}
        </div></div>
        <Card className="p-5"><p className="text-xs font-semibold uppercase tracking-[.16em] text-violet-300">02 · Make it yours</p>
          <label className="mt-4 block text-sm text-slate-200">Name or business<Input className="mt-2" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Anika Studio" required /></label>
          <label className="mt-4 block text-sm text-slate-200">Tell us about it <span className="text-slate-500">(optional for now)</span><Textarea className="mt-2" rows={5} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="A thoughtful interior designer in Mumbai, working on warm homes and small hospitality spaces." /></label>
          <Button className="mt-5 w-full" size="lg" type="submit" loading={busy}>{description.trim().length >= 10 ? 'Create from description' : 'Start with this template'}</Button>
        </Card>
      </form>
      <div className="lg:sticky lg:top-5 lg:self-start"><div className="mb-3 flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[.16em] text-slate-400">Live starting point</p><span className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] capitalize text-slate-400">{selected} · preview</span></div><div className="overflow-hidden rounded-3xl border border-white/10 shadow-2xl shadow-black/40"><SiteCanvas spec={preview} compact /></div><p className="mt-3 text-center text-xs text-slate-500">You can change the layout, colors, words, and page sections next.</p></div>
    </div>
  </Chrome>;
}
