from __future__ import annotations

from service.workers.message_processor import process_one_task


if __name__ == "__main__":
    result = process_one_task()
    print(result or "No pending task.")
