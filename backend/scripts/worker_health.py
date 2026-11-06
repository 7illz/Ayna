import socket
from datetime import UTC, datetime

from redis import Redis
from rq import Worker

from app.common.config import get_settings

workers = Worker.all(connection=Redis.from_url(get_settings().redis_url))
assert any(
    worker.hostname == socket.gethostname()
    and worker.last_heartbeat
    and (datetime.now(UTC) - worker.last_heartbeat).total_seconds() < 120
    for worker in workers
), "No recent heartbeat from this Ayna worker"
