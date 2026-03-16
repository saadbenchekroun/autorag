"use client";

import React, { useState } from 'react';

export default function Playground({ project }: { project: any }) {
  const [query, setQuery] = useState('');
  const [running, setRunning] = useState(false);
  const [response, setResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setRunning(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch(`http://localhost:8000/api/v1/projects/${project.project_id}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          architecture: project.architecture
        }),
      });

      if (!res.ok) {
        throw new Error(`Query failed: ${res.statusText}`);
      }

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setResponse(data);
    } catch (err: any) {
      setError(err.message || "An error occurred.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mt-8 pt-8">
      <form onSubmit={handleQuery} className="flex gap-3 mb-8">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={`Ask a question against your ${project.documents_indexed} documents...`}
          className="flex-1 bg-white border border-zinc-200 rounded-xl px-5 py-3 text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 transition-all shadow-sm"
        />
        <button
          type="submit"
          disabled={running}
          className="px-8 py-3 bg-zinc-900 hover:bg-black disabled:opacity-50 text-white font-medium rounded-xl transition-all shadow-md shadow-zinc-900/10 flex items-center justify-center shrink-0 min-w-[120px]"
        >
          {running ? (
            <div className="w-5 h-5 border-[2px] border-zinc-500 border-t-white rounded-full animate-spin"></div>
          ) : "Ask AutoRAG"}
        </button>
      </form>

      {error && (
        <div className="p-4 bg-red-50 border border-red-100 text-red-600 rounded-xl text-sm mb-8 flex items-start gap-3">
           <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          {error}
        </div>
      )}

      {response && (
        <div className="bg-white rounded-2xl p-8 border border-zinc-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div>
            <h4 className="text-[11px] font-semibold text-zinc-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              Generated Response
            </h4>
            <div className="prose prose-zinc max-w-none text-zinc-700 leading-relaxed font-light">
              {response.answer}
            </div>
            <div className="text-xs text-zinc-400 font-medium mt-6 bg-zinc-50 inline-block px-3 py-1.5 rounded-md border border-zinc-100">
              Generated via: {response.metrics?.generation_mode}
            </div>
          </div>

          <div className="pt-8 border-t border-zinc-100">
            <h4 className="text-[11px] font-semibold text-zinc-400 uppercase tracking-widest mb-6">Retrieved Context ({response.metrics?.chunks_retrieved} Vectors)</h4>
            <div className="grid gap-4">
              {response.context_used?.map((ctx: any, i: number) => (
                <div key={i} className="bg-zinc-50/50 p-5 rounded-xl border border-zinc-100 relative group overflow-hidden">
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-zinc-200 group-hover:bg-zinc-900 transition-colors"></div>
                  <span className="text-xs text-zinc-900 font-semibold block mb-2 font-mono bg-white px-2 py-1 rounded inline-block border border-zinc-100 tracking-tight">{ctx.source}</span>
                  <p className="text-sm text-zinc-600 leading-relaxed font-light">{ctx.text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
