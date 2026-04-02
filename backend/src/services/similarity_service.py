"""
Similarity Service for detecting duplicate news articles
"""
from typing import List, Optional
import logging
import hashlib
from src.config import settings

# Optional imports for embedding-based similarity
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    np = None

logger = logging.getLogger(__name__)


class SimilarityService:
    """Service for calculating text similarity"""

    def __init__(self):
        self.model = None
        self.threshold = settings.SIMILARITY_THRESHOLD
        self.load_model()

    def load_model(self):
        """Load sentence transformer model"""
        if not EMBEDDINGS_AVAILABLE:
            logger.warning("[WARNING] sentence-transformers not available. Using hash-based duplicate detection only.")
            return

        try:
            # Using multilingual model for Turkish support
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("[SUCCESS] Sentence transformer model loaded")
        except Exception as e:
            logger.error(f"[ERROR] Failed to load similarity model: {e}")

    def generate_hash(self, title: str, content: str) -> str:
        """
        Generate a simple hash for quick duplicate detection
        """
        combined = f"{title.lower().strip()}{content.lower().strip()}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()

    def get_embedding(self, text: str) -> Optional['np.ndarray']:
        """
        Generate embedding for text
        """
        if not EMBEDDINGS_AVAILABLE or not self.model:
            logger.warning("[WARNING] Similarity model not loaded")
            return None

        try:
            # Limit text length to avoid memory issues
            text = text[:1000]
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"[ERROR] Failed to generate embedding: {e}")
            return None

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts
        Returns: similarity score between 0 and 1
        """
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)

        if embedding1 is None or embedding2 is None:
            return 0.0

        try:
            # Calculate cosine similarity
            similarity = cosine_similarity(
                embedding1.reshape(1, -1),
                embedding2.reshape(1, -1)
            )[0][0]

            return float(similarity)
        except Exception as e:
            logger.error(f"[ERROR] Failed to calculate similarity: {e}")
            return 0.0

    def calculate_embedding_similarity(self, embedding1, embedding2) -> float:
        """
        Calculate cosine similarity between two embedding vectors
        Returns: similarity score between 0 and 1
        """
        if not EMBEDDINGS_AVAILABLE or embedding1 is None or embedding2 is None:
            return 0.0

        try:
            similarity = cosine_similarity(
                embedding1.reshape(1, -1),
                embedding2.reshape(1, -1)
            )[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"[ERROR] Failed to calculate embedding similarity: {e}")
            return 0.0

    def is_duplicate(self, text1: str, text2: str, threshold: Optional[float] = None) -> bool:
        """
        Check if two texts are duplicates based on similarity threshold
        """
        if threshold is None:
            threshold = self.threshold

        similarity = self.calculate_similarity(text1, text2)
        is_dup = similarity >= threshold

        if is_dup:
            logger.info(f"[DUPLICATE] Similarity: {similarity:.2%}")

        return is_dup

    def find_similar_articles(
        self,
        article_embedding,
        existing_embeddings: List,
        threshold: Optional[float] = None
    ) -> List[int]:
        """
        Find similar articles from existing embeddings
        Returns: List of indices of similar articles
        """
        if not EMBEDDINGS_AVAILABLE:
            return []

        if threshold is None:
            threshold = self.threshold

        if not existing_embeddings:
            return []

        try:
            # Calculate similarities with all existing articles
            similarities = cosine_similarity(
                article_embedding.reshape(1, -1),
                np.array(existing_embeddings)
            )[0]

            # Find articles above threshold
            similar_indices = np.where(similarities >= threshold)[0].tolist()

            return similar_indices

        except Exception as e:
            logger.error(f"[ERROR] Failed to find similar articles: {e}")
            return []


# Global similarity service instance
similarity_service = SimilarityService()
