import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import Chrome from '../components/Chrome';
import SiteCanvas from '../components/SiteCanvas';
import { Alert, Button, Card, Input, PageHeader, Select, Textarea } from '../components/ui';

const themes = ['slate', 'ink', 'forest', 'clay', 'indigo', 'sand'];

export default function SiteBuilder({ project, onReload }) {
  const [spec, setSpec] = useState(project.spec);
  const [tab, setTab] = useState('content');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => setSpec(project.spec), [project.spec]);
  const change = (key, value) => setSpec((old) => ({ ...old, [key]: value }));

  async function save() { setBusy(true); setError(null); try { await api.updateProject(project.id, { name: spec.site_name, spec }); setNotice('Draft saved. Your public site has not changed.'); onReload(); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  async function publish() { await save(); setBusy(true); try { await api.publish(project.id); setNotice('Published — your new site is live.'); onReload(); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  async function unpublish() { setBusy(true); try { await api.unpublish(project.id); setNotice('Taken offline.'); onReload(); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  function section(index, key, value) { setSpec((old) => ({ ...old, sections: old.sections.map((s, i) => i === index ? { ...s, [key]: value } : s) })); }

  const publicUrl = `${window.location.origin}${project.public_path}`;
  return <Chrome wide>
    <PageHeader title={spec.site_name || project.name} subtitle={project.is_published ? <a className="text-cyan-300 underline" href={project.public_path} target="_blank" rel="noreferrer">{publicUrl}</a> : 'Draft · only you can see this'} actions={<><Link to="/dashboard" className="text-sm text-slate-400 hover:text-white">All projects</Link>{project.is_published && <Button variant="secondary" onClick={unpublish}>Take offline</Button>}<Button variant="secondary" onClick={save} loading={busy}>Save draft</Button><Button onClick={publish} loading={busy}>{project.is_published ? 'Publish changes' : 'Publish website'}</Button></>} />
    {notice && <div className="mb-4"><Alert tone="good" onDismiss={() => setNotice(null)}>{notice}</Alert></div>}{error && <div className="mb-4"><Alert onDismiss={() => setError(null)}>{error}</Alert></div>}
    {project.has_unpublished_changes && <div className="mb-4"><Alert tone="warn">You have unpublished changes. Visitors are still seeing the previous version.</Alert></div>}
    <div className="grid gap-6 xl:grid-cols-[390px_1fr]">
      <Card className="h-fit p-3 xl:sticky xl:top-5"><div className="flex gap-1 border-b border-white/10 p-1">{[['content','Content'],['style','Style'],['settings','Settings']].map(([key,label]) => <button key={key} onClick={() => setTab(key)} className={`flex-1 rounded-lg px-2 py-2 text-sm ${tab === key ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white'}`}>{label}</button>)}</div>
        <div className="space-y-4 p-3">{tab === 'content' && <><label className="block text-sm text-slate-300">Site name<Input className="mt-1.5" value={spec.site_name} onChange={(e) => change('site_name', e.target.value)} /></label><label className="block text-sm text-slate-300">Tagline<Input className="mt-1.5" value={spec.tagline} onChange={(e) => change('tagline', e.target.value)} /></label><label className="block text-sm text-slate-300">Intro<Textarea className="mt-1.5" value={spec.hero_body || ''} onChange={(e) => change('hero_body', e.target.value)} /></label>{spec.sections.map((s, i) => <div className="border-t border-white/10 pt-4" key={s.key}><p className="mb-2 text-xs font-semibold uppercase tracking-wider text-violet-300">Section {i + 1}</p><Input value={s.heading} onChange={(e) => section(i, 'heading', e.target.value)} /><Textarea className="mt-2" value={s.body || ''} onChange={(e) => section(i, 'body', e.target.value)} /></div>)}</>}
        {tab === 'style' && <><label className="block text-sm text-slate-300">Template<Select className="mt-1.5" value={spec.template} onChange={(e) => change('template', e.target.value)}><option value="portfolio">Portfolio</option><option value="freelancer">Freelancer</option><option value="business">Local business</option><option value="event">Event</option><option value="personal">Personal</option></Select></label><p className="text-sm text-slate-300">Theme</p><div className="grid grid-cols-3 gap-2">{themes.map((theme) => <button key={theme} onClick={() => change('theme', theme)} className={`rounded-xl border px-2 py-3 text-xs capitalize ${spec.theme === theme ? 'border-violet-400 bg-violet-400/15 text-white' : 'border-white/10 text-slate-400'}`}>{theme}</button>)}</div></>}
        {tab === 'settings' && <><label className="block text-sm text-slate-300">Email<Input className="mt-1.5" value={spec.contact_email || ''} onChange={(e) => change('contact_email', e.target.value)} placeholder="hello@example.com" /></label><label className="block text-sm text-slate-300">Phone<Input className="mt-1.5" value={spec.contact_phone || ''} onChange={(e) => change('contact_phone', e.target.value)} /></label><label className="block text-sm text-slate-300">Location<Input className="mt-1.5" value={spec.location || ''} onChange={(e) => change('location', e.target.value)} /></label><label className="block text-sm text-slate-300">Button label<Input className="mt-1.5" value={spec.cta_label || ''} onChange={(e) => change('cta_label', e.target.value)} /></label></>}</div>
      </Card>
      <div><div className="mb-3 flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[.16em] text-slate-400">Live preview</p><span className="text-xs text-slate-500">Desktop</span></div><div className="overflow-hidden rounded-3xl border border-white/10 shadow-2xl shadow-black/40"><SiteCanvas spec={spec} compact /></div></div>
    </div>
  </Chrome>;
}
