from core.embeddings import HashEmbeddingBackend, cosine_similarity


def test_similar_phrases_score_higher_than_unrelated() -> None:
    backend = HashEmbeddingBackend()
    sonic = backend.embed("sonic crossworlds")
    close = backend.embed("sonic racing")
    other = backend.embed("jellyfin rick and morty")
    assert backend.similarity(sonic, close) > backend.similarity(sonic, other)


def test_cosine_identical() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
