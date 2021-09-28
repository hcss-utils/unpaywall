# -*- coding: utf-8 -*-
import ssl
import csv
import json
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
        else:
            raise ValueError("attempted_uuids should be either str or Path.")
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
        self._timeout = httpx.Timeout(60, read=5 * 60)
        self.raw_pdfs.mkdir(exist_ok=True, parents=True)
        self.context_created = True

    def fetch(self, session, doi):
        return session.get(f"{Unpaywall.BASE_URL}/{doi}", params={"email": self.email})

    def stream_response(self, session, endpoint):
        try:
            with session.stream("GET", endpoint, allow_redirects=True) as response:
                for chunk in response.iter_bytes():
                    yield chunk
        except httpx.ConnectError:
            self.logger.info(f"Errored (ConnectError): {endpoint}")
        except httpx.TransportError:
            self.logger.info(f"Errored (TransportError): {endpoint}")

    def download(self, session, endpoint, filename):
        constructed_path = self.raw_pdfs / f"{filename}.pdf"
        with open(constructed_path, "wb") as out:
            for chunk in self.stream_response(session=session, endpoint=endpoint):
                out.write(chunk)

    def fetch_all(self, dois):
        self.ensure_context_created()
        with httpx.Client(
            event_hooks=self._hooks, verify=self._ssl_context, timeout=self._timeout
        ) as session:
            for doi, uuid in dois:
                response = self.fetch(session=session, doi=doi)
                self.update_jsonl({"row": uuid}, self.attempted_uuids)
                if response.status_code in [403, 404]:
                    continue

                data = response.json()
                data["uuid"] = uuid
                updated = {
                    k: v for k, v in data.items() if k not in Unpaywall.USELESS_FIELDS
                }
                self.update_jsonl(data=updated, filepath=self.jsonl_file)
                if self._check_missing_links(data):
                    continue
                self.download(
                    session=session,
                    endpoint=data["best_oa_location"]["url_for_pdf"],
                    filename=data["uuid"],
                )

    def run(self):
        dois = []
        for doi, uuid in self.iter_csv():
            if self._check_exists(uuid) or self._check_attempted(uuid):
                continue
            dois.append((doi, uuid))
        self.logger.info(f"{len(dois)} left.")
        self.fetch_all(dois)
