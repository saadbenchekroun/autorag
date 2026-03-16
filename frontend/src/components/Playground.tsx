"use client";

import React, { useState } from 'react';

interface ArchitectureDecision {
  vector_database: string;
  chunking_strategy: string;
  chunk_size: number;
  overlap_size: number;
  embedding_model: string;
}

interface ProjectMeta {
  project_id: string;
  documents_indexed: number;
  chunks_created: number;
  architecture: ArchitectureDecision;
}

interface ContextChunk {
  text: string;
  source: string;
}

interface QueryResponse {
  answer: string;
  context_used: ContextChunk[];
  metrics: {
    chunks_retrieved: number;
    generation_mode: string;
  };
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Playground({ project }: { project: ProjectMeta }) {
  const [query, setQuery] = useState('');
  const [k, setK] = useState(3);
  const [running, setRunning] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setRunning(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${project.project_id}/query`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: query.trim(),
            architecture: project.architecture,
          }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data?.detail ?? `Query failed (${res.status})`);
      }

      setResponse(data as QueryResponse);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setRunning(false);
    }
  };

  const modeLabel = (mode: string) =>
    mode === 'openai' ? '🤖 OpenAI Generation' : '📄 Retrieval Only (no API key)';

  return (
    <div>
      {/* Query form */}
      <form onSubmit={handleQuery} className="space-y-3 mb-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Ask about your ${project.documents_indexed} document${project.documents_indexed !== 1 ? 's' : ''}…`}
            className="flex-1 bg-white border border-zinc-200 rounded-xl px-5 py-3 text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 transition-all shadow-sm"
          />
          <button
            type="submit"
            disabled={running || !query.trim()}
            className="px-8 py-3 bg-zinc-900 hover:bg-black disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all shadow-md shadow-zinc-900/10 flex items-center justify-center shrink-0 min-w-[120px]"
          >
            {running ? (
              <div className="w-5 h-5 border-[2px] border-zinc-500 border-t-white rounded-full animate-spin" />
            ) : "Ask AutoRAG"}
          </button>
        </div>

        {/* Retrieval depth control */}
        <div className="flex items-center gap-3 text-sm text-zinc-500">
          <label htmlFor="k-slider" className="whitespace-nowrap font-medium">Retrieve k =</label>
          <input
            id="k-slider"
            type="range"
            min={1}
            max={10}
            value={k}
            onChange={(e) => setK(Number(e.target.value))}
            className="w-32 accent-zinc-900"
          />
          <span className="font-mono text-zinc-700 w-4">{k}</span>
          <span className="text-zinc-400">chunks</span>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-100 text-red-600 rounded-xl text-sm mb-6 flex items-start gap-3">
          <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      {/* Response */}
      {response && (
        <div className="bg-white rounded-2xl p-8 border border-zinc-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Answer */}
          <div>
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <h4 className="text-[11px] font-semibold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Generated Response
              </h4>
              <span className="text-xs bg-zinc-100 text-zinc-600 px-3 py-1 rounded-full font-medium border border-zinc-200">
                {modeLabel(response.metrics?.generation_mode)}
              </span>
            </div>
            <div className="prose prose-zinc max-w-none text-zinc-700 leading-relaxed font-light whitespace-pre-wrap">
              {response.answer}
            </div>
          </div>

          {/* Retrieval metrics */}
          <div className="flex gap-6 text-sm pt-4 border-t border-zinc-50">
            <div>
              <span className="text-zinc-400 text-xs uppercase tracking-widest font-semibold block mb-1">Chunks retrieved</span>
              <span className="font-semibold text-zinc-900">{response.metrics?.chunks_retrieved}</span>
            </div>
            <div>
              <span className="text-zinc-400 text-xs uppercase tracking-widest font-semibold block mb-1">Vector store</span>
              <span className="font-semibold text-zinc-900 capitalize">{project.architecture?.vector_database}</span>
            </div>
            <div>
              <span className="text-zinc-400 text-xs uppercase tracking-widest font-semibold block mb-1">Embedding</span>
              <span className="font-semibold text-zinc-900 capitalize">{project.architecture?.embedding_model?.replace(/_/g, ' ')}</span>
            </div>
          </div>

          {/* Retrieved context */}
          {response.context_used?.length > 0 && (
            <div className="pt-6 border-t border-zinc-100">
              <h4 className="text-[11px] font-semibold text-zinc-400 uppercase tracking-widest mb-6">
                Retrieved Context ({response.context_used.length} chunks)
              </h4>
              <div className="grid gap-4">
                {response.context_used.map((ctx, i) => (
                  <div key={i} className="bg-zinc-50/50 p-5 rounded-xl border border-zinc-100 relative group overflow-hidden">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-zinc-200 group-hover:bg-zinc-900 transition-colors" />
                    <span className="text-xs text-zinc-900 font-semibold block mb-2 font-mono bg-white px-2 py-1 rounded inline-block border border-zinc-100 tracking-tight">
                      {ctx.source}
                    </span>
                    <p className="text-sm text-zinc-600 leading-relaxed font-light">{ctx.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
