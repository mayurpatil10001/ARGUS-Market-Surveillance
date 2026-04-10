"""
data/pipeline/kafka_consumer.py — Kafka trade consumer with graceful shutdown.
"""
from __future__ import annotations

import os
import signal
import logging
from typing import Callable, Optional

import msgpack
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TRADE_TOPIC = "argus.trades"
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
CONSUMER_GROUP = "argus-worker"


class TradeConsumer:
    """
    Consumes trade messages from 'argus.trades' Kafka topic.
    Commits offsets only after handler succeeds. Handles SIGTERM gracefully.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: str = TRADE_TOPIC,
        group_id: str = CONSUMER_GROUP,
    ):
        from kafka import KafkaConsumer

        self._running = False
        self._topic = topic
        self._consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers or KAFKA_BOOTSTRAP,
            group_id=group_id,
            value_deserializer=lambda v: msgpack.unpackb(v, raw=False),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            max_poll_records=100,
            session_timeout_ms=30_000,
            heartbeat_interval_ms=10_000,
        )
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)

    def _handle_sigterm(self, signum, frame):
        logger.info("SIGTERM received — shutting down consumer.")
        self._running = False

    def consume_loop(self, handler_fn: Callable[[dict], None]) -> None:
        """
        Infinite consumer loop. Calls handler_fn for each message.
        Commits offset only after handler_fn returns successfully.
        On handler exception: logs error, skips commit (message will be reprocessed).
        """
        self._running = True
        logger.info(f"Starting consumer on topic '{self._topic}' group '{CONSUMER_GROUP}'")

        while self._running:
            try:
                records = self._consumer.poll(timeout_ms=1000)
                for tp, messages in records.items():
                    for msg in messages:
                        trade = msg.value
                        if isinstance(trade, dict):
                            _parse_trade_timestamps(trade)
                        try:
                            handler_fn(trade)
                            self._consumer.commit()
                        except Exception as exc:
                            logger.error(
                                f"Handler error for msg at offset {msg.offset}: {exc}",
                                exc_info=True,
                            )
            except Exception as exc:
                logger.error(f"Consumer poll error: {exc}", exc_info=True)

        self._consumer.close()
        logger.info("Consumer closed.")

    def close(self) -> None:
        self._running = False
        try:
            self._consumer.close()
        except Exception:
            pass


def _parse_trade_timestamps(trade: dict) -> None:
    """Converts ISO timestamp strings back to datetime objects in-place."""
    from datetime import datetime
    for key in ("timestamp", "created_at"):
        if key in trade and isinstance(trade[key], str):
            try:
                trade[key] = datetime.fromisoformat(trade[key])
            except ValueError:
                pass


def default_handler(trade: dict) -> None:
    """
    Default message handler: persists trade to PostgreSQL.
    Used when running argus-worker as a standalone service.
    """
    from data.db.session import get_session
    from data.db.crud import bulk_create_trades
    from data.pipeline.cleaner import normalize_account_id

    session = get_session()
    try:
        if "account_id" not in trade or not trade["account_id"]:
            broker = trade.get("broker", "unknown")
            client = trade.get("client_id", "unknown")
            trade["account_id"] = normalize_account_id(broker, client)
        bulk_create_trades(session, [trade])
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    consumer = TradeConsumer()
    consumer.consume_loop(default_handler)
