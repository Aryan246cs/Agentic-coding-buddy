import { useState, useEffect } from 'react';
import PromptBar from '../components/PromptBar';
import Sidebar from '../components/Sidebar';
import CodeEditor from '../components/Editor';
import Preview from '../components/Preview';
import ProjectHistory from '../components/ProjectHistory';

export default function Builder() {
  const [files, setFiles] = useState({});
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [projectName, setProjectName] = useState('');

  // Load existing files on mount
  useEffect(() => {
    const loadExistingFiles = async () => {
      try {
        const response = await fetch('http://localhost:8000/projects');
        const data = await response.json();
        
        // Load the most recent project if available
        if (data.projects && data.projects.length > 0) {
          const latestProject = data.projects[0].name;
          loadProject(latestProject);
        }
      } catch (error) {
        console.error('Error loading existing files:', error);
      }
    };
    
    loadExistingFiles();
  }, []);

  const loadProject = async (projectName) => {
    try {
      const response = await fetch(`http://localhost:8000/projects/${projectName}`);
      const data = await response.json();
      
      if (data.files && Object.keys(data.files).length > 0) {
        setFiles(data.files);
        setProjectName(projectName);
        const firstFile = Object.keys(data.files)[0];
        if (firstFile) {
          setSelectedFile(firstFile);
        }
      }
    } catch (error) {
      console.error('Error loading project:', error);
    }
  };

  const handleGenerate = async (prompt) => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.error) {
        alert(`Error: ${data.error}`);
      } else {
        setFiles(data.files || {});
        setProjectName(data.project_name || '');
        
        // Auto-select first file
        const firstFile = Object.keys(data.files || {})[0];
        if (firstFile) {
          setSelectedFile(firstFile);
        }
      }
    } catch (error) {
      console.error('Error generating project:', error);
      alert('Failed to generate project. Make sure backend is running on port 8000.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      <PromptBar onGenerate={handleGenerate} loading={loading} />
      
      <div className="flex-1 flex overflow-hidden">
        <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
          <ProjectHistory 
            onSelectProject={loadProject}
            currentProject={projectName}
          />
          <Sidebar
            files={files}
            selectedFile={selectedFile}
            onSelectFile={setSelectedFile}
          />
        </div>
        
        <CodeEditor
          file={selectedFile}
          content={files[selectedFile]}
        />
        
        <Preview files={files} />
      </div>
    </div>
  );
}
