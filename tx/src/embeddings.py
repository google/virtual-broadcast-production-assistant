from config import SENTENCE_TRANSFORMERS_LOCAL
from transformers import AutoTokenizer, AutoModel
import torch

# Load tokenizer and model without joblib
tokenizer = AutoTokenizer.from_pretrained(
    SENTENCE_TRANSFORMERS_LOCAL,
    local_files_only=True
)
model = AutoModel.from_pretrained(
    SENTENCE_TRANSFORMERS_LOCAL,
    local_files_only=True
)
model.eval()
# Force CPU to avoid MPS-related shutdown segmentation faults on Mac
device = torch.device('cpu')
model.to(device)

def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Compute embeddings using Hugging Face Transformers + PyTorch.
    """
    enc = tokenizer(
        texts,
        padding=True,
        truncation=True,
        return_tensors='pt'
    ).to(device)
    with torch.no_grad():
        out = model(**enc)
        hidden = out.last_hidden_state
        mask = enc['attention_mask'].unsqueeze(-1).expand(hidden.size()).float()
        summed = (hidden * mask).sum(dim=1)
        counts = mask.sum(dim=1)
        return (summed / counts).cpu().tolist()


def generate_embeddings(entries):
    """
    Compute embeddings for a list of entries.

    Args:
        entries: list of dicts with keys 'documentId' and 'content'.

    Returns:
        List of dicts with keys 'documentId' and 'embeddings'.
    """
    # Extract texts for embedding
    texts = [entry.get('content', '') for entry in entries]
    # Compute embeddings for all texts at once
    vectors = embed_texts(texts)
    # Pair each embedding with its document ID
    result = []
    for entry, vector in zip(entries, vectors):
        result.append({
            'documentId': entry['documentId'],
            'embeddings': vector
        })
    return result
