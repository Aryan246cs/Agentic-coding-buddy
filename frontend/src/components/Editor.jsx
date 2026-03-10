import Editor from '@monaco-editor/react';

export default function CodeEditor({ file, content }) {
  const getLanguage = (filename) => {
    if (filename.endsWith('.html')) return 'html';
    if (filename.endsWith('.css')) return 'css';
    if (filename.endsWith('.js')) return 'javascript';
    return 'plaintext';
  };

  return (
    <div className="flex-1 bg-gray-900 flex flex-col">
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-900">
        <h3 className="text-sm font-medium text-gray-300">{file || 'No file selected'}</h3>
      </div>
      <div className="flex-1">
        {content ? (
          <Editor
            height="100%"
            language={getLanguage(file)}
            value={content}
            theme="vs-dark"
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            Select a file to view its content
          </div>
        )}
      </div>
    </div>
  );
}
