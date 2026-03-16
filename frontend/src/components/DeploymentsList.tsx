"use client";

import React, { useEffect, useState, useCallback } from 'react';
import Playground from './Playground';

interface ArchitectureDecision {
  vector_database: string;
  chunking_strategy: string;
  chunk_size: number;
  overlap_size: number;
  embedding_model: string;
}

interface ProjectMeta {
  project_id: string;
  created_at: number;
  documents_indexed: number;
  chunks_created: number;
  architecture: ArchitectureDecision;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function formatModelName(s: string): string {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function MetaChip({ label, value, title }: { label: string; value: string; title?: string }) {
  return (
    <div>
      <span className="block text-[11px] text-zinc-400 uppercase tracking-widest font-semibold mb-1">{label}</span>
      <span
        className="text-base text-zinc-900 font-medium capitalize truncate block"
        title={title ?? value}
      >
        {value}
      </span>
    </div>
  );
}

export default function DeploymentsList({ refreshKey }: { refreshKey?: number }) {
  const [projects, setProjects] = useState<ProjectMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [activePlayground, setActivePlayground] = useState<string | null>(null);

  const fetchDeployments = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/projects`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setProjects(data.projects ?? []);
    } catch (err) {
      console.error("Failed to fetch deployments", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDeployments();
    // Poll every 8s to surface newly completed background indexing jobs
    const interval = setInterval(fetchDeployments, 8000);
    return () => clearInterval(interval);
  }, [fetchDeployments, refreshKey]);

  if (loading) {
    return (
      <div className="p-12 text-center text-zinc-400 font-light animate-pulse">
        Loading deployments…
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="p-16 text-center flex flex-col items-center">
        <svg className="w-12 h-12 mb-6 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        <p className="text-xl font-medium text-zinc-900 mb-2">No indexed projects yet</p>
        <p className="text-zinc-500 font-light max-w-sm mx-auto">
          Upload documents above to initialise your first autonomous RAG pipeline. Results appear here automatically once indexing completes.
        </p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-zinc-100">
      {projects.map((proj) => {
        const arch = proj.architecture ?? {};
        const isActive = activePlayground === proj.project_id;
        return (
          <div key={proj.project_id} className="p-8 transition-colors hover:bg-zinc-50/30 group">
            {/* Project header */}
            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center gap-5">
                <div className="w-12 h-12 rounded-xl bg-zinc-900 text-white flex items-center justify-center shrink-0">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-zinc-900 tracking-tight flex items-center gap-3 flex-wrap">
                    Pipeline
                    <span className="text-xs font-mono text-zinc-500 bg-zinc-100 px-2.5 py-1 rounded-md">
                      {proj.project_id.split('-')[0]}
                    </span>
                    <span className="text-xs text-zinc-400 font-light">
                      {new Date(proj.created_at * 1000).toLocaleString()}
                    </span>
                  </h3>
                  <p className="text-sm text-zinc-400 font-mono mt-0.5 select-all">{proj.project_id}</p>
                </div>
              </div>

              <button
                onClick={() => setActivePlayground(isActive ? null : proj.project_id)}
                className={`px-5 py-2 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-zinc-900 text-white'
                    : 'bg-white border border-zinc-200 text-zinc-700 hover:border-zinc-300 hover:bg-zinc-50'
                }`}
              >
                {isActive ? 'Close Playground' : 'Query Playground'}
              </button>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <MetaChip label="Documents" value={String(proj.documents_indexed ?? '—')} />
              <MetaChip label="Chunks" value={String(proj.chunks_created ?? '—')} />
              <MetaChip
                label="Vector Store"
                value={arch.vector_database ?? '—'}
              />
              <MetaChip
                label="Chunking"
                value={formatModelName(arch.chunking_strategy ?? 'unknown')}
                title={arch.chunking_strategy}
              />
              <MetaChip
                label="Embeddings"
                value={formatModelName(arch.embedding_model ?? 'unknown')}
                title={arch.embedding_model}
              />
            </div>

            {/* Chunk size params */}
            {arch.chunk_size && (
              <div className="mt-3 text-xs text-zinc-400 font-light">
                chunk_size={arch.chunk_size} · overlap={arch.overlap_size}
              </div>
            )}

            {/* Playground */}
            {isActive && (
              <div className="mt-8 pt-8 border-t border-zinc-100 animate-in fade-in slide-in-from-top-4 duration-500">
                <Playground project={proj} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
