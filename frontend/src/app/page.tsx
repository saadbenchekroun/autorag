'use client';

import React, { useState } from 'react';
import UploadDataset from '@/components/UploadDataset';
import DeploymentsList from '@/components/DeploymentsList';
import ApiKeysDrawer from '@/components/ApiKeysDrawer';

export default function Home() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white text-zinc-900 font-sans selection:bg-zinc-200">

      <ApiKeysDrawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />

      {/* Premium Navbar */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-zinc-100">
        <div className="max-w-6xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 bg-zinc-900 rounded-full"></div>
            <span className="font-medium text-lg tracking-tight">AutoRAG</span>
          </div>
          <div className="flex gap-8">
            <button className="text-sm font-medium text-zinc-500 hover:text-zinc-900 transition-colors">Documentation</button>
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="text-sm font-medium text-zinc-500 hover:text-zinc-900 transition-colors"
            >
              API Keys
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl w-full mx-auto px-6 pt-24 pb-32">
        {/* Header Section */}
        <div className="text-center max-w-3xl mx-auto mb-20 animate-in fade-in slide-in-from-bottom-4 duration-1000 ease-out">
          <h1 className="text-4xl md:text-5xl font-semibold tracking-tight text-zinc-900 mb-6 leading-tight">
            Autonomous RAG architectures. <br/> Designed in seconds.
          </h1>
          <p className="text-lg text-zinc-500 leading-relaxed font-light">
            Upload your documents. We automatically determine the optimal vector database, embedding model, and chunking strategy for your specific dataset.
          </p>
        </div>

        {/* Upload Section */}
        <div className="mb-32">
          <UploadDataset />
        </div>

        {/* Active Deployments Section */}
        <div className="border-t border-zinc-100 pt-20">
          <div className="flex items-end justify-between mb-12">
            <div>
              <h2 className="text-2xl font-medium tracking-tight mb-2">Deployments</h2>
              <p className="text-sm text-zinc-500 font-light">Your actively running retrieval pipelines.</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl overflow-hidden shadow-[0_8px_30px_rgb(0,0,0,0.04)] ring-1 ring-zinc-100">
            <DeploymentsList />
          </div>
        </div>
      </main>
    </div>
  );
}
