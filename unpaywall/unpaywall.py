# -*- coding: utf-8 -*-
import ssl
import csv
import json
import logging
from pathlib import Path

import httpx


class Unpaywall:
    BASE_URL = "https://api.unpaywall.org/v2"
    USELESS_FIELDS = ["first_oa_location", "oa_locations", "oa_locations_embargoed"]

    def __init__(
        self,
        email,
        raw_pdfs,
        csv_file,
        jsonl_file,
        logger,
        attempted_uuids="attempted_uuids.jsonl",
    ):
        self.email = email
        self.raw_pdfs = raw_pdfs
        self.csv_file = csv_file
        self.jsonl_file = jsonl_file
        self.attempted_uuids = attempted_uuids
        self.logger = logger
        self.context_created = False

    def __call__(self):
        dois = [(doi, uuid) for doi, uuid in self.iter_csv()]
        self.run(dois)

    @staticmethod
    def update_jsonl(data, filepath):
        with open(filepath, "a", encoding="utf-8") as out:
            json.dump(data, out)
            out.write("\n")

    def iter_jsonl(self, filepath):
        with open(filepath, "r") as lines:
            for line in lines:
                yield json.loads(line)

    def iter_csv(self):
        with open(self.csv_file, newline="", encoding="ISO-8859-1") as csvfile:
            csv_reader = csv.DictReader(csvfile, delimiter=",")
            for row in csv_reader:
                yield row["doi"], row["uuid"]

    def _read_attempted_uuids(self):
        if isinstance(self.attempted_uuids, str):
            f = Path(self.attempted_uuids).resolve()
        if isinstance(self.attempted_uuids, Path):
            f = self.attempted_uuids
        if not f.exists():
            return []
        return [line["row"] for line in self.iter_jsonl(f)]

    def _check_attempted(self, uuid):
        attempted = self._read_attempted_uuids()
        return uuid in attempted

    def _check_exists(self, uuid):
        return (self.raw_pdfs / f"{uuid}.pdf").exists()

    def _check_missing_links(self, data):
        if not isinstance(data["best_oa_location"], dict):
            return True
        pdf_link = data["best_oa_location"]["url_for_pdf"]
        if pdf_link is None:
            return True

    def raise_on_4xx_5xx(self, response):
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            self.logger.info(f"Errored ({response.status_code}): {response.url}")

    def ensure_context_created(self):
        if self.context_created:
            return
        self._ssl_context = httpx.create_ssl_context()
        self._ssl_context.options ^= ssl.OP_NO_TLSv1
        self._hooks = {"response": [self.raise_on_4xx_5xx]}
        self.raw_pdfs.mkdir(exist_ok=True, parents=True)
        self.context_created = True

    def fetch(self, session, doi):
        return session.get(f"{Unpaywall.BASE_URL}/{doi}", params={"email": self.email})

    def stream_response(self, session, endpoint):
        try:
            with session.stream("GET", endpoint) as response:
                for chunk in response.iter_bytes():
                    yield chunk
        except httpx.ConnectError:
            self.logger.info(f"Connection error: {endpoint}")

    def download(self, session, link, filepath):
        with open(self.raw_pdfs / f"{filepath}.pdf", "wb") as out:
            for chunk in self.stream_response(session=session, endpoint=link):
                out.write(chunk)

    def run(self, dois):
        self.ensure_context_created()
        with httpx.Client(
            event_hooks=self._hooks, verify=self._ssl_context, timeout=None
        ) as session:
            for doi, uuid in dois:
                if self._check_exists(uuid) or self._check_attempted(uuid):
                    continue
                self.update_jsonl({"row": uuid}, self.attempted_uuids)

                response = self.fetch(session=session, doi=doi)
                if response.status_code == 404:
                    self.logger.info(response.json()["message"])
                    continue

                data = response.json()
                data["uuid"] = uuid
                if self._check_missing_links(data):
                    continue

                self.download(
                    session=session,
                    link=data["best_oa_location"]["url_for_pdf"],
                    filepath=data["uuid"],
                )
                self.update_jsonl(
                    data={
                        k: v
                        for k, v in data.items()
                        if k not in Unpaywall.USELESS_FIELDS
                    },
                    filepath=self.jsonl_file,
                )
