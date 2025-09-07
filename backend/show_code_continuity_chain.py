#!/usr/bin/env python3
"""
Debug: Show stitched chain by strategy-code continuity from database.

Usage:
  python backend/show_code_continuity_chain.py --user <USER_UUID> --symbol MSFT [--days 120]
"""

import argparse
import asyncio
import logging
from typing import Dict, Any, List, Set

from app.services.robinhood_service import RobinhoodService
from app.services.options_order_service import OptionsOrderService
from app.services.rolled_options_chain_detector import RolledOptionsChainDetector

logger = logging.getLogger("show_code_continuity_chain")


def extract_codes(order: Dict[str, Any]) -> Set[str]:
    codes: Set[str] = set()
    for key in ("long_strategy_code", "short_strategy_code"):
        v = order.get(key)
        if v:
            codes.add(v)
    for leg in order.get("legs", []) or []:
        for key in ("long_strategy_code", "short_strategy_code"):
            v = leg.get(key)
            if v:
                codes.add(v)
    return {c for c in codes if c}


def print_chain(chain: Dict[str, Any]) -> None:
    orders: List[Dict[str, Any]] = chain.get("orders", [])
    if not orders:
        print("No orders in chain")
        return

    print(f"Symbol: {chain.get('chain_symbol', '')}")
    print(f"Detection: {chain.get('detection_method', '')}")
    print(f"Orders: {len(orders)}  Net Premium: {chain.get('net_premium', 0)}  Status: {chain.get('status', '')}")
    print("---")

    # Chronologically sorted inside detector, but ensure order
    orders = sorted(orders, key=lambda x: x.get("created_at", ""))

    prev_codes: Set[str] = set()
    for i, o in enumerate(orders, 1):
        dt = (o.get("created_at") or "")[:19]
        oid = o.get("id") or o.get("order_id")
        direction = (o.get("direction") or "").upper()
        qty = o.get("processed_quantity", 0)
        prem = o.get("processed_premium", 0)

        # Primary leg info
        legs = o.get("legs", []) or []
        pos_effect = None
        strike = None
        expiry = None
        otype = None
        if legs:
            opens = [l for l in legs if (l.get("position_effect") == "open")]
            closes = [l for l in legs if (l.get("position_effect") == "close")]
            if opens and closes:
                pos_effect = "roll"
                leg0 = opens[0]
            elif opens:
                pos_effect = "open"
                leg0 = opens[0]
            elif closes:
                pos_effect = "close"
                leg0 = closes[0]
            else:
                leg0 = legs[0]
                pos_effect = leg0.get("position_effect")

            strike = leg0.get("strike_price")
            expiry = leg0.get("expiration_date")
            otype = leg0.get("option_type")

        codes = extract_codes(o)
        shared = prev_codes & codes if prev_codes else set()

        print(f"{i:2d}. {dt}  {oid}  {direction:6s} qty={qty} prem={prem}  {pos_effect or ''} {otype or ''} {strike or ''} {expiry or ''}")
        print(f"    codes: {', '.join(sorted(codes)) or '-'}")
        if shared:
            print(f"    shared with prev: {', '.join(sorted(shared))}")
        prev_codes = codes


async def run(user_id: str, symbol: str, days_back: int) -> None:
    rh = RobinhoodService()
    opts = OptionsOrderService(rh)
    detector = RolledOptionsChainDetector(opts)

    chains = await detector.detect_chains_from_database(user_id=user_id, days_back=days_back, symbol=symbol)
    if not chains:
        print("No chains detected")
        return

    # Prefer continuity-detected chain, otherwise the longest chain for this symbol
    chains = [c for c in chains if (c.get("chain_symbol", "") or "").upper() == symbol.upper()]
    if not chains:
        print("No chains for symbol found")
        return

    continuity = [c for c in chains if c.get("detection_method") == "strategy_code_continuity"]
    chain = None
    if continuity:
        # If multiple, take the longest
        chain = max(continuity, key=lambda c: c.get("total_orders", 0))
    else:
        chain = max(chains, key=lambda c: c.get("total_orders", 0))

    print_chain(chain)


def main():
    parser = argparse.ArgumentParser(description="Show stitched chain by code continuity from DB")
    parser.add_argument("--user", required=True, help="User UUID")
    parser.add_argument("--symbol", default="MSFT", help="Underlying symbol (default: MSFT)")
    parser.add_argument("--days", type=int, default=365, help="Days back to consider (default: 365)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(run(user_id=args.user, symbol=args.symbol, days_back=args.days))


if __name__ == "__main__":
    main()

