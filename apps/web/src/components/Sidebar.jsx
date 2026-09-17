import { FileCode, FileText, Braces, File } from 'lucide-react';

const getFileIcon = (filename) => {
  if (filename.endsWith('.html')) return <FileCode className="w-4 h-4 text-orange-400" />;
  if (filename.endsWith('.css')) return <FileText className="w-4 h-4 text-blue-400" />;
  if (filename.endsWith('.js')) return <Braces className="w-4 h-4 text-yellow-400" />;
  return <File className="w-4 h-4 text-gray-400" />;
};

export default function Sidebar({ files, selectedFile, onSelectFile }) {
  const fileNames = Object.keys(files);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
          Project Files
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto">
        {fileNames.length === 0 ? (
          <div className="p-4 text-gray-500 text-sm">
            No files generated yet
          </div>
        ) : (
          <div className="p-2">
            {fileNames.map((filename) => (
              <button
                key={filename}
                onClick={() => onSelectFile(filename)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-colors ${
                  selectedFile === filename
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800'
                }`}
              >
                {getFileIcon(filename)}
                <span className="text-sm truncate">{filename}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
