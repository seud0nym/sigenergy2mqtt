"""InfluxDB HTTP writer implementations.

Writers own endpoint-specific connection state and provisioning.  They do not
own the HTTP session, which allows an established writer to be shared by
multiple services without duplicating connection pools.
"""

import json
import logging
from typing import Protocol

import requests

from sigenergy2mqtt.config import active_config

logger = logging.getLogger(__name__)


class Writer(Protocol):
    """Small interface used by :class:`InfluxBase` for write transports."""

    writer_type: str

    def probe(self, session: requests.Session, test_line: bytes) -> bool:
        """Return whether this configured writer is usable."""
        ...

    def write(self, session: requests.Session, data: bytes) -> bool:
        """Write line-protocol data and return whether it was accepted."""
        ...


class V2HttpWriter:
    """InfluxDB v2 HTTP writer, including bucket provisioning."""

    writer_type = "v2_http"

    def __init__(self, base: str, bucket: str, org: str | None, token: str | None, log_identity: str) -> None:
        self.url = f"{base}/api/v2/write?bucket={bucket}&precision=s"
        if org:
            self.url += f"&org={org}"
        self.headers = {"Authorization": f"Token {token}"} if token else {}
        self._base = base
        self._bucket = bucket
        self._token = token
        self._log_identity = log_identity

    def _create_bucket(self, session: requests.Session) -> bool:
        if self._token is None:
            return False
        try:
            headers = {"Authorization": f"Token {self._token}", "Content-Type": "application/json"}
            orgs = session.get(f"{self._base}/api/v2/orgs", headers=headers, timeout=5)
            if orgs.status_code == 200:
                items = orgs.json()
                org_id = None
                if isinstance(items, dict) and items.get("orgs"):
                    organizations = items.get("orgs")
                    if isinstance(organizations, list) and organizations:
                        org_id = organizations[0].get("id")
                if org_id:
                    response = session.post(
                        f"{self._base}/api/v2/buckets",
                        headers=headers,
                        data=json.dumps({"name": self._bucket, "orgID": org_id}),
                        timeout=5,
                    )
                    return response.status_code in (201, 200)
        except (ValueError, requests.RequestException, TimeoutError) as error:
            logger.debug(f"{self._log_identity} v2 bucket creation failed: {error}")
        return False

    def probe(self, session: requests.Session, test_line: bytes) -> bool:
        try:
            response = session.post(self.url, headers=self.headers or None, data=test_line, timeout=5)
            if response.status_code in (204, 200):
                logger.info(f"{self._log_identity} Using v2 HTTP write endpoint to {self.url}")
                return True
            if response.status_code in (400, 404) and self._token and self._create_bucket(session):
                retry = session.post(self.url, headers=self.headers or None, data=test_line, timeout=5)
                if retry.status_code in (204, 200):
                    logger.info(f"{self._log_identity} Created v2 bucket and will use v2 HTTP write to {self.url}")
                    return True
        except (requests.RequestException, TimeoutError) as error:
            logger.debug(f"{self._log_identity} v2 HTTP detection failed: {error}")
        return False

    def write(self, session: requests.Session, data: bytes) -> bool:
        response = session.post(
            self.url,
            headers=self.headers,
            data=data,
            timeout=active_config.influxdb.write_timeout,
        )
        if response.status_code in (204, 200):
            return True
        logger.error(f"InfluxDB v2 HTTP write failed: {response.status_code=} {response.text=} (url={self.url})")
        return False


class V1HttpWriter:
    """InfluxDB v1 HTTP writer, including database provisioning."""

    writer_type = "v1_http"

    def __init__(self, base: str, db: str, auth: tuple[str, str] | None, log_identity: str) -> None:
        self.url = f"{base}/write"
        self.db = db
        self.auth = auth
        self._base = base
        self._log_identity = log_identity

    def _create_database(self, session: requests.Session) -> bool:
        try:
            response = session.post(
                f"{self._base}/query",
                params={"q": f"CREATE DATABASE {self.db}"},
                auth=self.auth,
                timeout=5,
            )
            return response.status_code == 200
        except (requests.RequestException, TimeoutError) as error:
            logger.debug(f"{self._log_identity} v1 database creation failed: {error}")
        return False

    def probe(self, session: requests.Session, test_line: bytes) -> bool:
        params = {"db": self.db, "precision": "s"}
        try:
            response = session.post(self.url, params=params, data=test_line, auth=self.auth, timeout=5)
            if response.status_code in (204, 200):
                logger.info(f"{self._log_identity} Using v1 HTTP write endpoint to {self.url}")
                return True
            database_error = response.status_code in (404, 400) or (
                response.status_code >= 400 and response.content and b"database" in response.content.lower()
            )
            if database_error and self._create_database(session):
                retry = session.post(self.url, params=params, data=test_line, auth=self.auth, timeout=5)
                if retry.status_code in (204, 200):
                    logger.info(f"{self._log_identity} Created v1 database and will use v1 HTTP write to {self.url}")
                    return True
        except (requests.RequestException, TimeoutError) as error:
            logger.debug(f"{self._log_identity} v1 HTTP detection failed: {error}")
        return False

    def write(self, session: requests.Session, data: bytes) -> bool:
        response = session.post(
            self.url,
            params={"db": self.db, "precision": "s"},
            data=data,
            auth=self.auth,
            timeout=active_config.influxdb.write_timeout,
        )
        if response.status_code in (204, 200):
            return True
        logger.error(f"InfluxDB v1 HTTP write failed: {response.status_code=} {response.text=} (url={self.url})")
        return False
