import { useMemo } from 'react';

const escapeStyle = (value = '') => value.replace(/<\/style/gi, '<\\/style');
const escapeScript = (value = '') => value.replace(/<\/script/gi, '<\\/script');

/**
 * Render generated projects inside an opaque-origin iframe. CSP gives the
 * generated page no API, storage, navigation, or general network access.
 */
export default function GeneratedSiteCanvas({ files, title = 'Custom website preview', className = '' }) {
  const srcDoc = useMemo(() => {
    if (!files?.['app.js'] || !files?.['site.css']) return '<!doctype html><html><body>Preview is not ready.</body></html>';
    const nonce = crypto.randomUUID().replaceAll('-', '');
    const policy = `default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline'; img-src data: blob: https://images.unsplash.com https://images.pexels.com; font-src data:; connect-src 'none'; form-action 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'`;
    return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="${policy}"><style>${escapeStyle(files['site.css'])}</style><style>${escapeStyle(files['styles.css'] || '')}</style><title>${title.replace(/[<>]/g, '')}</title></head><body><div id="root"></div><script nonce="${nonce}">${escapeScript(files['app.js'])}</script></body></html>`;
  }, [files, title]);

  return <iframe
    title={title}
    srcDoc={srcDoc}
    sandbox="allow-scripts"
    referrerPolicy="no-referrer"
    className={`block h-full min-h-[620px] w-full border-0 bg-white ${className}`}
  />;
}
