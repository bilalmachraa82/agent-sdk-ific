"""
Qdrant vector store service with multi-tenant support.
Manages document embeddings and similarity search for PT2030 regulations.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, FieldCondition, MatchValue, Filter
import hashlib

from backend.core.config import settings

logger = logging.getLogger(__name__)


class Document:
    """Represents a document for embedding and storage."""

    def __init__(
        self,
        content: str,
        doc_type: str,
        source: str,
        metadata: Dict[str, Any] = None,
        doc_id: str = None
    ):
        self.id = doc_id or str(uuid4())
        self.content = content
        self.doc_type = doc_type  # e.g., 'regulation', 'template', 'example'
        self.source = source  # e.g., 'pt2030_official', 'prr_guide'
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()
        self.content_hash = hashlib.sha256(content.encode()).hexdigest()


class EmbeddingModel:
    """Wrapper for embedding model (BGE-M3)."""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        """Initialize embedding model."""
        self.model_name = model_name
        logger.info(f"Embedding model: {model_name}")

        # Note: In production, load the actual model
        # from sentence_transformers import SentenceTransformer
        # self.model = SentenceTransformer(model_name)

        self.model = None  # Placeholder for development

    def embed(self, text: str) -> List[float]:
        """
        Create embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1024 dimensions)
        """
        if not self.model:
            # Placeholder: return random embedding for development
            # In production, use actual model: embedding = self.model.encode([text])
            logger.warning("Using placeholder embeddings (set model in production)")
            return np.random.randn(settings.qdrant_vector_size).tolist()

        embedding = self.model.encode([text])[0]
        return embedding.tolist()


class QdrantService:
    """Multi-tenant vector store service."""

    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.embedding_model = EmbeddingModel()
        self.collection_name = settings.qdrant_collection_name
        self.vector_size = settings.qdrant_vector_size

    async def connect(self):
        """Connect to Qdrant server."""
        try:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=settings.qdrant_timeout
            )
            # Test connection
            self.client.get_collections()
            logger.info(f"Connected to Qdrant at {settings.qdrant_url}")
            await self._ensure_collection_exists()
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    async def _ensure_collection_exists(self):
        """Create collection if it doesn't exist."""
        try:
            # Check if collection exists
            try:
                self.client.get_collection(self.collection_name)
                logger.info(f"Collection '{self.collection_name}' already exists")
                return
            except Exception:
                pass

            # Create collection with payload schema for multi-tenant filtering
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=Models.VectorParams(
                    size=self.vector_size,
                    distance=Models.Distance.COSINE
                ),
                payload_schema_config={
                    "tenant_id": Models.PayloadIndexedFieldType(
                        type=Models.PayloadSchemaType.KEYWORD
                    ),
                    "doc_type": Models.PayloadIndexedFieldType(
                        type=Models.PayloadSchemaType.KEYWORD
                    ),
                    "source": Models.PayloadIndexedFieldType(
                        type=Models.PayloadSchemaType.KEYWORD
                    ),
                }
            )
            logger.info(f"Created collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise

    def _create_filter(self, tenant_id: str, doc_type: str = None) -> Filter:
        """
        Create Qdrant filter for tenant isolation.

        Args:
            tenant_id: Tenant ID to filter by
            doc_type: Optional document type filter

        Returns:
            Qdrant Filter object
        """
        conditions = [
            FieldCondition(
                key="tenant_id",
                match=MatchValue(value=tenant_id)
            )
        ]

        if doc_type:
            conditions.append(
                FieldCondition(
                    key="doc_type",
                    match=MatchValue(value=doc_type)
                )
            )

        return Filter(must=conditions)

    async def index_documents(
        self,
        documents: List[Document],
        tenant_id: str
    ) -> bool:
        """
        Index documents into vector store with tenant isolation.

        Args:
            documents: Documents to index
            tenant_id: Tenant ID for isolation

        Returns:
            True if successful
        """
        if not self.client:
            return False

        try:
            points = []

            for doc in documents:
                # Create embedding
                embedding = self.embedding_model.embed(doc.content)

                # Create payload with tenant_id for isolation
                payload = {
                    "tenant_id": tenant_id,
                    "doc_id": doc.id,
                    "doc_type": doc.doc_type,
                    "source": doc.source,
                    "content": doc.content,
                    "content_hash": doc.content_hash,
                    "metadata": doc.metadata,
                    "created_at": doc.created_at,
                    "indexed_at": datetime.utcnow().isoformat()
                }

                point = PointStruct(
                    id=hash(f"{tenant_id}:{doc.id}") % (10 ** 10),  # Unique ID
                    vector=embedding,
                    payload=payload
                )
                points.append(point)

            # Upsert points (insert or update)
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            logger.info(f"Indexed {len(documents)} documents for tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            return False

    async def search(
        self,
        query: str,
        tenant_id: str,
        doc_type: str = None,
        limit: int = 5,
        score_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents with tenant isolation.

        Args:
            query: Search query text
            tenant_id: Tenant ID for isolation
            doc_type: Optional document type filter
            limit: Maximum results to return
            score_threshold: Minimum similarity score (uses settings default if None)

        Returns:
            List of search results with scores and metadata
        """
        if not self.client:
            return []

        try:
            # Create query embedding
            query_embedding = self.embedding_model.embed(query)

            # Create tenant-filtered search
            filter_obj = self._create_filter(tenant_id, doc_type)
            threshold = score_threshold or settings.qdrant_similarity_threshold

            # Search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=filter_obj,
                limit=limit,
                score_threshold=threshold,
                with_payload=True
            )

            # Format results
            results = []
            for hit in search_result:
                results.append({
                    "id": hit.payload.get("doc_id"),
                    "content": hit.payload.get("content"),
                    "doc_type": hit.payload.get("doc_type"),
                    "source": hit.payload.get("source"),
                    "metadata": hit.payload.get("metadata", {}),
                    "similarity_score": hit.score,
                    "created_at": hit.payload.get("created_at")
                })

            logger.debug(f"Search for '{query}' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def delete_document(self, doc_id: str, tenant_id: str) -> bool:
        """
        Delete a document from the index.

        Args:
            doc_id: Document ID to delete
            tenant_id: Tenant ID for verification

        Returns:
            True if successful
        """
        if not self.client:
            return False

        try:
            # Delete by filter (tenant_id + doc_id)
            filter_obj = Filter(
                must=[
                    FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=tenant_id)
                    ),
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=filter_obj
            )

            logger.info(f"Deleted document {doc_id} for tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    async def clear_tenant(self, tenant_id: str) -> bool:
        """
        Delete all documents for a tenant.
        Use with caution on large collections.

        Args:
            tenant_id: Tenant ID to clear

        Returns:
            True if successful
        """
        if not self.client:
            return False

        try:
            filter_obj = Filter(
                must=[
                    FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=tenant_id)
                    )
                ]
            )

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=filter_obj
            )

            logger.info(f"Cleared all documents for tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear tenant: {e}")
            return False


# Global Qdrant service instance
qdrant_service = QdrantService()


async def init_qdrant():
    """Initialize Qdrant service."""
    await qdrant_service.connect()


async def close_qdrant():
    """Close Qdrant service."""
    # Qdrant doesn't require explicit disconnect
    pass
