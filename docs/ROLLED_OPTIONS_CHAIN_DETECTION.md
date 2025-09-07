# Rolled Options Chain Detection

This document explains how rolled options chains are detected, how orders are loaded from the database, and what database fields are involved. It summarizes the production implementation while staying aligned with the detailed logic in `backend/app/services/rolled_options_chain_detector.py` and the storage schema in `backend/app/models`.

## Overview

Rolled chain detection reconstructs a trader’s sequence from the original single‑leg open, through any number of roll transactions (close + open), to the final close. The detector operates database‑first, prioritizing data already ingested from the broker. It supports multiple detection strategies and validates chains with strict position‑flow rules.

Key properties:

- Symbol separation: one underlying per chain, never mixing symbols
- Option‑type separation: calls and puts never mixed in one chain
- Time window: max 8 months between first/last order in a chain
- Valid orders only: `state == 'filled'`

## Where the Logic Lives

- Detector: `backend/app/services/rolled_options_chain_detector.py`
- Orders DB service: `backend/app/services/options_order_service.py`
- Persisted chains: `backend/app/models/rolled_options_chain.py`
- Orders model (schema): `backend/app/models/options_order.py`
- Fast API for precomputed chains: `backend/app/api/rolled_options_v2.py`

## Data Flow (High Level)

1. Orders are synced from Robinhood and stored into `options_orders` via `OptionsOrderService`.
2. Chain detection loads orders from the DB (`get_orders_for_chain_detection`) and groups them.
3. Multiple strategies build candidate chains; validators filter out invalid sequences.
4. Background cron composes chain summaries and persists them to `rolled_options_chains` for fast reads.
5. API v2 serves precomputed chains to the UI with pagination and filters.

## Database Interactions

### Reading Orders for Detection

Method: `OptionsOrderService.get_orders_for_chain_detection(user_id, days_back, symbol)`

- Filters: `user_id`, `state='filled'`, optional `created_at >= now - days_back`, optional `chain_symbol`.
- Sort: ascending by `created_at` for temporal analysis.
- Returns: list of `OptionsOrder` ORM objects; detector converts to dicts for processing.

### Writing Precomputed Chains

Background processing composes and writes to `rolled_options_chains`:

- Aggregated metrics (credits, debits, net premium, roll count)
- Chain status: `active`, `closed`, or `expired`
- `chain_data` JSONB with full orders and analysis details for drill‑down

## Options Orders Schema (Detection‑Relevant Fields)

Table: `options_orders` (ORM: `OptionsOrder`)

- id: UUID (PK)
- user_id: UUID (FK users.id)
- order_id: string (broker order identifier)
- state: string (‘filled’, …)
- type: string (‘limit’, ‘market’)
- chain_id: string (broker chain identifier)
- chain_symbol: string (underlying ticker)
- processed_quantity: numeric (contracts filled)
- processed_premium: numeric (total premium processed)
- premium: numeric (per‑contract premium)
- direction: string (‘credit’ | ‘debit’)
- strategy: string (e.g., ‘single’, ‘calendar_spread’, may include ‘roll’)
- opening_strategy / closing_strategy: string
- created_at / updated_at: timestamptz
- legs_count: int
- legs_details: JSONB (raw legs array)
- Top‑level leg extracts (for indexable queries):
  - leg_index: int
  - leg_id: string
  - side: ‘buy’ | ‘sell’
  - position_effect: ‘open’ | ‘close’
  - option_type: ‘call’ | ‘put’
  - strike_price: numeric
  - expiration_date: ‘YYYY‑MM‑DD’
  - long_strategy_code / short_strategy_code: string
- raw_data: JSONB (original broker payload)
- db_created_at / db_updated_at: timestamptz

Common indexes power fast filtering by user, time, symbol, strategy, and leg facets (see model for full list).

## Persisted Chains Schema

Table: `rolled_options_chains` (ORM: `RolledOptionsChain`)

