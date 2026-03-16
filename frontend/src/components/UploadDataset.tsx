"use client";

import React, { useState, useRef } from 'react';

export default function UploadDataset() {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    // Inject API configurations for intelligent architecture decisions
    const savedKeys = localStorage.getItem('autorag_api_keys');
    if (savedKeys) {
      formData.append("api_keys", savedKeys);
    }

    try {
      const response = await fetch("http://localhost:8000/api/v1/projects/build", {
        method: "POST",
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "An error occurred during upload.");
    } finally {
      setUploading(false);
    }
  };

  if (result) {
    const arch = result.architecture_decision;
    return (
      <div className="w-full mx-auto my-8 p-10 bg-white shadow-[0_8px_30px_rgb(0,0,0,0.04)] ring-1 ring-zinc-100 rounded-[2rem] relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center gap-4 mb-8 pb-8 border-b border-zinc-100">
            <div className="w-12 h-12 bg-zinc-900 text-white rounded-xl flex items-center justify-center shrink-0">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
            </div>
            <div>
              <h3 className="text-2xl font-semibold text-zinc-900 tracking-tight">Architecture Generated</h3>
              <p className="text-zinc-500 font-light mt-1">Indexing optimized pipeline in the background using auto-detected settings.</p>
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
            <div className="bg-zinc-50/50 p-5 rounded-2xl border border-zinc-100">
               <span className="block text-xs text-zinc-400 uppercase tracking-widest font-medium mb-2">Vector Store</span>
               <span className="text-lg text-zinc-900 font-medium capitalize">{arch?.vector_database}</span>
            </div>
            <div className="bg-zinc-50/50 p-5 rounded-2xl border border-zinc-100">
               <span className="block text-xs text-zinc-400 uppercase tracking-widest font-medium mb-2">Embeddings</span>
               <span className="text-lg text-zinc-900 font-medium capitalize truncate block" title={arch?.embedding_model}>{arch?.embedding_model.replace('_', ' ')}</span>
            </div>
            <div className="bg-zinc-50/50 p-5 rounded-2xl border border-zinc-100">
               <span className="block text-xs text-zinc-400 uppercase tracking-widest font-medium mb-2">Chunking</span>
               <span className="text-lg text-zinc-900 font-medium capitalize truncate block" title={arch?.chunking_strategy}>{arch?.chunking_strategy.replace('_', ' ')}</span>
            </div>
            <div className="bg-zinc-50/50 p-5 rounded-2xl border border-zinc-100">
                 <span className="block text-xs text-zinc-400 uppercase tracking-widest font-medium mb-2">Parameters</span>
                 <span className="text-lg text-zinc-900 font-medium leading-none block">{arch?.chunk_size} <span className="text-sm font-light text-zinc-400">tokens</span></span>
                 <span className="text-sm text-zinc-500 font-light mt-1 block">{arch?.overlap_size} overlap</span>
            </div>
          </div>

          <div className="mb-10">
            <h4 className="text-sm font-semibold tracking-wide text-zinc-900 mb-4 uppercase">AI Reasoning Logs</h4>
            <div className="space-y-3">
              {arch?.reasoning.map((r: string, i: number) => (
                <div key={i} className="flex gap-4 p-4 rounded-xl bg-zinc-50/50 border border-zinc-100">
                  <span className="text-zinc-400 mt-0.5 shrink-0 opacity-50">0{i+1}</span> 
                  <span className="text-zinc-600 font-light leading-relaxed">{r}</span>
                </div>
              ))}
            </div>
          </div>
          
          <div className="flex justify-end pt-6 border-t border-zinc-100">
            <button 
              onClick={() => {setResult(null); setFiles([])}}
              className="px-6 py-2.5 bg-zinc-900 hover:bg-black text-white text-sm font-medium rounded-xl transition-all shadow-sm">
              Build Another Pipeline
            </button>
          </div>
        </div>
      </div>
    )
  }

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
          onChange={handleFileSelect} 
        />
        
        <div className="w-20 h-20 mx-auto bg-zinc-50 rounded-2xl flex items-center justify-center mb-6 border border-zinc-100 relative">
          {uploading ? (
            <div className="w-8 h-8 border-[3px] border-zinc-200 border-t-zinc-900 rounded-full animate-spin"></div>
          ) : (
            <svg className="w-8 h-8 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
            </svg>
          )}
        </div>
        
        <h3 className="text-2xl font-medium mb-3 text-zinc-900 tracking-tight">Dataset Ingestion</h3>
        <p className="text-zinc-500 font-light mb-10 max-w-md mx-auto leading-relaxed">
          {uploading ? "Analyzing document semantics and building vector infrastructure..." : "Upload PDFs, Markdown, Word docs, or zip files. We handle parsing, chunking, and embedding."}
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
          <div className="mt-8 p-4 bg-red-50 text-red-600 rounded-xl text-sm border border-red-100">
            {error}
          </div>
        )}

        {files.length > 0 && !uploading && (
          <div className="mt-12 pt-8 border-t border-zinc-100 text-left animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-2xl mx-auto">
            <h4 className="text-xs font-semibold text-zinc-400 mb-4 uppercase tracking-widest">{files.length} Files Queued</h4>
            <ul className="space-y-3">
              {files.slice(0, 3).map((f, i) => (
                <li key={i} className="flex items-center gap-4 bg-white p-4 rounded-xl border border-zinc-100 shadow-sm">
                  <div className="w-10 h-10 rounded-lg bg-zinc-50 flex items-center justify-center shrink-0 border border-zinc-100">
                    <svg className="w-5 h-5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                  </div>
                  <span className="text-sm font-medium text-zinc-700 truncate">{f.name}</span>
                  <span className="text-xs font-medium text-zinc-400 ml-auto shrink-0 bg-zinc-100 px-2 py-1 rounded-md">{(f.size / 1024 / 1024).toFixed(2)} MB</span>
                </li>
              ))}
              {files.length > 3 && (
                <li className="text-sm text-zinc-500 font-light text-center py-2">
                  + {files.length - 3} additional documents
                </li>
              )}
            </ul>
            <button 
              onClick={handleUpload}
              className="w-full mt-8 py-3.5 bg-zinc-900 hover:bg-black text-white text-sm font-medium rounded-xl transition-all shadow-md shadow-zinc-900/10 flex items-center justify-center gap-2">
              Generate RAG Pipeline
              <svg className="w-4 h-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
