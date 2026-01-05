"""
Helper script to trigger a full-history options orders sync (no lookback)

Usage:
  python backend/scripts/full_history_sync.py --user-id <UUID> [--force-full]

Notes:
  - Expects Robinhood credentials in environment (.env) so the service can authenticate.
  - Creates the user in DB if it does not exist (best-effort), otherwise uses provided ID.
"""

import asyncio
import argparse
import logging
import os

from app.services.robinhood_service import RobinhoodService
from app.services.options_order_service import OptionsOrderService
from app.core.database import get_db
from app.models.user import User
from sqlalchemy import select

logger = logging.getLogger("full_history_sync")


async def ensure_user_exists(user_id: str) -> None:
    async for db in get_db():
        # Check if user exists
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return
        # Create a minimal user record
        from sqlalchemy.dialects.postgresql import insert
        username = os.getenv("ROBINHOOD_USERNAME", "robinhood_user")
        record = {
            "id": user_id,
            "email": f"{username}@robinhood.local",
            "full_name": f"Robinhood User ({username})",
            "robinhood_username": username,
            "robinhood_user_id": None,
            "is_active": True,
        }
        stmt = insert(User).values(record).on_conflict_do_nothing(index_elements=["id"])
        await db.execute(stmt)
        await db.commit()


async def main(user_id: str, force_full: bool) -> None:
    rh = RobinhoodService()
    service = OptionsOrderService(rh)

    # Best-effort ensure user exists
    await ensure_user_exists(user_id)

    # Kick off full-history sync (no lookback)
    result = await service.sync_options_orders(
        user_id=user_id,
        force_full_sync=force_full,
        days_back=None,
    )
    if result.get("success"):
        data = result.get("data", {})
        logger.info(
            "Full-history sync complete: processed=%s stored=%s since=%s type=%s",
            data.get("orders_processed"),
            data.get("orders_stored"),
            data.get("since_time"),
            data.get("sync_type"),
        )
        print({"success": True, "data": data})
    else:
        print({"success": False, "message": result.get("message")})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True, help="UUID of the user to sync")
    parser.add_argument("--force-full", action="store_true", help="Force full sync mode")
    args = parser.parse_args()
    asyncio.run(main(args.user_id, args.force_full))

