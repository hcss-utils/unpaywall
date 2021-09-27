import ssl
import csv
import json
import logging
from pathlib import Path
import httpx


EMAIL = "hcssteamukraine@gmail.com"
BASE_URL = "https://api.unpaywall.org/v2"
USELESS_FIELDS = ["first_oa_location", "oa_locations", "oa_locations_embargoed"]

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PDFS = DATA / "raw_pdfs"
PDFS.mkdir(exist_ok=True, parents=True)


def create_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(ROOT / f"{name}.log")
    fh.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


logger = create_logger("unpaywall")


def raise_on_4xx_5xx(response):
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        logger.info(f"Errored ({response.status_code}): {response.url}")
    except httpx.ConnectError:
        logger.info(f"ConnectError")


def log_request(request):
    logger.info(
        f"Request event hook: {request.method} {request.url} - Waiting for response"
    )


def log_response(response):
    request = response.request
    logger.info(
        f"Response event hook: {request.method} {request.url} - Status {response.status_code}"
    )


def read_csv(p):
    with open(p, newline="", encoding="ISO-8859-1") as csvfile:
        csv_reader = csv.DictReader(csvfile, delimiter=",")
        for row in csv_reader:
            yield row["doi"], row["uuid"]


def stream_response(session, endpoint):
    with session.stream("GET", endpoint) as response:
        for chunk in response.iter_bytes():
            yield chunk


def download(session, pdf_link, filename):
    with open(PDFS / f"{filename}.pdf", "wb") as output:
        for chunk in stream_response(session, pdf_link):
            output.write(chunk)


def update_jsonl(data, filepath):
    with open(DATA / filepath, "a", encoding="utf-8") as out:
        json.dump(data, out)
        out.write("\n")

def fetch(dois):

    _attempted_uuids = []
    with open(DATA / "traceback_uuids.jsonl", "r") as lines:
        for line in lines:
            _attempted_uuids.append(json.loads(line)["row"])

    hooks = {
        # "request": [log_request], 
        "response": [
            raise_on_4xx_5xx, 
            # log_response
        ]
    }
    ssl_context = httpx.create_ssl_context()
    ssl_context.options ^= ssl.OP_NO_TLSv1
    with httpx.Client(timeout=None, event_hooks=hooks, verify=ssl_context) as session:
        _c = 0
        for doi, uuid in dois:
            _c += 1
            if _c % 100 == 0:
                logger.info(f"Processed {_c} rows.")
            if uuid in _attempted_uuids:
                continue
            update_jsonl(data={"row": uuid}, filepath="traceback_uuids.jsonl")

            if (PDFS / f"{uuid}.pdf").exists():
                # logger.info(f"{uuid} already exists")
                continue
            response = session.get(f"{BASE_URL}/{doi}?email={EMAIL}")
            if response.status_code == 404:
                logging.info(response.json()["message"])
                continue
            
            data = response.json()
            data["uuid"] = uuid

            if not isinstance(data["best_oa_location"], dict):
                # logger.info(f"{uuid} doest have 'oa_location'")
                continue
            pdf_link = data["best_oa_location"]["url_for_pdf"]
            if pdf_link is None:
                # logger.info(f"{uuid} - empty 'pdf_link'")
                continue

            download(session=session, pdf_link=pdf_link, filename=data["uuid"])
            update_jsonl(
                data={k: v for k, v in data.items() if k not in USELESS_FIELDS},
                filepath="data.jsonl",
            )


if __name__ == "__main__":

    dois = [
        (doi, uuid) for doi, uuid in read_csv(DATA / "processed" / "lens-scopus-wos.csv") if doi != ""
    ]
    fetch(dois)
