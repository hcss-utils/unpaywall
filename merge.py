import json
from pathlib import Path


root = Path(__file__).resolve().parent
data = root / "data"
pdfs = data / "processed_pdfs"


def read_jsonl(p):
    with open(p, "r", encoding="utf-8") as jsonl:
        for line in jsonl:
            yield json.loads(line)


def read_json(p):
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def retrieve_texts(data, field="body_text"):
    """Parse 'body_text' or 'abstract' fields extracting raw texts."""
    return " ".join(section["text"] for section in data[field])


def join_parses(processed_pdfs, jsonl):
    texts = []
    for pdf in processed_pdfs.rglob("*.json"):
        content = read_json(pdf)
        texts.append(
            {
                "uuid": pdf.stem,
                "body_text": retrieve_texts(content["pdf_parse"]),
            }
        )

    result = []
    for line in read_jsonl(jsonl):
        for text in texts:
            if line["uuid"] == text["uuid"]:
                line["content"] = text["body_text"]
                print("matched")
        result.append(line)

    return result


if __name__ == "__main__":
    result = join_parses(processed_pdfs=pdfs, jsonl=data / "data.jsonl")
    with open(data / "processed.jsonl", "w", encoding="utf-8") as out:
        for line in result:
            json.dump(line, out)
            out.write("\n")
