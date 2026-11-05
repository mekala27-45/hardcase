import csv
import io
import json
import stat
import unicodedata
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from hardcase.contracts import Stage, atomic_json, digest, file_digest, finite, load_json, require, utcnow

NOTICES = {
    "upstream-scifact": "https://raw.githubusercontent.com/allenai/scifact/master/LICENSE.md",
    "beir-scifact-card": "https://huggingface.co/datasets/BeIR/scifact/raw/main/README.md",
    "beir-qrels-card": "https://huggingface.co/datasets/BeIR/scifact-qrels/raw/main/README.md",
}


def normalize(text):
    require(isinstance(text, str), "TEXT_NOT_STRING")
    return unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n").strip()


def safe_members(archive, max_bytes=100 * 1024 * 1024):
    names = set()
    total = 0
    rows = []
    for item in archive.infolist():
        path = PurePosixPath(item.filename)
        require(not path.is_absolute() and ".." not in path.parts and "\\" not in item.filename and ":" not in item.filename, "UNSAFE_ARCHIVE_PATH")
        require(not stat.S_ISLNK(item.external_attr >> 16), "ARCHIVE_SYMLINK")
        require(item.filename not in names, "DUPLICATE_ARCHIVE_NAME")
        names.add(item.filename)
        total += item.file_size
        require(total <= max_bytes, "ARCHIVE_TOO_LARGE")
        rows.append({"name": item.filename, "bytes": item.file_size, "crc": item.CRC})
    for name in ("corpus.jsonl", "queries.jsonl", "qrels/train.tsv", "qrels/test.tsv"):
        require(f"scifact/{name}" in names, "MISSING_ARCHIVE_MEMBER")
    return rows


def records(raw, kind):
    result = {}
    for line in raw.decode("utf-8").splitlines():
        row = json.loads(line)
        require(isinstance(row.get("_id"), str) and row["_id"], "INVALID_ID")
        require(row["_id"] not in result, "DUPLICATE_ID")
        require(isinstance(row.get("text"), str), "INVALID_TEXT")
        if kind == "corpus":
            require(isinstance(row.get("title"), str), "INVALID_TITLE")
        result[row["_id"]] = row
    require(bool(result), "EMPTY_INVENTORY")
    return result


def judgments(raw, queries, corpus):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter="\t")
    require(reader.fieldnames == ["query-id", "corpus-id", "score"], "QREL_SCHEMA")
    rows, seen = [], set()
    for row in reader:
        query, document, score = row["query-id"], row["corpus-id"], float(row["score"])
        require(query in queries and document in corpus, "QREL_REFERENCE")
        require(finite(score) and score >= 0, "QREL_SCORE")
        require((query, document) not in seen, "DUPLICATE_QREL")
        seen.add((query, document))
        rows.append({"query_id": query, "document_id": document, "score": score})
    require(bool(rows), "EMPTY_QRELS")
    return rows


def fetch(url, destination, maximum=50 * 1024 * 1024):
    request = urllib.request.Request(url, headers={"User-Agent": "hardcase-research/0.1"})
    with urllib.request.urlopen(request, timeout=90) as response:
        require(response.status == 200, "DOWNLOAD_STATUS")
        payload = response.read(maximum + 1)
    require(len(payload) <= maximum, "DOWNLOAD_TOO_LARGE")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return {"url": url, "retrieved_at": utcnow(), "status": 200, "sha256": file_digest(destination), "bytes": len(payload)}


def capture(root=Path(".")):
    root = Path(root)
    config = load_json(root / "requests/experiment.json")
    raw = root / "data/raw"
    with Stage(root / "artifacts/preparation", "capture", {"config": digest(config)}) as stage:
        archive_path = raw / "scifact.zip"
        source = fetch(config["source_url"], archive_path)
        notices = {name: fetch(url, root / "data/notices" / f"{name}.md", 1024 * 1024) for name, url in NOTICES.items()}
        with zipfile.ZipFile(archive_path) as archive:
            inventory = safe_members(archive)
            corpus = records(archive.read("scifact/corpus.jsonl"), "corpus")
            queries = records(archive.read("scifact/queries.jsonl"), "queries")
            train = judgments(archive.read("scifact/qrels/train.tsv"), queries, corpus)
            test = judgments(archive.read("scifact/qrels/test.tsv"), queries, corpus)
        train_ids = sorted({r["query_id"] for r in train})
        test_ids = sorted({r["query_id"] for r in test})
        observed = {"documents": len(corpus), "train_queries": len(train_ids), "test_queries": len(test_ids), "train_qrels": len(train), "test_qrels": len(test)}
        stage.update(source=source, notices=notices, observed=observed, archive_inventory=inventory)
        require(observed == config["expected"], "SOURCE_INVENTORY_MISMATCH")
        require(not set(train_ids) & set(test_ids), "SOURCE_SPLIT_ID_OVERLAP")
        atomic_json(root / "data/processed/corpus.json", corpus)
        atomic_json(root / "data/processed/train-queries.json", {q: queries[q] for q in train_ids})
        atomic_json(root / "data/processed/train-qrels.json", train)
        # This boundary exposes text, never final test relevance, to leakage audit.
        atomic_json(root / "data/audit/test-query-text.json", {q: queries[q]["text"] for q in test_ids})
        atomic_json(root / "data/vault/test-queries.json", {q: queries[q] for q in test_ids})
        atomic_json(root / "data/vault/test-qrels.json", test)
        atomic_json(root / "data/manifests/source.json", {"source": source, "notices": notices, "observed": observed, "train_ids": train_ids, "test_ids": test_ids, "corpus_digest": digest(corpus), "train_labels_digest": digest(train), "test_labels_digest": digest(test), "redistribution": "raw third-party bytes excluded from public source; notices retained by provenance"})


if __name__ == "__main__":
    capture()
