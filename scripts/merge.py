import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PDFS = DATA / "processed_pdfs"
PDFS.mkdir(exist_ok=True, parents=True)


def read_jsonl(p):
    with open(p, "r", encoding="utf-8") as jsonl:
        for line in jsonl:
            yield json.loads(line)


def read_json(p):
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def retrieve_texts(data, field="body_text"):
    return " ".join(section["text"] for section in data[field])


def build_lookup(processed_pdfs):
    parses = {}
    for pdf in processed_pdfs.rglob("*.json"):
        content = read_json(pdf)
        parses[pdf.stem] = retrieve_texts(content["pdf_parse"])
    return parses


def join_parses(processed_pdfs, jsonl):
    result = []
    parses = build_lookup(processed_pdfs)
    for line in read_jsonl(jsonl):
        line["content"] = parses.get(line["uuid"], [])
        result.append(line)
    return result


if __name__ == "__main__":
    result = join_parses(processed_pdfs=PDFS, jsonl=DATA / "data.jsonl")
    with open(DATA / "processed.jsonl", "w", encoding="utf-8") as out:
        for line in result:
            json.dump(line, out)
            out.write("\n")
