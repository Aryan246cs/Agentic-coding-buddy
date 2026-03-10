import { useEffect, useState } from 'react';
import { Monitor } from 'lucide-react';

export default function Preview({ files }) {
  const [srcDoc, setSrcDoc] = useState('');

  useEffect(() => {
    // Find HTML file (could be index.html, templates/index.html, etc.)
    const htmlFile = Object.keys(files).find(f => f.endsWith('.html'));
    
    if (htmlFile) {
      let html = files[htmlFile];
      
      // Find CSS file
      const cssFile = Object.keys(files).find(f => f.endsWith('.css'));
      if (cssFile) {
        const css = files[cssFile];
        // Inject CSS into HTML
        if (html.includes('</head>')) {
          html = html.replace('</head>', `<style>${css}</style></head>`);
        } else {
          html = `<style>${css}</style>` + html;
        }
      }
      
      // Find JS file
      const jsFile = Object.keys(files).find(f => f.endsWith('.js') && !f.includes('node_modules'));
      if (jsFile) {
        const js = files[jsFile];
        // Inject JS into HTML
        if (html.includes('</body>')) {
          html = html.replace('</body>', `<script>${js}</script></body>`);
        } else {
          html = html + `<script>${js}</script>`;
        }
      }
      
      setSrcDoc(html);
    } else {
      setSrcDoc('');
    }
  }, [files]);

  return (
    <div className="flex-1 bg-gray-900 flex flex-col border-l border-gray-800">
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-900 flex items-center gap-2">
        <Monitor className="w-4 h-4 text-gray-400" />
        <h3 className="text-sm font-medium text-gray-300">Live Preview</h3>
      </div>
      <div className="flex-1 bg-white">
        {srcDoc ? (
          <iframe
            srcDoc={srcDoc}
            title="preview"
            sandbox="allow-scripts"
            className="w-full h-full border-0"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 bg-gray-900">
            Generate a project to see preview
          </div>
        )}
      </div>
    </div>
  );
}
