import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Blocks, Sparkles } from 'lucide-react';
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
  const sections = fallbackSections[template] || [{ key: 'highlights', heading: 'A few things to know', body: 'The details that make this yours.', items: ['Our story', 'What we offer'] }];
  return {
    spec_version: 1, template, theme: 'slate', site_name: name || 'Your name or business',
    tagline: ['event', 'wedding'].includes(template) ? 'A day worth making space for.' : 'A clear introduction to what you do.',
    hero_eyebrow: ['event', 'wedding'].includes(template) ? 'Save your spot' : 'Thoughtfully made, with intention',
    hero_body: 'Start with a strong point of view, then make every detail your own.', sections,
    contact_email: '', contact_phone: '', location: '', links: {}, cta_label: 'Get in touch',
  };
}
const ideas = [
  { label: 'Architecture portfolio', text: 'A small, image-led architecture portfolio. Warm white, olive and charcoal. Editorial type, large photography, project cards, about and contact.' },
  { label: 'Neighborhood bakery', text: 'A lively neighborhood bakery site in soft butter yellow and cherry red, with menu, opening hours, location, and a pre-order button.' },
  { label: 'Meditation retreat', text: 'A calm landing page for a meditation retreat. Forest green and sand colors, schedule, instructors, venue, testimonials, and booking CTA.' },
];
export default function NewSite() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [mode, setMode] = useState('');
  const [selected, setSelected] = useState('portfolio');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function loadTemplates() {
    if (templates.length) return;
    try { const result = await api.templates(); setTemplates(result.sites || []); }
    catch (err) { setError(err.message); }
  }
  function chooseMode(next) {
    setMode(next);
    if (next === 'template') loadTemplates();
    setError(null);
  }
  async function create(event) {
    event.preventDefault(); setBusy(true); setError(null);
    try {
      let spec;
      let files;
      if (mode === 'custom') {
        const result = await api.planCustomSite(`Website name: ${name}\n\n${description}`);
        spec = result.spec; files = { 'App.tsx': result.files['App.tsx'], 'styles.css': result.files['styles.css'] };
      } else {
        spec = draftFor(selected, name);
        if (description.trim().length >= 10) {
          const result = await api.planSite(description);
          spec = { ...result.spec, template: selected, site_name: name || result.spec.site_name, sections: result.spec.sections?.length ? result.spec.sections : fallbackSections[selected] };
        }
      }
      const project = await api.createProject({ kind: 'site', name: name || spec.site_name, source_prompt: description || (mode === 'template' ? `Started from ${selected}` : ''), spec, ...(files ? { files } : {}) });
      navigate(`/projects/${project.id}`);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  const preview = draftFor(selected, name);
  const hasName = name.trim().length > 0;
  return <Chrome wide>
    <PageHeader title="Build a website" subtitle="Start with a polished template, or describe something that’s entirely yours." />
    {error && <div className="mb-5"><Alert onDismiss={() => setError(null)}>{error}</Alert></div>}
    <div className="mb-7 grid gap-4 md:grid-cols-2">
      <button onClick={() => chooseMode('template')} className={`rounded-2xl border p-5 text-left transition ${mode === 'template' ? 'border-violet-400/70 bg-violet-400/[.08]' : 'border-white/10 bg-white/[.025] hover:border-white/25 hover:bg-white/[.045]'}`}>
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/[.07] text-violet-200"><Blocks size={20} /></span><h2 className="mt-4 text-lg font-semibold text-white">Use a template</h2><p className="mt-1 text-sm leading-6 text-slate-400">Pick a ready-made direction and customize the layout, sections, colors, and content.</p>
      </button>
      <button onClick={() => chooseMode('custom')} className={`rounded-2xl border p-5 text-left transition ${mode === 'custom' ? 'border-cyan-300/60 bg-cyan-300/[.06]' : 'border-white/10 bg-white/[.025] hover:border-white/25 hover:bg-white/[.045]'}`}>
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-300/10 text-cyan-200"><Sparkles size={20} /></span><h2 className="mt-4 text-lg font-semibold text-white">Make a custom website with AI</h2><p className="mt-1 text-sm leading-6 text-slate-400">Describe the style and sections you want. Our AI team plans, designs, writes, reviews, and build-checks a React site.</p>
      </button>
    </div>
    {mode && <div className="grid gap-8 lg:grid-cols-[.92fr_1.08fr]">
      <form onSubmit={create} className="space-y-6">
        {mode === 'template' ? <div><div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[.16em] text-violet-300">01 · Choose a starting point</p><button type="button" onClick={() => chooseMode('custom')} className="text-xs text-slate-400 hover:text-white">Switch to custom AI →</button></div><div className="mt-3 grid gap-3 sm:grid-cols-2">
          {templates.map((item, index) => <button type="button" key={item.key} onClick={() => setSelected(item.key)} className={`min-h-28 rounded-2xl border p-4 text-left transition ${selected === item.key ? 'border-violet-400 bg-violet-400/[.09]' : 'border-white/10 bg-white/[.025] hover:border-white/25'}`}><span className={`mb-3 grid h-7 w-7 place-items-center rounded-lg text-xs ${selected === item.key ? 'bg-violet-400/20 text-violet-200' : 'bg-white/[.06] text-slate-400'}`}>0{index + 1}</span><p className="font-medium text-white">{item.name}</p><p className="mt-1 text-xs leading-5 text-slate-400">{item.blurb}</p></button>)}
        </div></div> : <div><div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[.16em] text-cyan-200">01 · Describe your vision</p><button type="button" onClick={() => chooseMode('template')} className="text-xs text-slate-400 hover:text-white">Browse templates →</button></div><label className="mt-3 block text-sm text-slate-200">What should the site look and feel like?<Textarea className="mt-2" rows={8} required minLength={20} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Tell us the business, who the site is for, the colors, mood, layout, sections, and what visitors should do. The more detail, the more personal the result." /></label><p className="mt-2 text-xs text-slate-500">Include color palette, design references, hero, cards, sections, and any interactions you have in mind.</p><div className="mt-4 flex flex-wrap gap-2">{ideas.map((idea) => <button type="button" key={idea.label} onClick={() => setDescription(idea.text)} className="rounded-full border border-white/10 px-3 py-1.5 text-left text-[11px] text-slate-400 hover:border-cyan-200/30 hover:text-white">{idea.label}</button>)}</div></div>}
        <Card className="p-5"><p className="text-xs font-semibold uppercase tracking-[.16em] text-violet-300">02 · Make it yours</p><label className="mt-4 block text-sm text-slate-200">Website name<Input className="mt-2" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Anika Studio" required /></label>{mode === 'template' && <label className="mt-4 block text-sm text-slate-200">Tell us about it <span className="text-slate-500">(optional)</span><Textarea className="mt-2" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="A thoughtful interior designer in Mumbai, working on warm homes and small hospitality spaces." /></label>}<Button className="mt-5 w-full" size="lg" type="submit" loading={busy} disabled={!hasName || (mode === 'custom' && description.trim().length < 20)}>{busy ? 'Your AI team is building…' : mode === 'custom' ? 'Plan, design & build my site' : 'Start with this template'}</Button><p className="mt-3 text-center text-xs text-slate-500">Custom builds pass a React and Tailwind compilation check before opening in the editor.</p></Card>
      </form>
      <div className="lg:sticky lg:top-5 lg:self-start"><div className="mb-3 flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[.16em] text-slate-400">{mode === 'custom' ? 'Your build workspace' : 'Live starting point'}</p><span className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] capitalize text-slate-400">{mode === 'custom' ? 'React · Tailwind' : `${selected} · template`}</span></div><div className="overflow-hidden rounded-3xl border border-white/10 shadow-2xl shadow-black/40">{mode === 'custom' ? <div className="grid min-h-[560px] place-items-center bg-[#0b0d13] p-8 text-center"><div className="max-w-sm"><span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-violet-300/20 bg-violet-300/10 text-violet-200"><Sparkles size={24} /></span><p className="mt-5 text-lg font-medium text-white">A website made for your brief</p><p className="mt-2 text-sm leading-6 text-slate-400">Once the AI team finishes the design and build checks, you’ll land in a live code editor with an isolated preview.</p></div></div> : <SiteCanvas spec={preview} compact />}</div><p className="mt-3 text-center text-xs text-slate-500">{mode === 'custom' ? 'Your source files and every saved build will stay in this project.' : 'You can change the layout, colors, words, and page sections next.'}</p></div>
    </div>}
  </Chrome>;
}
