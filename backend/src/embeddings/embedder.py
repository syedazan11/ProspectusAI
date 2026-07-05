from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Generates embeddings for text using a SentenceTransformer model.
    """

    def __init__(self):

        self.model = SentenceTransformer(
            "BAAI/bge-small-en-v1.5"
        )

    def embed(self, text: str):

        return self.model.encode(
            text,
            normalize_embeddings=True,
        )

    def embed_batch(self, texts: list[str]):

        return self.model.encode(
            texts,
            normalize_embeddings=True,
        )
    def embed_query(self, query: str):
        """
        Generates an embedding for a search query.
        """

        return self.embed(query)