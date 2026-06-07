"""MedCPT encoders on the M1 (MPS).

Embeddings are the [CLS] vector, L2-normalized so cosine == dot (matches MedCPT's
inner-product training while keeping PQ well-behaved). The Article encoder consumes
[title, abstract] pairs; the Query encoder consumes the question string.
"""
import torch
from transformers import AutoTokenizer, AutoModel
from . import config


class _Encoder:
    def __init__(self, name, maxlen):
        self.dev = config.device()
        self.tok = AutoTokenizer.from_pretrained(name, revision=config.MEDCPT_REVISION)
        self.model = AutoModel.from_pretrained(name, revision=config.MEDCPT_REVISION)
        self.model = self.model.to(self.dev).eval()
        self.maxlen = maxlen

    @torch.no_grad()
    def encode(self, items, batch_size=64):
        out = []
        for i in range(0, len(items), batch_size):
            chunk = items[i:i + batch_size]
            enc = self.tok(chunk, truncation=True, padding=True,
                           max_length=self.maxlen, return_tensors="pt").to(self.dev)
            emb = self.model(**enc).last_hidden_state[:, 0, :]          # [CLS]
            emb = torch.nn.functional.normalize(emb, p=2, dim=1)        # cosine-ready
            out.append(emb.float().cpu())
        return torch.cat(out).numpy()


_article = None
_query = None


def article_encoder():
    global _article
    if _article is None:
        _article = _Encoder(config.ARTICLE_ENCODER, config.ART_MAXLEN)
    return _article


def query_encoder():
    global _query
    if _query is None:
        _query = _Encoder(config.QUERY_ENCODER, config.QRY_MAXLEN)
    return _query


def embed_articles(records):
    pairs = [[r["title"] or "", r["abstract"] or ""] for r in records]
    return article_encoder().encode(pairs)


def embed_query(text):
    return query_encoder().encode([text])[0]
