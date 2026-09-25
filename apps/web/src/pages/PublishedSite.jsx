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
import SiteCanvas from '../components/SiteCanvas';

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

  return <SiteCanvas spec={site.spec} />;
}
