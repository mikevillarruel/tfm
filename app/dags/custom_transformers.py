import re

import pandas as pd
import spacy_stanza
from sklearn.base import BaseEstimator, TransformerMixin


class Cleaner(BaseEstimator, TransformerMixin):
    """
    A custom transformer to lowercase, remove URLs, mentions, punctuation,
    special characters and numbers from text in a column in a DataFrame.
    """

    def __init__(self):
        pass

    def fit(self, X: pd.Series, y=None):
        return self

    def transform(self, X: pd.Series):
        # Lowercase the text
        X = X.str.lower()

        # Remove URLs
        pattern = r"http\S+"
        X = X.apply(
            lambda tweet: re.sub(pattern, " ", tweet).strip())

        # Remove mentions
        pattern = r"@\S+"
        X = X.apply(
            lambda tweet: re.sub(pattern, " ", tweet).strip())

        # Remove punctuation and special characters
        pattern = r"[^\w]"
        X = X.apply(
            lambda tweet: re.sub(pattern, " ", tweet).strip())

        # Remove numbers
        pattern = r"\d+"
        X = X.apply(
            lambda tweet: re.sub(pattern, " ", tweet).strip())

        return X


class StopWordsRemover(BaseEstimator, TransformerMixin):
    """
    A custom transformer to remove stop words from a column in a DataFrame.
    """

    def __init__(self, stop_words: list):
        self.stop_words = stop_words

    def fit(self, X: pd.Series, y=None):
        return self

    def transform(self, X: pd.Series):
        # Split the text into words
        pattern = r"\s+"
        X = X.str.split(pat=pattern, regex=True)

        # Remove stop words
        X = X.apply(lambda tweet: " ".join(
            [word for word in tweet if word not in self.stop_words]))

        return X


class Lemmatizer(BaseEstimator, TransformerMixin):
    """
    A custom transformer to lemmatize a column in a DataFrame.
    Require stanza library to be installed and the spanish model to be downloaded.
    Example:    
        import spacy_stanza
        stanza.download("es")
    """

    def __init__(self):
        pass

    def fit(self, X: pd.Series, y=None):
        return self

    def transform(self, X: pd.Series):
        # Lemmatize the text spanish
        lemmatizer = spacy_stanza.load_pipeline("es", verbose=False)
        X = X.apply(lambda tweet: " ".join(
            [word.lemma_ for word in lemmatizer(tweet)]))
        return X
