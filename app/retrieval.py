import json
from pathlib import Path
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class KnowledgeBaseRetriever:
    def __init__(self, kb_path: Path):
        self.kb_path = kb_path
        self.documents: List[Dict[str, Any]] = []
        self.vectorizer: TfidfVectorizer = None
        self.tfidf_matrix = None
        self.load_and_index()

    def _prepare_document_text(self, doc: Dict[str, Any]) -> str:
        name = doc.get("name", "")
        category = doc.get("category", "")
        description = doc.get("description", "")
        features = " ".join(doc.get("features", []))
        keywords = " ".join(doc.get("keywords", []))
        ideal_for = doc.get("ideal_for", "")
        return f"{name} {category} {description} {features} {keywords} {ideal_for}"

    def load_and_index(self):
        with open(self.kb_path, "r", encoding="utf-8") as f:
            self.documents = json.load(f)

        corpus = [self._prepare_document_text(doc) for doc in self.documents]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def get_all(self) -> List[Dict[str, Any]]:
        return self.documents

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not query or not query.strip() or self.tfidf_matrix is None:
            return self.documents[:min(top_k, len(self.documents))]

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        ranked_indices = similarities.argsort()[::-1]

        scored_results = []
        for idx in ranked_indices:
            score = float(similarities[idx])
            rounded_score = round(score, 4)
            doc_copy = dict(self.documents[idx])
            doc_copy["relevance_score"] = rounded_score
            scored_results.append(doc_copy)

        # Drop results scoring below 0.02
        filtered = [doc for doc in scored_results if doc["relevance_score"] >= 0.02]

        if not filtered:
            # If nothing clears the floor, return the top 2 anyway so the LLM always has context
            return scored_results[:min(2, len(scored_results))]

        return filtered[:top_k]

_kb_path = Path(__file__).resolve().parent / "data" / "knowledge_base.json"
retriever = KnowledgeBaseRetriever(_kb_path)

def get_retriever() -> KnowledgeBaseRetriever:
    return retriever
