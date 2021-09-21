import os
import json
import logging
import httpx


EMAIL = "hcssteamukraine@gmail.com"
BASE_URL = "https://api.unpaywall.org/v2"
IRRELEVANT_FIELDS = ["first_oa_location", "oa_locations_embargoed", "oa_locations"]

root = os.path.dirname(os.path.abspath(__file__))
data = os.path.join(root, "data")
pdfs = os.path.join(data, "raw_pdfs")


def create_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(os.path.join(root, f"{name}.log"))
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
        logger.info(f"Errored ({response.status_code}): {str(response.url)}")


def log_request(request):
    logger.info(
        f"Request event hook: {request.method} {request.url} - Waiting for response"
    )


def log_response(response):
    request = response.request
    logger.info(
        f"Response event hook: {request.method} {request.url} - Status {response.status_code}"
    )


def stream_response(session, endpoint):
    with session.stream("GET", endpoint) as response:
        for chunk in response.iter_bytes():
            yield chunk


def download(session, response):
    filename = response["doi"].replace("/", "_")
    try:
        pdf_link = response["best_oa_location"]["url_for_pdf"]
    except TypeError:
        logger.info(f"{filename} - is empty")
        return
    with open(os.path.join(pdfs, rf"{filename}.pdf"), "wb") as output:
        for chunk in stream_response(session, pdf_link):
            output.write(chunk)


def update_jsonl(response, filepath):
    with open(os.path.join(data, filepath), "a", encoding="utf-8") as out:
        json.dump(response, out)
        out.write("\n")


def fetch(dois):
    hooks = {"request": [log_request], "response": [raise_on_4xx_5xx, log_response]}
    with httpx.Client(timeout=60, event_hooks=hooks) as session:
        for doi in dois:
            response = session.get(f"{BASE_URL}/{doi}?email={EMAIL}")
            if response.status_code == 404:
                logging.info(response["message"])
                continue
            data = response.json()
            download(session, data)
            update_jsonl(data, "data.jsonl")
            logger.info(f"Downloaded/updated {doi}")


if __name__ == "__main__":

    dois = [
        "10.1016/j.intell.2017.01.008",
        "10.31228/osf.io/3vuzf",
        "10.17323/1996-7845-2017-04-32",
        "10.1177/0010836713494996",
        "10.7577/njcie.2891",
        "10.1063/1.1505280",
        "10.1163/ej.9789004164826.i-794.94",
        "10.1080/09709274.2010.11906276",
        "10.30541/v22i4pp.261-282",
        "10.1057/9781137300355_15",
    ]
    fetch(dois)
