import { useState, useEffect } from 'react';
import { FolderOpen, ChevronDown, ChevronRight, Clock } from 'lucide-react';

export default function ProjectHistory({ onSelectProject, currentProject }) {
  const [projects, setProjects] = useState([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await fetch('http://localhost:8000/projects');
      const data = await response.json();
      setProjects(data.projects || []);
    } catch (error) {
      console.error('Error loading projects:', error);
    }
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const formatProjectName = (name) => {
    // Remove timestamp and make readable
    return name.replace(/_\d{8}_\d{6}$/, '').replace(/_/g, ' ');
  };

  return (
    <div className="border-b border-gray-800">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-semibold text-gray-300">Project History</span>
          <span className="text-xs text-gray-500">({projects.length})</span>
        </div>
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
      </button>
      
      {isOpen && (
        <div className="max-h-64 overflow-y-auto">
          {projects.length === 0 ? (
            <div className="p-4 text-sm text-gray-500">No projects yet</div>
          ) : (
            projects.map((project) => (
              <button
                key={project.name}
                onClick={() => {
                  onSelectProject(project.name);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-4 py-3 hover:bg-gray-800 transition-colors border-l-2 ${
                  currentProject === project.name
                    ? 'border-purple-500 bg-gray-800/50'
                    : 'border-transparent'
                }`}
              >
                <div className="flex items-start gap-2">
                  <FolderOpen className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-gray-300 truncate capitalize">
                      {formatProjectName(project.name)}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {formatDate(project.created)}
                    </div>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
