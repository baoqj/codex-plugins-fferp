from __future__ import annotations

import json


def main() -> None:
    print(json.dumps({"skill": "fferp-payment-reconciler", "status": "manual_workflow_required"}))


if __name__ == "__main__":
    main()
