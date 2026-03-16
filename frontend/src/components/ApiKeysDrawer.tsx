"use client";

import React, { useState, useEffect } from 'react';

interface ApiKeys {
  llm_provider: string;
  llm_key: string;
  vector_db_provider: string;
  vector_db_key: string;
  embedding_provider: string;
  embedding_key: string;
}

export default function ApiKeysDrawer({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
  const [keys, setKeys] = useState<ApiKeys>({
    llm_provider: 'openai',
    llm_key: '',
    vector_db_provider: 'none',
    vector_db_key: '',
    embedding_provider: 'none',
    embedding_key: ''
  });

  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const savedKeys = localStorage.getItem('autorag_api_keys');
    if (savedKeys) {
      try {
        setKeys(JSON.parse(savedKeys));
      } catch (e) {
        console.error("Failed to parse API keys from localStorage");
      }
    }
  }, []);

  const handleSave = () => {
    localStorage.setItem('autorag_api_keys', JSON.stringify(keys));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/10 backdrop-blur-sm z-[100] animate-in fade-in duration-300"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-white z-[101] shadow-2xl border-l border-zinc-100 p-10 flex flex-col animate-in slide-in-from-right duration-500 ease-out">
        <div className="flex items-center justify-between mb-12">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-zinc-900">Infrastructure Keys</h2>
            <p className="text-sm text-zinc-500 font-light mt-1">Configure your cloud intelligence providers.</p>
          </div>
          <button 
            onClick={onClose}
            className="w-10 h-10 rounded-full hover:bg-zinc-50 flex items-center justify-center transition-colors text-zinc-400 hover:text-zinc-900"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>

        <div className="flex-1 space-y-8 overflow-y-auto pr-2">
          {/* LLM Section */}
          <div className="space-y-4">
            <label className="block text-[11px] font-bold text-zinc-400 uppercase tracking-widest">Architecture Intelligence (LLM)</label>
            <div className="space-y-3">
              <select 
                value={keys.llm_provider}
                onChange={(e) => setKeys({...keys, llm_provider: e.target.value})}
                className="w-full bg-zinc-50 border border-zinc-100 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-zinc-900 transition-all"
              >
                <option value="openai">OpenAI (GPT-4o/o1)</option>
                <option value="gemini">Google Gemini 1.5 Pro</option>
                <option value="anthropic">Anthropic Claude 3.5</option>
                <option value="deepseek">DeepSeek V3</option>
                <option value="groq">Groq (Llama 3.1)</option>
                <option value="openrouter">OpenRouter (Any Model)</option>
              </select>
              <input 
                type="password"
                placeholder="Enter API Key"
                value={keys.llm_key}
                onChange={(e) => setKeys({...keys, llm_key: e.target.value})}
                className="w-full bg-white border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-zinc-900 transition-all shadow-sm"
              />
            </div>
            <p className="text-[11px] text-zinc-400 font-light leading-relaxed">
              If provided, an LLM will autonomously design your RAG architecture based on dataset semantics. Otherwise, our deterministic engine will take over.
            </p>
          </div>

          {/* Vector DB Section */}
          <div className="space-y-4">
            <label className="block text-[11px] font-bold text-zinc-400 uppercase tracking-widest">Vector Store API (Cloud)</label>
            <div className="space-y-3">
              <select 
                value={keys.vector_db_provider}
                onChange={(e) => setKeys({...keys, vector_db_provider: e.target.value})}
                className="w-full bg-zinc-50 border border-zinc-100 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-zinc-900 transition-all"
              >
                <option value="none">None / Local (Chroma)</option>
                <option value="pinecone">Pinecone</option>
                <option value="weaviate">Weaviate</option>
                <option value="milvus">Milvus</option>
                <option value="qdrant">Qdrant</option>
                <option value="pgvector">PGVector</option>
                <option value="elasticsearch">Elasticsearch</option>
              </select>
              <input 
                type="password"
                placeholder="Enter Vector DB Key"
                value={keys.vector_db_key}
                onChange={(e) => setKeys({...keys, vector_db_key: e.target.value})}
                className="w-full bg-white border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-zinc-900 transition-all shadow-sm"
              />
            </div>
          </div>

          {/* Embedding Section */}
          <div className="space-y-4">
            <label className="block text-[11px] font-bold text-zinc-400 uppercase tracking-widest">Embeddings API (Optional)</label>
            <div className="space-y-3">
              <select 
                value={keys.embedding_provider}
                onChange={(e) => setKeys({...keys, embedding_provider: e.target.value})}
                className="w-full bg-zinc-50 border border-zinc-100 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-zinc-900 transition-all"
              >
                <option value="none">None / Local (BGE/MiniLM)</option>
                <option value="openai">OpenAI</option>
                <option value="cohere">Cohere</option>
                <option value="voyage">Voyage AI</option>
                <option value="huggingface">HuggingFace Enterprise</option>
              </select>
              <input 
                type="password"
                placeholder="Enter Embeddings Key"
                value={keys.embedding_key}
                onChange={(e) => setKeys({...keys, embedding_key: e.target.value})}
                className="w-full bg-white border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-zinc-900 transition-all shadow-sm"
              />
            </div>
          </div>
        </div>

        <div className="mt-10 pt-8 border-t border-zinc-100">
          <button 
            onClick={handleSave}
            className={`w-full py-4 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2 ${saved ? 'bg-emerald-500 text-white shadow-emerald-500/20 shadow-lg' : 'bg-zinc-900 text-white hover:bg-black shadow-zinc-900/20 shadow-lg active:scale-[0.98]'}`}
          >
            {saved ? (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
                Configurations Saved
              </>
            ) : "Save Infrastructure Settings"}
          </button>
          <p className="text-center text-[10px] text-zinc-400 mt-4 font-light">
            Keys are stored locally in your browser and never touch our servers persistently.
          </p>
        </div>
      </div>
    </>
  );
}
