"use client";

import React, { useState, useRef } from 'react';

// Supported file extensions (mirrors backend pipeline.yaml)
const SUPPORTED_EXTENSIONS = [
  '.pdf', '.docx', '.txt', '.md', '.html', '.csv', '.json',
  '.py', '.js', '.ts', '.java', '.cpp'
];

// Max upload size matches backend MAX_UPLOAD_MB default (50 MB)
const MAX_MB = 50;

interface ArchitectureDecision {
  vector_database: string;
  chunking_strategy: string;
  chunk_size: number;
  overlap_size: number;
  embedding_model: string;
  reasoning: string[];
}

interface DocumentMetrics {
  filename?: string;
  estimated_tokens: number;
  has_code_blocks: boolean;
  semantic_density: string;
  raw_length_chars: number;
}

interface BuildPipelineResponse {
  project_id: string;
  message: string;
  architecture_decision: ArchitectureDecision;
  dataset_analysis: DocumentMetrics[];
  errors: string[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function formatModelName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function TokenBadge({ density }: { density: string }) {
  const colors: Record<string, string> = {
    high: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    medium: 'bg-amber-50 text-amber-700 border-amber-200',
    low: 'bg-slate-50 text-slate-600 border-slate-200',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-medium ${colors[density] ?? colors.low}`}>
      {density}
    </span>
  );
}

export default function UploadDataset({ onIndexed }: { onIndexed?: () => void }) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<BuildPipelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) setFiles(Array.from(e.dataTransfer.files));
  };
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) setFiles(Array.from(e.target.files));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    // Client-side size validation
    const oversized = files.find(f => f.size > MAX_MB * 1024 * 1024);
    if (oversized) {
      setError(`"${oversized.name}" exceeds the ${MAX_MB} MB upload limit.`);
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    const savedKeys = localStorage.getItem('autorag_api_keys');
    if (savedKeys) formData.append("api_keys", savedKeys);

    try {
      const response = await fetch(`${API_BASE}/api/v1/projects/build`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        const detail = data?.detail;
        const msg = typeof detail === 'string'
          ? detail
          : detail?.error ?? `Upload failed (${response.status})`;
        throw new Error(msg);
      }

      setResult(data as BuildPipelineResponse);
      onIndexed?.();
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during upload.");
    } finally {
      setUploading(false);
    }
  };

  // ── Result screen ──────────────────────────────────────────────────────
  if (result) {
    const arch = result.architecture_decision;
    const totalTokens = result.dataset_analysis.reduce((s, m) => s + m.estimated_tokens, 0);

    return (
      <div className="w-full mx-auto my-8 p-10 bg-white shadow-[0_8px_30px_rgb(0,0,0,0.04)] ring-1 ring-zinc-100 rounded-[2rem] relative overflow-hidden">
        <div className="relative z-10">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8 pb-8 border-b border-zinc-100">
            <div className="w-12 h-12 bg-zinc-900 text-white rounded-xl flex items-center justify-center shrink-0">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <h3 className="text-2xl font-semibold text-zinc-900 tracking-tight">Architecture Generated</h3>
              <p className="text-zinc-500 font-light mt-1">
                Indexing {result.dataset_analysis.length} document{result.dataset_analysis.length !== 1 ? 's' : ''} (~{totalTokens.toLocaleString()} tokens) in the background.
              </p>
            </div>
          </div>

          {/* Architecture cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'Vector Store', value: arch.vector_database },
              { label: 'Embeddings', value: formatModelName(arch.embedding_model) },
              { label: 'Chunking', value: formatModelName(arch.chunking_strategy) },
              { label: 'Parameters', value: `${arch.chunk_size}`, sub: `${arch.overlap_size} overlap` },
            ].map(({ label, value, sub }) => (
              <div key={label} className="bg-zinc-50/50 p-5 rounded-2xl border border-zinc-100">
                <span className="block text-xs text-zinc-400 uppercase tracking-widest font-medium mb-2">{label}</span>
                <span className="text-lg text-zinc-900 font-medium capitalize truncate block" title={value}>{value}</span>
                {sub && <span className="text-sm text-zinc-400 font-light">{sub}</span>}
              </div>
            ))}
          </div>

          {/* Per-document analysis */}
          {result.dataset_analysis.length > 0 && (
            <div className="mb-8">
              <h4 className="text-sm font-semibold tracking-wide text-zinc-900 mb-3 uppercase">Document Analysis</h4>
              <div className="rounded-2xl border border-zinc-100 overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-zinc-50 border-b border-zinc-100">
                    <tr>
                      {['File', 'Tokens', 'Density', 'Code'].map(h => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-zinc-400 uppercase tracking-widest">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-50">
                    {result.dataset_analysis.map((m, i) => (
                      <tr key={i} className="hover:bg-zinc-50/50 transition-colors">
                        <td className="px-4 py-3 font-medium text-zinc-700 truncate max-w-[160px]" title={m.filename ?? ''}>{m.filename ?? '—'}</td>
                        <td className="px-4 py-3 text-zinc-500">{m.estimated_tokens.toLocaleString()}</td>
                        <td className="px-4 py-3"><TokenBadge density={m.semantic_density} /></td>
                        <td className="px-4 py-3">
                          {m.has_code_blocks
                            ? <span className="text-xs bg-violet-50 text-violet-700 border border-violet-200 px-2 py-0.5 rounded font-medium">Yes</span>
                            : <span className="text-zinc-300">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Skipped files warning */}
          {result.errors.length > 0 && (
            <div className="mb-8 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
              <p className="font-semibold mb-1">⚠ {result.errors.length} file{result.errors.length > 1 ? 's' : ''} skipped</p>
              <ul className="list-disc list-inside space-y-1 font-light">
                {result.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}

          {/* AI Reasoning */}
          <div className="mb-8">
            <h4 className="text-sm font-semibold tracking-wide text-zinc-900 mb-4 uppercase">Decision Reasoning</h4>
            <div className="space-y-3">
              {arch.reasoning.map((r, i) => (
                <div key={i} className="flex gap-4 p-4 rounded-xl bg-zinc-50/50 border border-zinc-100">
                  <span className="text-zinc-400 mt-0.5 shrink-0 opacity-50 font-mono text-xs">{String(i + 1).padStart(2, '0')}</span>
                  <span className="text-zinc-600 font-light leading-relaxed">{r}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Project ID */}
          <div className="mb-8 p-4 bg-zinc-50 rounded-xl border border-zinc-100 text-sm font-light text-zinc-500">
            Project ID: <code className="font-mono text-zinc-700 ml-1">{result.project_id}</code>
            <span className="ml-3 text-xs text-zinc-400">← Use this to query via CLI: <code className="font-mono">autorag query {result.project_id} "your question"</code></span>
          </div>

          <div className="flex justify-end pt-6 border-t border-zinc-100">
            <button
              onClick={() => { setResult(null); setFiles([]); }}
              className="px-6 py-2.5 bg-zinc-900 hover:bg-black text-white text-sm font-medium rounded-xl transition-all shadow-sm">
              Build Another Pipeline
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Upload screen ──────────────────────────────────────────────────────
  return (
    <div className="w-full mx-auto">
      <div
        className={`border-2 border-dashed rounded-[2rem] p-16 text-center transition-all duration-500 relative overflow-hidden backdrop-blur-sm ${
          isDragging
            ? 'border-zinc-900 bg-zinc-50 scale-[1.01]'
            : 'border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50/50 hover:shadow-[0_8px_30px_rgb(0,0,0,0.04)]'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          multiple
          ref={fileInputRef}
          className="hidden"
          accept={SUPPORTED_EXTENSIONS.join(',')}
          onChange={handleFileSelect}
        />

        <div className="w-20 h-20 mx-auto bg-zinc-50 rounded-2xl flex items-center justify-center mb-6 border border-zinc-100 relative">
          {uploading ? (
            <div className="w-8 h-8 border-[3px] border-zinc-200 border-t-zinc-900 rounded-full animate-spin" />
          ) : (
            <svg className="w-8 h-8 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          )}
        </div>

        <h3 className="text-2xl font-medium mb-3 text-zinc-900 tracking-tight">Dataset Ingestion</h3>
        <p className="text-zinc-500 font-light mb-3 max-w-md mx-auto leading-relaxed">
          {uploading
            ? "Analysing document semantics and building vector infrastructure…"
            : "Upload files to auto-design your RAG pipeline. Indexing runs in the background."}
        </p>
        <p className="text-xs text-zinc-400 mb-10 font-mono">
          {SUPPORTED_EXTENSIONS.join(' · ')} · max {MAX_MB} MB per file
        </p>

        {!uploading && (
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-8 py-3 bg-zinc-900 text-white text-sm font-medium rounded-xl hover:bg-black transition-all shadow-md shadow-zinc-900/10 active:scale-95"
          >
            Select Documents
          </button>
        )}

        {error && (
          <div className="mt-8 p-4 bg-red-50 text-red-600 rounded-xl text-sm border border-red-100 text-left">
            <p className="font-medium mb-1">Upload failed</p>
            <p className="font-light">{error}</p>
          </div>
        )}

        {files.length > 0 && !uploading && (
          <div className="mt-12 pt-8 border-t border-zinc-100 text-left animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-2xl mx-auto">
            <h4 className="text-xs font-semibold text-zinc-400 mb-4 uppercase tracking-widest">{files.length} File{files.length > 1 ? 's' : ''} Queued</h4>
            <ul className="space-y-3">
              {files.slice(0, 5).map((f, i) => (
                <li key={i} className="flex items-center gap-4 bg-white p-4 rounded-xl border border-zinc-100 shadow-sm">
                  <div className="w-10 h-10 rounded-lg bg-zinc-50 flex items-center justify-center shrink-0 border border-zinc-100">
                    <svg className="w-5 h-5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <span className="text-sm font-medium text-zinc-700 truncate flex-1">{f.name}</span>
                  <span className="text-xs font-medium text-zinc-400 shrink-0 bg-zinc-100 px-2 py-1 rounded-md">
                    {(f.size / 1024 / 1024).toFixed(2)} MB
                  </span>
                </li>
              ))}
              {files.length > 5 && (
                <li className="text-sm text-zinc-500 font-light text-center py-2">
                  + {files.length - 5} more
                </li>
              )}
            </ul>
            <button
              onClick={handleUpload}
              className="w-full mt-8 py-3.5 bg-zinc-900 hover:bg-black text-white text-sm font-medium rounded-xl transition-all shadow-md shadow-zinc-900/10 flex items-center justify-center gap-2">
              Generate RAG Pipeline
              <svg className="w-4 h-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
