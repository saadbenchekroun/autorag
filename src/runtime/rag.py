import os
from typing import Any, Dict

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.core.config import config


class RAGRuntimeSystem:
    """Production runtime handling vector retrieval and language model generation."""

    def __init__(self) -> None:
        self.embeddings_cache: Dict[str, Any] = {}

    def _get_embedding_function(self, model_choice: str) -> Any:
        """Loads and caches required embedding model."""
        if model_choice not in self.embeddings_cache:
            if "openai" in model_choice:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    model_name = (
                        "text-embedding-3-small"
                        if "small" in model_choice
                        else "text-embedding-3-large"
                    )
                    self.embeddings_cache[model_choice] = OpenAIEmbeddings(model=model_name)
                    return self.embeddings_cache[model_choice]
                else:
                    model_choice = "huggingface_bge"  # fallback

            if "minilm" in model_choice or model_choice == "huggingface_minilm":
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
            elif "e5" in model_choice or "gte" in model_choice or "instructor" in model_choice:
                model_name = "BAAI/bge-small-en-v1.5"
            else:
                model_name = "BAAI/bge-small-en-v1.5"
            self.embeddings_cache[model_choice] = HuggingFaceEmbeddings(model_name=model_name)
        return self.embeddings_cache[model_choice]

    def generate_response(
        self, project_id: str, query_text: str, architecture_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes the actual local RAG generation loop using LangChain LCEL.

        Args:
            project_id: Deployment ID
            query_text: User question
            architecture_decision: Pipeline configuration dict

        Returns:
            Dict context and text.
        """
        persist_dir = os.path.join(
            os.getcwd(),
            config.get_nested("pipeline.ingestion.directories.chroma_db_dir", "chroma_db"),
            project_id,
        )
        if not os.path.exists(persist_dir):
            return {
                "error": "Vector database not found for this project. Please index documents first."
            }

        # 1. Load Embeddings and VectorStore
        embedding_model_choice = architecture_decision.get("embedding_model", "huggingface_minilm")
        embedding_function = self._get_embedding_function(embedding_model_choice)

        vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embedding_function)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        # 2. Retrieve Context
        try:
            docs = retriever.invoke(query_text)
            context_text = "\n\n".join([doc.page_content for doc in docs])
            context_used = [
                {
                    "text": doc.page_content[:200] + "...",
                    "source": doc.metadata.get("source", "unknown"),
                }
                for doc in docs
            ]
        except Exception as e:
            return {"error": f"Failed to retrieve context: {str(e)}"}

        # 3. LLM Generation
        # Fallback to pure retrieval mode if OpenAI Key is absent to keep it working without external apis
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            answer = (
                "API Key not found. Displaying retrieved context answering your query:\n\n"
                + context_text
            )
        else:
            llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
            template = """Answer the question based only on the following context:
{context}

Question: {question}

Answer:"""
            prompt = ChatPromptTemplate.from_template(template)

            chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )
            answer = chain.invoke(query_text)

        return {
            "answer": answer,
            "context_used": context_used,
            "metrics": {
                "chunks_retrieved": len(docs),
                "generation_mode": "OpenAI" if api_key else "Retrieval-Only Fallback",
            },
        }


rag_runtime = RAGRuntimeSystem()
