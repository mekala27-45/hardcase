# Third-party provenance

The Hardcase code license does not replace dataset or model terms.

SciFact upstream claims and evidence annotations are described under CC BY 4.0; abstracts are described under ODC-By 1.0. Retain the [upstream notice](https://github.com/allenai/scifact/blob/master/LICENSE.md). The captured notice hash and retrieval timestamp are in evidence/preparation/source.json.

The BEIR [SciFact corpus card](https://huggingface.co/datasets/BeIR/scifact) and [qrels card](https://huggingface.co/datasets/BeIR/scifact-qrels) carry their own CC-BY-SA-4.0 package metadata. Preserve those cards separately. Captured bytes are retained under data/notices in the exact frozen input archive. Do not collapse these distinct provenance layers into a blanket code license.

The pinned [all-MiniLM-L6-v2 student](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) and [MS MARCO MiniLM teacher](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) identify Apache-2.0 in their model cards. Exact revisions and captured file hashes are in requests/model-lock.json. Derived model artifacts retain the original model provenance and the experiment-specific limitations.

Fahkwang, Varta and M PLUS Code Latin are supplied through pinned Fontsource packages with their included font licenses. The frontend lock records exact package integrity values. Preserve their distribution notices in built font assets.

Authored setup, resume and protocol fixtures are synthetic operational examples. They are not SciFact observations, benchmark qrels or evidence of retrieval quality.
