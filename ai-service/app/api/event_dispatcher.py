"""Thread-safe asynchronous AI-event delivery with bounded retries."""
import asyncio
from datetime import datetime, timezone
import logging
from threading import Thread
from time import sleep
from uuid import uuid4

import httpx

from .. import config

logger = logging.getLogger(__name__)


class EventDispatcher:
    def __init__(self, backend_url=config.BACKEND_URL, api_key=config.API_KEY, retries=3):
        self.endpoint = f"{backend_url.rstrip('/')}/api/v1/ai-events"
        self.api_key = api_key
        self.retries = retries
        self._loop = asyncio.new_event_loop()
        self._queue = asyncio.Queue()
        self._thread = Thread(target=self._run, name="ai-event-dispatcher", daemon=True)
        self._started = False

    def start(self):
        if not self._started:
            self._started = True
            self._thread.start()
        return self

    def publish(self, payload, endpoint=None):
        if not self._started:
            self.start()
        event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        destination = endpoint or self.endpoint
        asyncio.run_coroutine_threadsafe(self._queue.put((destination, event)), self._loop)
        return event

    def close(self):
        if self._started:
            asyncio.run_coroutine_threadsafe(self._queue.put(None), self._loop).result(timeout=2)
            self._thread.join(timeout=3)
            self._started = False

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._deliver())
        self._loop.close()

    async def _deliver(self):
        async with httpx.AsyncClient(timeout=5) as client:
            while True:
                item = await self._queue.get()
                if item is None:
                    self._queue.task_done()
                    break
                endpoint, event = item
                delivered = False
                for attempt in range(self.retries):
                    try:
                        response = await client.post(
                            endpoint,
                            json=event,
                            headers={"x-api-key": self.api_key},
                        )
                        response.raise_for_status()
                        delivered = True
                        break
                    except httpx.HTTPError as error:
                        if attempt + 1 == self.retries:
                            logger.error("AI event delivery failed (%s): %s", event["event_id"], error)
                        else:
                            await asyncio.sleep(min(2 ** attempt, 4))
                if not delivered:
                    logger.error("Dropping AI event after bounded retries: %s", event["event_id"])
                self._queue.task_done()
