import os

from redis import Redis
from rq import SimpleWorker, Worker

from app.common.config import get_settings


def main():
    # Windows native development only; Docker always uses process-isolated Worker.
    worker_class = SimpleWorker if os.name == "nt" else Worker
    worker_class(["ayna"], connection=Redis.from_url(get_settings().redis_url)).work()


if __name__ == "__main__":
    main()
