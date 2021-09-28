# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from unpaywall import Unpaywall

ROOT = Path(__file__).resolve().parent.parent
LOGGER_FILE = ROOT / "unpaywalled.log"

DATA = ROOT / "data"
PDFS = DATA / "raw_pdfs"

PROCESSED = DATA / "processed"
CSV_FILE = PROCESSED / "lens-scopus-wos.csv"
JSONL_FILE = PROCESSED / "data.jsonl"
ATTEMPTED_UUIDS = DATA / "attempted_uuids.jsonl"


def create_logger(name):
    logger = logging.getLogger(name.stem)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(name)
    fh.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


if __name__ == "__main__":

    logger = create_logger(LOGGER_FILE)
    parser = Unpaywall(
        email="hcssteamukraine@gmail.com",
        raw_pdfs=PDFS,
        csv_file=CSV_FILE,
        jsonl_file=JSONL_FILE,
        attempted_uuids=ATTEMPTED_UUIDS,
        logger=logger,
    )
    parser.run()
