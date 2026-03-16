import os
from typing import Any

from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from src.core.config import config
from src.core.exceptions import RetrievalError
from src.core.logging import get_logger
from src.core.schemas import ArchitectureDecision, ContextChunk, QueryMetrics, QueryResponse
from src.services.embedding_registry import get_embedding_function

logger = get_logger(__name__)

_DEFAULT_RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "3"))


class RAGRuntimeSystem:
    """Production runtime handling vector retrieval and language-model generation."""

    def generate_response(
        self,
        project_id: str,
        query_text: str,
        architecture_decision: ArchitectureDecision,
        k: int = _DEFAULT_RETRIEVAL_K,
    ) -> QueryResponse | dict[str, Any]:
        """Execute the RAG generation loop for *query_text* over *project_id*.

        Args:
            project_id: Deployment UUID referencing the indexed vector store.
            query_text: Natural-language user question.
            architecture_decision: Pipeline configuration used during indexing.
            k: Number of context chunks to retrieve (default: ``RETRIEVAL_K`` env var, 3).

        Returns:
            A :class:`QueryResponse` on success, or a plain error dict if the
            vector store is missing (so the API can return 404).
        """
        persist_dir = os.path.join(
            os.getcwd(),
            config.get_nested("pipeline.ingestion.directories.chroma_db_dir", "chroma_db"),
            project_id,
        )
        if not os.path.exists(persist_dir):
            return {
                "error": (
                    f"Vector database not found for project '{project_id}'. "
                    "Ensure indexing has completed before querying."
                )
            }

        # --- 1. Load embedding function and vector store ---
        embedding_function = get_embedding_function(architecture_decision.embedding_model)
        vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embedding_function)
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})

        # --- 2. Retrieve context chunks ---
        try:
            docs = retriever.invoke(query_text)
        except Exception as exc:
            raise RetrievalError(
                f"Failed to retrieve context for project '{project_id}': {exc}"
            ) from exc

        context_text = "\n\n".join(doc.page_content for doc in docs)
        context_used = [
            ContextChunk(
                text=doc.page_content[:200] + ("..." if len(doc.page_content) > 200 else ""),
                source=doc.metadata.get("source", "unknown"),
            )
            for doc in docs
        ]

        # --- 3. LLM generation (falls back to retrieval-only if no API key) ---
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning(
                "openai_key_missing_retrieval_only",
                project_id=project_id,
                chunks=len(docs),
            )
            answer = (
                "OpenAI API key not configured. Displaying retrieved context:\n\n" + context_text
            )
            generation_mode = "retrieval_only"
        else:
            llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=api_key)
            template = (
                "Answer the question based only on the following context:\n"
                "{context}\n\n"
                "Question: {question}\n\n"
                "Answer:"
            )
            prompt = ChatPromptTemplate.from_template(template)
            chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )
            answer = chain.invoke(query_text)
            generation_mode = "openai"

        logger.info(
            "rag_response_generated",
            project_id=project_id,
            chunks_retrieved=len(docs),
            mode=generation_mode,
        )

        return QueryResponse(
            answer=answer,
            context_used=context_used,
            metrics=QueryMetrics(
                chunks_retrieved=len(docs),
                generation_mode=generation_mode,
            ),
        )


rag_runtime = RAGRuntimeSystem()
