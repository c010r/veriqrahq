from __future__ import annotations

import asyncio

from app.services.arce_sync import sync_history_for_all_agencies


if __name__ == "__main__":
    asyncio.run(sync_history_for_all_agencies())
