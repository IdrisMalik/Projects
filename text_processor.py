import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
nltk.download('punkt') # Download Punkt Sentence Tokenizer if not present

def preprocess_text(text):
    sentences = sent_tokenize(text)
    words = [word_tokenize(sentence) for sentence in sentences]
    return sentences, words