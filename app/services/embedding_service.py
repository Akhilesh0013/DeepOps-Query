import tiktoken
from openai import OpenAI

from app.config import settings
from app.services.query_cache_service import query_cache

openai_client = OpenAI(api_key=settings.openai_api_key)

# text-embedding-3-* models use cl100k_base and accept at most 8192 tokens per input.
_MAX_INPUT_TOKENS = 8191
_EMBED_BATCH_SIZE = 128
_encoding = tiktoken.get_encoding("cl100k_base")


def _truncate_to_token_limit(text: str) -> str:
    tokens = _encoding.encode(text)
    if len(tokens) <= _MAX_INPUT_TOKENS:
        return text
    return _encoding.decode(tokens[:_MAX_INPUT_TOKENS])


def embed_texts(
    texts: list[str],
    model: str | None = None,
    use_cache: bool = True,
) -> list[list[float]]:
    if not texts:
        return []
    if model is None:
        model = settings.embedding_model

    results: list[list[float] | None] = [None] * len(texts)
    miss_indices: list[int] = []
    miss_texts: list[str] = []

    for i, text in enumerate(texts):
        cached = query_cache.get_embedding(text) if use_cache else None
        if cached is not None:
            results[i] = cached

        else:
            miss_indices.append(i)
            miss_texts.append(text)

    for start in range(0, len(miss_texts), _EMBED_BATCH_SIZE):
        batch_texts = miss_texts[start : start + _EMBED_BATCH_SIZE]
        batch_indices = miss_indices[start : start + _EMBED_BATCH_SIZE]

        # OpenAI rejects empty strings and inputs over the token limit, which would
        # otherwise fail the whole batch — sanitize each input before sending.
        prepared = [_truncate_to_token_limit(t) if t.strip() else " " for t in batch_texts]

        response = openai_client.embeddings.create(input=prepared, model=model)
        for item in response.data:
            original_idx = batch_indices[item.index]
            vector = item.embedding
            results[original_idx] = vector
            if use_cache:
                query_cache.set_embedding(miss_texts[start + item.index], vector)

    return [r for r in results if r is not None]
