import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { api } from '../lib/api';
import Chrome from '../components/Chrome';
import GeneratedSiteCanvas from '../components/GeneratedSiteCanvas';
import { Alert, Button, Input, PageHeader, Textarea } from '../components/ui';

const sourceNames = ['App.tsx', 'styles.css'];
export default function CustomSiteStudio({ project, onReload }) {
  const [view, setView] = useState('preview');
  const [activeFile, setActiveFile] = useState('App.tsx');
  const [source, setSource] = useState(() => ({ 'App.tsx': project.files?.['App.tsx'] || '', 'styles.css': project.files?.['styles.css'] || '' }));
  const [revisions, setRevisions] = useState([]);
  const [revisionPrompt, setRevisionPrompt] = useState('');
  const [slug, setSlug] = useState(project.slug);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    api.siteRevisions(project.id).then((result) => setRevisions(result.revisions)).catch(() => {});
  }, [project.id, project.updated_at]);

  const dirty = source['App.tsx'] !== project.files?.['App.tsx'] || source['styles.css'] !== project.files?.['styles.css'];
  async function saveFiles(nextSource = source, label = 'Draft saved') {
    setBusy(true); setError(null);
    try {
      await api.updateProject(project.id, { name: project.name, slug, spec: project.spec, files: nextSource });
      setNotice(label); await onReload();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  async function reviseWithAI(event) {
    event.preventDefault();
    const instruction = revisionPrompt.trim();
    if (!instruction) return;
    setBusy(true); setError(null); setNotice('The planner, designer, builder, and reviewer are working on your changes…');
    try {
      const brief = `${project.source_prompt || `Build a website for ${project.name}.`}\n\nRequested changes:\n${instruction}`;
      const result = await api.planCustomSite(brief);
      await api.updateProject(project.id, { name: result.spec.site_name || project.name, slug, spec: result.spec, files: { 'App.tsx': result.files['App.tsx'], 'styles.css': result.files['styles.css'] } });
      setRevisionPrompt(''); setNotice('Your new version passed the React and Tailwind build checks.');
      await onReload();
    } catch (err) { setError(err.message); setNotice(null); }
    finally { setBusy(false); }
  }
  async function restoreRevision(revisionId) {
    setBusy(true); setError(null);
    try { await api.restoreSiteRevision(project.id, revisionId); setNotice('Version restored as a new draft revision.'); await onReload(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  async function publish() {
    setBusy(true); setError(null);
    try {
      if (dirty) await api.updateProject(project.id, { name: project.name, slug, spec: project.spec, files: source });
      await api.publish(project.id); setNotice('Published — the new version is live.'); await onReload();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  const url = `${window.location.origin}/s/${slug}`;
  return <Chrome wide>
    <PageHeader title={project.name} subtitle={project.is_published ? <a className="text-cyan-300 underline" href={project.public_path} target="_blank" rel="noreferrer">{url}</a> : 'Custom React website · private draft'} actions={<><Link to="/dashboard" className="px-2 py-2 text-sm text-slate-400 hover:text-white">All projects</Link><Button variant="secondary" onClick={() => saveFiles(source)} loading={busy}>{dirty ? 'Build & save' : 'Save draft'}</Button><Button onClick={publish} loading={busy}>{project.is_published ? 'Publish changes' : 'Publish website'}</Button></>} />
    {notice && <div className="mb-4"><Alert tone="good" onDismiss={() => setNotice(null)}>{notice}</Alert></div>}
    {error && <div className="mb-4"><Alert onDismiss={() => setError(null)}>{error}</Alert></div>}
    {project.has_unpublished_changes && <div className="mb-4"><Alert tone="warn">Your draft is newer than the live website.</Alert></div>}
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[.03] p-3">
      <div className="flex gap-1">{[['preview','Preview'],['code','Code'],['history','History']].map(([key,label]) => <button key={key} onClick={() => setView(key)} className={`rounded-lg px-4 py-2 text-sm ${view === key ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white'}`}>{label}</button>)}</div>
      {view === 'code' && <span className={`text-xs ${dirty ? 'text-amber-300' : 'text-emerald-300'}`}>{dirty ? 'Unsaved source changes' : 'Build verified'}</span>}
    </div>
    {view === 'preview' && <div className="overflow-hidden rounded-3xl border border-white/10 bg-white shadow-2xl shadow-black/30"><GeneratedSiteCanvas files={project.files} title={`${project.name} preview`} /></div>}
    {view === 'code' && <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#0b0d13]"><div className="flex items-center justify-between border-b border-white/10 px-3"><div className="flex gap-1">{sourceNames.map((file) => <button key={file} onClick={() => setActiveFile(file)} className={`border-b-2 px-3 py-3 text-xs ${activeFile === file ? 'border-violet-400 text-white' : 'border-transparent text-slate-500'}`}>{file}</button>)}</div><Button size="sm" onClick={() => saveFiles(source)} loading={busy}>Build & save</Button></div><div className="h-[70vh] min-h-[520px]"><Editor height="100%" language={activeFile === 'App.tsx' ? 'typescript' : 'css'} theme="vs-dark" value={source[activeFile]} onChange={(value) => setSource((old) => ({ ...old, [activeFile]: value || '' }))} options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: 'on', automaticLayout: true, padding: { top: 16 }, scrollBeyondLastLine: false }} /></div><div className="border-t border-white/10 p-4"><form onSubmit={reviseWithAI} className="flex flex-col gap-3 sm:flex-row"><Textarea rows={2} value={revisionPrompt} onChange={(e) => setRevisionPrompt(e.target.value)} placeholder="Ask AI to refine this site — e.g. make the hero more editorial and add a testimonials section." className="flex-1" /><Button type="submit" variant="secondary" disabled={!revisionPrompt.trim()} loading={busy}>Revise with AI</Button></form></div></div>}
    {view === 'history' && <div className="space-y-3">{revisions.length === 0 ? <div className="rounded-2xl border border-dashed border-white/15 p-10 text-center text-sm text-slate-400">Your saved website versions will show up here.</div> : revisions.map((item) => <div key={item.id} className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/[.03] p-4"><div><p className="font-medium text-white">Version {item.version} · {item.label}</p><p className="mt-1 text-xs text-slate-500">{new Date(item.created_at).toLocaleString()} {item.prompt ? `· ${item.prompt.slice(0, 120)}` : ''}</p></div><Button variant="secondary" size="sm" onClick={() => restoreRevision(item.id)} loading={busy}>Restore this version</Button></div>)}</div>}
    <div className="mt-6 grid gap-4 md:grid-cols-2"><form onSubmit={(e) => { e.preventDefault(); saveFiles(); }} className="rounded-2xl border border-white/10 bg-white/[.025] p-5"><p className="text-sm font-semibold text-white">Ask the AI team for a change</p><p className="mt-1 text-xs text-slate-500">Your original brief stays attached to every iteration.</p><Textarea className="mt-3" rows={3} value={revisionPrompt} onChange={(e) => setRevisionPrompt(e.target.value)} placeholder="Add a pricing section and change the colors to warm cream and forest green." /><Button className="mt-3" type="button" onClick={reviseWithAI} disabled={!revisionPrompt.trim()} loading={busy}>Generate a revision</Button></form><div className="rounded-2xl border border-white/10 bg-white/[.025] p-5"><p className="text-sm font-semibold text-white">Website settings</p><label className="mt-3 block text-sm text-slate-300">Public address<Input className="mt-1.5" value={slug} onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))} /></label><p className="mt-2 text-xs text-slate-500">{url}</p><p className="mt-3 text-xs text-slate-500">React + TypeScript · Tailwind CSS · isolated preview</p></div></div>
  </Chrome>;
}
