import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { api } from '../lib/api';
import Chrome from '../components/Chrome';
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Loading,
  LinkButton,
  PageHeader,
  StatusBadge,
} from '../components/ui';

export default function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(null);

  async function load() {
    try {
      const [projectList, templateList] = await Promise.all([
        api.listProjects(),
        api.templates(),
      ]);
      setProjects(projectList.projects);
      setTemplates(templateList);
    } catch (err) {
      setError(err.message);
      setProjects([]);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function startFromTemplate(key) {
    setStarting(key);
    setError(null);
    try {
      const project = await api.createFromTemplate(key);
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(err.message);
      setStarting(null);
    }
  }

  async function remove(project) {
    if (!window.confirm(`Delete "${project.name}"? This cannot be undone.`)) return;
    try {
      await api.deleteProject(project.id);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (projects === null) return <Loading />;

  return (
    <Chrome>
      <PageHeader title="Your workspace" subtitle="Websites for the world. Workflows for the work behind it." actions={<div className="flex gap-2"><LinkButton to="/new/site" variant="secondary">New website</LinkButton><LinkButton to="/new">New workflow</LinkButton></div>} />

      <div className="mb-8 grid gap-3 md:grid-cols-2">
        <Link to="/new/site" className="group rounded-2xl border border-cyan-300/20 bg-gradient-to-br from-cyan-400/10 to-transparent p-5 transition hover:-translate-y-0.5 hover:border-cyan-300/45">
          <span className="text-xs font-semibold uppercase tracking-[.16em] text-cyan-300">Public presence</span><h2 className="mt-2 text-lg font-semibold text-white">Build a website <span className="inline-block transition group-hover:translate-x-1">→</span></h2><p className="mt-1 text-sm text-slate-400">Choose a refined template, make it yours, and publish a link.</p>
        </Link>
        <Link to="/new" className="group rounded-2xl border border-violet-300/20 bg-gradient-to-br from-violet-400/10 to-transparent p-5 transition hover:-translate-y-0.5 hover:border-violet-300/45">
          <span className="text-xs font-semibold uppercase tracking-[.16em] text-violet-300">Operations</span><h2 className="mt-2 text-lg font-semibold text-white">Build a workflow <span className="inline-block transition group-hover:translate-x-1">→</span></h2><p className="mt-1 text-sm text-slate-400">Turn requests and approvals into a working team system.</p>
        </Link>
      </div>

      {error && (
        <div className="mb-6">
          <Alert onDismiss={() => setError(null)}>{error}</Alert>
        </div>
      )}

      {projects.length === 0 ? (
        <EmptyState
          title="Your workspace is ready"
          action={<div className="flex justify-center gap-2"><LinkButton to="/new/site" variant="secondary">Create a website</LinkButton><LinkButton to="/new">Create a workflow</LinkButton></div>}
        >
          Start with a public website or the workflow that keeps your team moving.
        </EmptyState>
      ) : (
        <div className="space-y-3">
          {projects.map((project) => (
            <Card key={project.id} className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/projects/${project.id}`}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {project.name}
                    </Link>
                    <StatusBadge status={project.status} />
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${project.kind === 'site' ? 'bg-cyan-400/10 text-cyan-200' : 'bg-violet-400/10 text-violet-200'}`}>{project.kind === 'site' ? 'Website' : 'Workflow'}</span>
                  </div>
                  <p className="mt-1 truncate text-sm text-slate-500">
                    {project.is_published ? (
                      <a
                        href={project.public_path}
                        target="_blank"
                        rel="noreferrer"
                        className="hover:underline"
                      >
                        {window.location.origin}
                        {project.public_path}
                      </a>
                    ) : (
                      'Not published yet'
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <LinkButton to={`/projects/${project.id}`} variant="secondary" size="sm">
                    Open
                  </LinkButton>
                  <Button variant="danger" size="sm" onClick={() => remove(project)}>
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {templates.apps?.length > 0 && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Workflow templates
          </h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {templates.apps.map((template) => (
              <Card key={template.key} className="flex flex-col p-4">
                <h3 className="font-medium text-slate-900">{template.name}</h3>
                <p className="mt-1.5 flex-1 text-sm leading-relaxed text-slate-600">
                  {template.blurb}
                </p>
                <p className="mt-3 text-xs text-slate-500">
                  {template.roles.join(' · ')}
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  loading={starting === template.key}
                  onClick={() => startFromTemplate(template.key)}
                >
                  Use this
                </Button>
              </Card>
            ))}
          </div>
        </section>
      )}
    </Chrome>
  );
}
