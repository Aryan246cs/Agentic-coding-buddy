import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

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
      setTemplates(templateList.apps);
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
      window.location.href = `/projects/${project.id}`;
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
      <PageHeader
        title="Your apps"
        subtitle="Everything you have built."
        actions={<LinkButton to="/new">Build something new</LinkButton>}
      />

      {error && (
        <div className="mb-6">
          <Alert onDismiss={() => setError(null)}>{error}</Alert>
        </div>
      )}

      {projects.length === 0 ? (
        <EmptyState
          title="Nothing here yet"
          action={<LinkButton to="/new">Describe what you need</LinkButton>}
        >
          Tell us how something works in your team — who submits it and who approves
          it — and we will build it.
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

      {templates.length > 0 && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Or start from one of these
          </h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {templates.map((template) => (
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
