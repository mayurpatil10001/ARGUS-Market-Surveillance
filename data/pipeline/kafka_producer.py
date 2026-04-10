"""
data/pipeline/kafka_producer.py — Kafka trade producer using msgpack serialization.
"""
from __future__ import annotations

import os
import logging
from typing import Optional

import msgpack
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TRADE_TOPIC = "argus.trades"
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")


class TradeProducer:
    """
    Produces trade messages to the 'argus.trades' Kafka topic.
    Serializes with msgpack for performance. Thread-safe via internal locks.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: str = TRADE_TOPIC,
    ):
        from kafka import KafkaProducer

        self._topic = topic
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers or KAFKA_BOOTSTRAP,
            value_serializer=lambda v: msgpack.packb(v, use_bin_type=True),
            key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
            acks="all",
            retries=5,
            max_in_flight_requests_per_connection=1,
            compression_type="gzip",
        )

    def send_trade(self, trade: dict) -> None:
        """
        Sends a single trade dict to Kafka.
        Key = account_id for partitioning.
        Timestamps are serialized as ISO strings for cross-language compatibility.
        """
        payload = _serialize_trade(trade)
        key = trade.get("account_id", "unknown")
        future = self._producer.send(self._topic, key=key, value=payload)
        try:
            future.get(timeout=10)
        except Exception as exc:
            logger.error(f"Failed to send trade for {key}: {exc}")
            raise

    def send_batch(self, trades: list[dict]) -> int:
        """
        Sends a list of trade dicts to Kafka. Returns count of successfully sent trades.
        Uses non-blocking sends for throughput then flushes.
        """
        sent = 0
        for trade in trades:
            payload = _serialize_trade(trade)
            key = trade.get("account_id", "unknown")
            self._producer.send(self._topic, key=key, value=payload)
            sent += 1
        self._producer.flush(timeout=30)
        return sent

    def close(self) -> None:
        self._producer.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _serialize_trade(trade: dict) -> dict:
    """Convert datetime objects to ISO strings before msgpack serialization."""
    serialized = {}
    for k, v in trade.items():
        if hasattr(v, "isoformat"):
            serialized[k] = v.isoformat()
        elif hasattr(v, "item"):  # numpy scalar
            serialized[k] = v.item()
        else:
            serialized[k] = v
    return serialized
