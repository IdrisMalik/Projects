from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import nltk
from nltk.tokenize import sent_tokenize
from transformers import BartTokenizer, BartForConditionalGeneration, pipeline

nltk.download('punkt')

def lsa_summarize(text, num_sentences=3):
    sentences = sent_tokenize(text)
    if not sentences:
        return ""
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(sentences)
    svd = TruncatedSVD(n_components=1, random_state=42)
    sentence_scores = svd.fit_transform(tfidf_matrix)
    ranked_sentences = sorted(((sentence_scores[i][0], i) for i in range(len(sentences))), reverse=True)
    top_sentence_indices = [i for score, i in ranked_sentences[:num_sentences]]
    summary = " ".join([sentences[i] for i in sorted(top_sentence_indices)])
    return summary


def bart_summarize(text):
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    summary = summarizer(text, max_length=150, min_length=50, do_sample=False)[0]['summary_text']
    return summary