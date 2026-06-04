import sys
from unittest.mock import MagicMock

# Only mock the heavy, network-bound sentence_transformers module.
# This prevents downloading of the embedding model during unit testing.
class MockSentenceTransformer(MagicMock):
    def encode(self, sentences, *args, **kwargs):
        # Return dummy embeddings matching the length of the sentences
        import numpy as np
        return np.random.randn(len(sentences), 384)

mock_module = MagicMock()
mock_module.SentenceTransformer = MockSentenceTransformer
sys.modules['sentence_transformers'] = mock_module
