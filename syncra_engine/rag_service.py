import os
import sys
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Ensure root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from syncra_engine.db import get_connection
except ImportError:
    from db import get_connection



class LegalRAGService:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r'(?u)\b\w+\b',
            sublinear_tf=True
        )
        self.articles = []
        self.tfidf_matrix = None
        self.reload_corpus()

    def reload_corpus(self):
        """Loads all legal articles from SQLite database and computes TF-IDF index."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, law_code, article_num, title, category, official_text_ar, official_text_fr, practical_implication, keywords FROM legal_articles")
        rows = cursor.fetchall()
        conn.close()

        self.articles = [dict(row) for row in rows]
        
        # Build search document for each article combining title, texts, category, and keywords
        corpus_texts = []
        for art in self.articles:
            doc = f"{art['title']} {art['category']} {art['law_code']} {art['article_num']} {art['official_text_ar']} {art['official_text_fr']} {art['practical_implication']} {art['keywords']}"
            corpus_texts.append(doc)

        if corpus_texts:
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus_texts)
        else:
            self.tfidf_matrix = None

    def query(self, user_prompt: str, top_k: int = 3):
        """Queries the legal corpus using cosine similarity over TF-IDF vectors."""
        if not self.articles or self.tfidf_matrix is None:
            self.reload_corpus()

        if not user_prompt.strip():
            return {
                "query": user_prompt,
                "matches_count": 0,
                "results": [],
                "ai_synthesis": "يرجى كتابة نص السؤال القانوني للبحث في المتن التشريعي الجزائري."
            }

        # Vectorize query
        query_vec = self.vectorizer.transform([user_prompt])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        # Rank matches
        ranked_indices = np.argsort(similarities)[::-1]
        
        results = []
        for idx in ranked_indices[:top_k]:
            score = float(similarities[idx])
            # If similarity is above minimal threshold
            if score > 0.05 or len(results) == 0:
                art = self.articles[idx].copy()
                art['similarity_score'] = round(score, 4)
                art['relevance_percentage'] = min(round(score * 125, 1), 99.8) if score > 0.1 else round(score * 100, 1)
                results.append(art)

        # AI Synthesis Construction
        if results and results[0]['similarity_score'] > 0.08:
            top_match = results[0]
            ai_synthesis = (
                f"بناءً على المتن التشريعي الجزائري المعتمد ({top_match['law_code']} - {top_match['article_num']}):\n\n"
                f"📌 الموضوع: {top_match['title']}\n"
                f"📜 الحكم القانوني: {top_match['official_text_ar']}\n\n"
                f"⚙️ الأثر المباشر على تسيير الموارد البشرية والأجور: {top_match['practical_implication']}\n\n"
                f"💡 الإجراء الموصى به: يُرجى تسجيل العملية مع إرفاق المرجع {top_match['article_num']} لضمان المطابقة الكاملة مع مفتشية العمل ومصالح الضمان الاجتماعي."
            )
        else:
            ai_synthesis = (
                f"لم يتم العثور على تطابق قطعي مع السؤال: '{user_prompt}'. "
                "يرجى توضيح المصطلح القانوني (مثال: 'ساعات إضافية'، 'عطلة مرضية'، 'إنهاء فترة التجربة'، 'حساب STC'، 'سلم ضريبة IRG')."
            )

        return {
            "query": user_prompt,
            "engine": "SYNCRA Legal RAG AI (Deterministic Scikit-Learn TF-IDF + Cosine Retrieval)",
            "matches_count": len(results),
            "results": results,
            "ai_synthesis": ai_synthesis
        }

rag_service = LegalRAGService()

if __name__ == "__main__":
    test_queries = [
        "كيف يتم حساب الساعات الإضافية وما هي نسبتها؟",
        "كم نسبة تعويض العطلة المرضية في الضمان الاجتماعي cnas؟",
        "ما هي المادة التي تنظم مخالصة رصيد كل حساب stc؟"
    ]
    for q in test_queries:
        res = rag_service.query(q)
        print(f"\n--- QUERY: {q} ---")
        print(f"Top Match: {res['results'][0]['title']} ({res['results'][0]['relevance_percentage']}%)")
        print(f"Law: {res['results'][0]['law_code']} - {res['results'][0]['article_num']}")
