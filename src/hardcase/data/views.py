from hardcase.contracts import digest, require
from .capture import normalize


def document_view(document, tokenizer, max_length=256):
    full = normalize(document["title"]) + "\n\n" + normalize(document["text"])
    encoded = tokenizer(full, truncation=True, max_length=max_length, return_offsets_mapping=True, add_special_tokens=True)
    offsets = encoded.pop("offset_mapping")
    end = max((b for a, b in offsets), default=0)
    visible = full[:end]
    again = tokenizer(visible, truncation=True, max_length=max_length, add_special_tokens=True)
    require(again["input_ids"] == encoded["input_ids"], "VISIBLE_TEXT_TOKEN_MISMATCH")
    return {"id": document["_id"], "title": document["title"], "text": full, "visible_text": visible, "encoded_span": [0, end], "truncated": end < len(full), "token_count": len(encoded["input_ids"]), "token_digest": digest(encoded["input_ids"]), "raw_text_digest": digest(document["text"]), "text_digest": digest(full), "visible_digest": digest(visible), "notice": "SciFact abstracts: ODC-By 1.0; packaged BEIR notices retained"}
