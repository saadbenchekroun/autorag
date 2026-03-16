"use client";

import React, { useEffect, useState } from 'react';
import Playground from './Playground';

export default function DeploymentsList() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activePlayground, setActivePlayground] = useState<string | null>(null);

  const fetchDeployments = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/projects");
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (err) {
      console.error("Failed to fetch deployments", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployments();
    // Simple polling to catch newly compiled projects in the background
    const interval = setInterval(fetchDeployments, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="p-12 text-center text-zinc-400 font-light animate-pulse">Loading deployments...</div>;
  }

  if (projects.length === 0) {
    return (
      <div className="p-16 text-center flex flex-col items-center">
        <svg className="w-12 h-12 mb-6 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
        <p className="text-xl font-medium text-zinc-900 mb-2">No active infrastructure</p>
        <p className="text-zinc-500 font-light max-w-sm mx-auto">Systems are currently idle. Upload documents above to initialize your first autonomous RAG architecture.</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-zinc-100">
      {projects.map((proj) => (
        <div key={proj.project_id} className="p-8 transition-colors hover:bg-zinc-50/50 group">
          <div className="flex items-start justify-between mb-8">
            <div className="flex items-center gap-5">
              <div className="w-12 h-12 rounded-xl bg-zinc-900 text-white flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
              </div>
              <div>
                <h3 className="text-xl font-medium text-zinc-900 tracking-tight flex items-center gap-3">
                  Pipeline <span className="text-xs font-mono text-zinc-500 bg-zinc-100 px-2.5 py-1 rounded-md">{proj.project_id.split('-')[0]}</span>
                </h3>
                <p className="text-sm text-zinc-500 font-light mt-1">{new Date(proj.created_at * 1000).toLocaleString()}</p>
              </div>
            </div>
            
            <button 
              onClick={() => setActivePlayground(activePlayground === proj.project_id ? null : proj.project_id)}
              className={`px-5 py-2 rounded-xl text-sm font-medium transition-all ${activePlayground === proj.project_id ? 'bg-zinc-900 text-white' : 'bg-white border border-zinc-200 text-zinc-700 hover:border-zinc-300 hover:bg-zinc-50'}`}
            >
              {activePlayground === proj.project_id ? 'Close Playground' : 'Query Playground'}
            </button>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <span className="block text-[11px] text-zinc-400 uppercase tracking-widest font-semibold mb-1">Documents</span>
              <span className="text-base text-zinc-900 font-medium">{proj.documents_indexed}</span>
            </div>
            <div>
              <span className="block text-[11px] text-zinc-400 uppercase tracking-widest font-semibold mb-1">Chunks Indexed</span>
              <span className="text-base text-zinc-900 font-medium">{proj.chunks_created}</span>
            </div>
            <div>
              <span className="block text-[11px] text-zinc-400 uppercase tracking-widest font-semibold mb-1">Vector Engine</span>
              <span className="text-base text-zinc-900 font-medium capitalize">{proj.architecture?.vector_database}</span>
            </div>
            <div>
              <span className="block text-[11px] text-zinc-400 uppercase tracking-widest font-semibold mb-1">Embeddings</span>
              <span className="text-base text-zinc-900 font-medium capitalize truncate block" title={proj.architecture?.embedding_model}>
                {proj.architecture?.embedding_model.replace('_', ' ')}
              </span>
            </div>
          </div>
          
          {activePlayground === proj.project_id && (
            <div className="mt-8 pt-8 border-t border-zinc-100 animate-in fade-in slide-in-from-top-4 duration-500">
              <Playground project={proj} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