- id: UUID (PK)
- user_id: UUID (FK users.id)
- chain_id: string (stable identifier per chain)
- underlying_symbol: string
- status: ‘active’ | ‘closed’ | ‘expired’
- initial_strategy: string
- start_date: timestamptz
- last_activity_date: timestamptz
- total_orders: int
- roll_count: int
- total_credits_collected: numeric
- total_debits_paid: numeric
- net_premium: numeric
- total_pnl: numeric
- chain_data: JSONB (full orders + analysis)
- summary_metrics: JSONB (dashboard roll‑ups)
- created_at / updated_at / processed_at: timestamptz

`chain_data` typically includes:

```json
{
  "orders": [ /* broker‑shape orders used for UI */ ],
  "latest_position": { "strike_price": 55, "expiration_date": "2025-02-21", "option_type": "put" },
  "enhanced": true,
  "chain_type": "enhanced"
}
```

## Detection Strategies (Combined)

The detector combines multiple strategies, then merges/deduplicates overlapping results, keeping the longer/more complete chain.

1) Strategy‑code grouping

- Group orders that share `long_strategy_code` or `short_strategy_code` (from order or legs).
- Chronologically sort each code’s orders to form candidate chains.

2) Strategy‑code continuity

- Stitch sequences where adjacent orders share at least one strategy code, allowing transitions like A → A/B → B.
- Operates per symbol+option type, in chronological order.

3) Heuristic roll/chain detection

- Identify roll orders via multi‑criteria:
  - `form_source == 'strategy_roll'` (auto‑roll)
  - `strategy` contains ‘roll’ or ‘calendar_spread’
  - Multi‑leg orders containing both `position_effect: open` and `position_effect: close`
  - Presence of `rolled_from` / `rolled_to`
- Build chains by tracking opens and matching later closes strictly (strike, type, expiry, opposite sides). Middle roll orders may change strike/expiry for the “new open”.

4) Form‑source grouping

- Treat `form_source == 'strategy_roll'` orders grouped by symbol as chains (valid even if single roll, e.g., broker‑marked).

After assembling candidates, the detector:

- Filters out chains that lack both at least one open and one close anywhere
- Removes strict subsets (if chain A’s order IDs ⊂ chain B’s, drop A)

## Position‑Flow Validation

Two canonical patterns are supported.

Sell‑to‑Open chain

1. Initial: SELL to OPEN (single leg)
2. Rolls: BUY to CLOSE (old) + SELL to OPEN (new) (two legs)
3. Final: BUY to CLOSE (single leg)

Buy‑to‑Open chain

1. Initial: BUY to OPEN (single leg)
2. Rolls: SELL to CLOSE (old) + BUY to OPEN (new) (two legs)
3. Final: SELL to CLOSE (single leg)

Strict matching rules when closing an open position:

- strike_price equal
- option_type equal (call/put)
- expiration_date equal
- side must be opposite of the opening leg

Additional constraints:

- Symbol and option type never mix inside a chain
- Max duration between first/last order is 240 days
- Middle rolls may change strike and/or expiration for the newly opened position

## Chain Status Derivation

A chain is considered closed if any of these heuristics confirm closure:

- Count of opens equals closes across all legs
- The last order contains any closing leg
- Opening credits combined with later debits (typical short premium collection then buyback)

Otherwise the chain remains active; if the latest expiration has passed, status may be marked `expired`.

## Example (Condensed)

1) 2024‑12‑01 SELL to OPEN 1 XYZ PUT $50 exp 2025‑01‑17 (credit)
2) 2024‑12‑10 BUY to CLOSE $50 PUT (debit) + SELL to OPEN $55 PUT exp 2025‑02‑21 (credit)
3) 2025‑02‑18 BUY to CLOSE $55 PUT (debit)

Detected as one chain with 3 orders, 1 roll, precise opens/closes continuity, and net premium = credits − debits.

## Endpoints and Background Processing

- GET `/rolled-options-v2/chains`: paginated, filtered chains from DB
- GET `/rolled-options-v2/chains/{chain_id}`: full chain details
- POST `/rolled-options-v2/sync`: trigger background processing (cron service)
- GET `/rolled-options-v2/status`: processing progress and freshness

## Related References

- Logic details: `backend/ROLL_DETECTION_LOGIC.md`
- Enhanced process notes: `backend/ENHANCED_CHAINS_DOCUMENTATION.md`

