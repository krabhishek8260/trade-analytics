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

## Sync & Refresh

How data gets from Robinhood to your dashboard and stays fresh.

Orders Sync (Source of Truth)

- Endpoint: `/options/orders/sync` (POST)
- Service: `OptionsOrderService.sync_options_orders(user_id, force_full_sync, days_back)`
- Full sync:
  - Use when onboarding or after schema changes.
  - Looks back up to 365 days by default (configurable via `days_back`).
  - Fetches from Robinhood API and stores into `options_orders`.
- Incremental sync:
  - Default path when `force_full_sync=false`.
  - Computes `since_time` from the last successful sync (with a 1‑day safety buffer) and pulls only new/updated orders.
  - Much faster; safe to run frequently.
- Status: `/options/orders/sync-status` returns last sync info and counts.

Rolled Chains Processing (Compute Layer)

- Endpoint: `/rolled-options-v2/sync` (POST)
- Service: `RolledOptionsCronService`
- Full vs incremental:
  - Full: clears existing `rolled_options_chains` for the user, then rebuilds all chains (uses extended lookback in detection).
  - Incremental: upserts chains; does not delete existing; updates affected symbols/periods.
- Steps during processing:
  - Load orders (DB‑first, extended lookback for enhanced detection when needed).
  - Detect chains (`RolledOptionsChainDetector.detect_chains_from_database`).
  - Analyze and upsert each chain to `rolled_options_chains` (atomic per‑chain nested transactions).
  - Update `user_rolled_options_sync` with counts and timestamps; schedule next run ~30 minutes.
  - Expire Redis caches with pattern `rolled_options:*` so the UI reads fresh data immediately.
- Status: `/rolled-options-v2/status` returns `status`, `last_processed`, `last_successful`, `data_age_minutes`.

Dashboard Refresh After Placing a New Order

- Automatic path:
  - A background cycle runs about every 30 minutes. Your new order will appear after the next:
    1) Orders sync writes it to `options_orders`.
    2) Rolled processing recomputes and upserts chains, clears cache.
  - UI fetches from `/rolled-options-v2/chains` and will reflect fresh data once caches clear.
- Manual refresh (immediate):
  - Trigger orders sync:
    - `POST /options/orders/sync` (optional: `?force_full_sync=true`)
  - Trigger rolled chains processing:
    - `POST /rolled-options-v2/sync` (optional: `?force_full_sync=true`)
  - Check status:
    - `GET /rolled-options-v2/status` until `status` shows `completed`.
  - Optional: expire caches explicitly if needed:
    - `POST /rolled-options-v2/cache/expire` (clears `rolled_options:*`).

Quick Examples (curl)

```
# 1) Incremental orders sync (fast)
curl -X POST \
  "http://localhost:8000/api/v1/options/orders/sync"

# 2) Trigger rolled chains processing
curl -X POST \
  "http://localhost:8000/api/v1/rolled-options-v2/sync"

# 3) Watch processing status
curl "http://localhost:8000/api/v1/rolled-options-v2/status" | jq

# 4) (Optional) Expire caches if testing
curl -X POST \
  "http://localhost:8000/api/v1/rolled-options-v2/cache/expire"
```

Frontend Integration

- The UI calls:
  - `getRolledOptionsChains()` → `/rolled-options-v2/chains` (paginated, filtered)
  - `triggerOptionsOrdersSync()` → `/options/orders/sync` (manual pull)
  - `triggerRolledOptionsSync()` → `/rolled-options-v2/sync` (manual recompute)
  - `getRolledOptionsSyncStatus()` → `/rolled-options-v2/status` (poll progress/freshness)
- After processing completes, Redis caches for rolled options are cleared server‑side, so the next UI fetch returns fresh chains.

## Updating Existing Chains (When a Roll Happens)

End-to-End Flow

- New broker fill: a roll (close+open) or a final close is filled at Robinhood.
- Orders sync: `/options/orders/sync` ingests it into `options_orders` (incremental uses last sync minus 1 day buffer).
- Rolled processing: `/rolled-options-v2/sync` runs the detector on DB orders, rebuilds the chain, and upserts to `rolled_options_chains`.

Detector Behavior (Rebuild + Merge)

- Rebuilds sequences using strategy codes, code continuity, and roll heuristics; merges overlaps preferring the longer chain, and drops strict subsets.
- Chain ID stays stable (strategy-code or `SYMBOL_firstOrderId`), so DB upsert updates the same record.

Database Upsert (Update-in-Place)

- Key: `(user_id, chain_id)` conflict target.
- On update, refreshes: `status`, `initial_strategy`, `last_activity_date`, `total_orders`, `roll_count`, `total_credits_collected`, `total_debits_paid`, `net_premium`, `total_pnl`, `chain_data`, `summary_metrics`, `processed_at`, `updated_at`.
- Full sync: clears user’s chains then rebuilds all; incremental: upserts without delete.

Status Transitions

- Closed if opens==closes, or last order contains any close, or typical credit→debit pattern (short premium then buyback).
- Otherwise active; if latest expiry has passed, may mark as expired.

Cache + UI Refresh

- After storing, server clears Redis keys `rolled_options:*`; next UI fetch of `/rolled-options-v2/chains` shows the updated chain immediately.

Manual vs Automatic Triggers

- Automatic: background cycle (~30 minutes) runs orders sync → detect → upsert → cache‑clear.
- Manual (immediate):
  - POST `/options/orders/sync`
  - POST `/rolled-options-v2/sync`
  - Poll `/rolled-options-v2/status` until `status=completed`.

Relevant Code

- Orders incremental since-time: `backend/app/services/options_order_service.py:84`
- Orders for detection: `backend/app/services/options_order_service.py:878`
- Detector entry (DB-first): `backend/app/services/rolled_options_chain_detector.py:63`
- Detector status calc: `backend/app/services/rolled_options_chain_detector.py:492`
- Closed/open logic: `backend/app/services/rolled_options_chain_detector.py:508`
- Merge/dedupe preference: `backend/app/services/rolled_options_chain_detector.py:159`
- Subset dedupe: `backend/app/services/rolled_options_chain_detector.py:202`
- Chain upsert fields (on conflict): `backend/app/services/rolled_options_cron_service.py:640`
- Full sync delete: `backend/app/services/rolled_options_cron_service.py:268`
- Cache clear after processing: `backend/app/services/rolled_options_cron_service.py:321`


## Diagrams

Data Flow

Robinhood API
  │  (sync via OptionsOrderService)
  ▼
options_orders (DB)
  │  (read: get_orders_for_chain_detection)
  ▼
Detector (strategy-code, continuity, heuristic, form-source)
  │  (validate, merge, dedupe)
  ▼
rolled_options_chains (DB)
  │  (read: API v2)
  ▼
Frontend (chains, summary, pagination)

Patterns (single leg abbreviations: SO=Sell/Open, BO=Buy/Open, SC=Sell/Close, BC=Buy/Close)

Sell-to-Open

Order 1: SO ──▶ position open
Order 2: BC + SO ──▶ roll (close old, open new)
Order 3: BC ──▶ final close

Buy-to-Open

Order 1: BO ──▶ position open
Order 2: SC + BO ──▶ roll (close old, open new)
Order 3: SC ──▶ final close

## Field Glossary

Options Orders (`options_orders`)

- id: UUID; DB primary key; example: 4b4c1f0d-...-c2b1
- user_id: UUID; owner; example: 9e9e3d3a-...-ab12
- order_id: string; broker order ID; example: 2b9f3c5e-...
- state: string; order state; example: filled
- type: string; order type; example: limit
- chain_id: string; broker chain identifier; example: 0a1b2c3d...
- chain_symbol: string; underlying; example: NVDA
- processed_quantity: numeric; contracts filled; example: 1.0
- processed_premium: numeric; total premium; example: 152.34
- premium: numeric; per-contract premium; example: 1.52
- direction: string; credit|debit; example: credit
- strategy: string; strategy label; example: single, calendar_spread, roll
- opening_strategy: string; opening strategy; example: short_put
- closing_strategy: string; closing strategy; example: buy_to_close
- created_at: timestamptz; broker created; example: 2025-02-01T15:34:12Z
- updated_at: timestamptz; broker updated; example: 2025-02-01T15:35:20Z
- legs_count: int; number of legs; example: 2
- legs_details: JSONB; raw legs array; example: [{ position_effect: "close", side: "buy", option_type: "put", strike_price: 50, expiration_date: "2025-03-21", quantity: 1 }]
- leg_index: int; primary leg index for indexing; example: 0
- leg_id: string; broker leg identifier; example: 4d5e...
- side: string; buy|sell (primary leg); example: sell
- position_effect: string; open|close (primary leg); example: open
- option_type: string; call|put (primary leg); example: put
- strike_price: numeric; strike (primary leg); example: 50.0
- expiration_date: string; YYYY-MM-DD (primary leg); example: 2025-03-21
- long_strategy_code: string; grouping code (long legs); example: STRAT_A
- short_strategy_code: string; grouping code (short legs); example: STRAT_B
- raw_data: JSONB; original broker payload; example: { ... }
- db_created_at: timestamptz; row created; example: 2025-02-01T15:36:00Z
- db_updated_at: timestamptz; row updated; example: 2025-02-01T15:36:00Z

Rolled Options Chains (`rolled_options_chains`)

- id: UUID; DB primary key; example: 7f8c...
- user_id: UUID; owner; example: 9e9e3d3a-...-ab12
- chain_id: string; chain identifier (stable per chain); example: NVDA_2b9f3c5e
- underlying_symbol: string; ticker; example: NVDA
- status: string; active|closed|expired; example: active
- initial_strategy: string; first recognizable strategy; example: short_put
- start_date: timestamptz; first order time; example: 2024-12-01T14:00:00Z
- last_activity_date: timestamptz; last order time; example: 2025-02-18T20:10:00Z
- total_orders: int; number of orders in chain; example: 3
- roll_count: int; rolls (typically total_orders - 1 if starting from a pure open); example: 1
- total_credits_collected: numeric; sum of credits; example: 230.00
- total_debits_paid: numeric; sum of debits; example: 180.50
- net_premium: numeric; credits - debits; example: 49.50
- total_pnl: numeric; realized + unrealized; example: 65.20
- chain_data: JSONB; full chain payload for UI; example: { orders: [...], latest_position: {...}, enhanced: true, chain_type: "enhanced" }
- summary_metrics: JSONB; dashboard roll-ups; example: { avg_roll_interval_days: 14 }
- created_at: timestamptz; row created; example: 2025-02-18T21:00:00Z
- updated_at: timestamptz; row updated; example: 2025-02-18T21:00:00Z
- processed_at: timestamptz; last processing time; example: 2025-02-18T21:00:00Z

User Rolled Options Sync (`user_rolled_options_sync`) — status/freshness

- user_id: UUID; primary key and FK
- last_processed_at: timestamptz; last attempt timestamp
- last_successful_sync: timestamptz; last success timestamp
- next_sync_after: timestamptz; scheduled next run
- total_chains / active_chains / closed_chains: ints; counts
- total_orders_processed: int; processed orders count
- processing_status: string; pending|processing|completed|error
- error_message: text; last error (if any)
- retry_count: int; retries so far
- full_sync_required: bool; whether next should be full
- incremental_sync_enabled: bool; toggle incremental mode

## JSON Examples

Example `legs_details` (two-leg roll)

```
[
  {
    "position_effect": "close",
    "side": "buy",
    "option_type": "put",
    "strike_price": 50.0,
    "expiration_date": "2025-03-21",
    "quantity": 1,
    "long_strategy_code": null,
    "short_strategy_code": "STRAT_A"
  },
  {
    "position_effect": "open",
    "side": "sell",
    "option_type": "put",
    "strike_price": 55.0,
    "expiration_date": "2025-04-18",
    "quantity": 1,
    "long_strategy_code": null,
    "short_strategy_code": "STRAT_B"
  }
]
```

Example `chain_data` persisted on a chain

```
{
  "enhanced": true,
  "chain_type": "enhanced",
  "latest_position": {
    "strike_price": 55.0,
    "expiration_date": "2025-04-18",
    "option_type": "put"
  },
  "orders": [
    {
      "id": "order-1",
      "state": "filled",
      "direction": "credit",
      "created_at": "2024-12-01T14:00:00Z",
      "form_source": null,
      "strategy": "single",
      "chain_symbol": "NVDA",
      "legs": [
        {
          "position_effect": "open",
          "side": "sell",
          "option_type": "put",
          "strike_price": 50.0,
          "expiration_date": "2025-01-17",
          "quantity": 1
        }
      ]
    },
    {
      "id": "order-2",
      "state": "filled",
      "direction": "credit",
      "created_at": "2024-12-10T14:00:00Z",
      "form_source": "strategy_roll",
      "strategy": "roll",
      "chain_symbol": "NVDA",
      "legs": [
        {
          "position_effect": "close",
          "side": "buy",
          "option_type": "put",
          "strike_price": 50.0,
          "expiration_date": "2025-01-17",
          "quantity": 1
        },
        {
          "position_effect": "open",
          "side": "sell",
          "option_type": "put",
          "strike_price": 55.0,
          "expiration_date": "2025-04-18",
          "quantity": 1
        }
      ],
      "roll_details": {
        "type": "roll",
        "close_position": {
          "strike_price": 50.0,
          "expiration_date": "2025-01-17",
          "option_type": "put"
        },
        "open_position": {
          "strike_price": 55.0,
          "expiration_date": "2025-04-18",
          "option_type": "put"
        }
      }
    },
    {
      "id": "order-3",
      "state": "filled",
      "direction": "debit",
      "created_at": "2025-02-18T20:10:00Z",
      "strategy": "single",
      "chain_symbol": "NVDA",
      "legs": [
        {
          "position_effect": "close",
          "side": "buy",
          "option_type": "put",
          "strike_price": 55.0,
          "expiration_date": "2025-04-18",
          "quantity": 1
        }
      ]
    }
  ],
  "metrics": {
    "total_orders": 3,
    "roll_count": 1,
    "total_credits_collected": 230.0,
    "total_debits_paid": 180.5,
    "net_premium": 49.5
  }
}
```

## End-to-End Walkthrough (Real Example)

This walkthrough mirrors the SMCI example chain captured in `SMCI_CHAIN_EXAMPLES.md` and demonstrates how a chain moves from raw orders to a persisted `rolled_options_chains` row.

Input Orders (SMCI PUT roll)

- 2024-07-16: SELL to OPEN 1 SMCI PUT $790 exp 2024-07-26 (credit 1145.00)
- 2024-07-24: BUY to CLOSE $790 PUT (07/26) + SELL to OPEN $790 PUT (08/02) (credit 900.00)
- 2024-07-30: BUY to CLOSE $790 PUT (08/02) + SELL to OPEN $790 PUT (08/09) (credit 800.00)
- 2024-08-07: BUY to CLOSE 1 SMCI PUT $790 exp 2024-08-09 (debit 245.00)

Detection Steps

- Group by symbol/type: all orders are `SMCI` `put` → same group.
- Identify roll orders: the 2 middle orders each have 2 legs with both `open` and `close`.
- Build chain: start from single‑leg open (first order), stitch each roll that closes the prior open and opens the next, then include the final single‑leg close.
- Time window: first→last within 240 days (passes).

Validation Checks

- First order: single leg with `position_effect='open'` (passes).
- Middle orders: exactly one `close` + one `open` leg (passes).
- Last order: single leg with `position_effect='close'` (passes).
- Position continuity: each `close` matches a previously opened position (strike/type/expiry, opposite side) (passes).

Derived Metrics

- Total credits collected: 1145.00 + 900.00 + 800.00 = 2845.00
- Total debits paid: 245.00
- Net premium: 2845.00 − 245.00 = 2600.00
- Total orders: 4; Roll count: 2
- Status: closed (last order contains a closing leg; opens == closes)

Persisted Chain (rolled_options_chains)

- chain_id: stable chain key (e.g., from first order)
- underlying_symbol: SMCI
- status: closed
- initial_strategy: short_put (derived from first open)
- start_date: 2024-07-16T…
- last_activity_date: 2024-08-07T…
- total_orders: 4
- roll_count: 2
- total_credits_collected: 2845.00
- total_debits_paid: 245.00
- net_premium: 2600.00
- total_pnl: populated by PnL service if applicable
- chain_data: includes `orders` (as seen), `enhanced: true` when chain starts with a single‑leg open, and optionally `latest_position` for active chains

## Exact JSON Excerpts (SMCI)

Source file: `backend/debug_data/20250907_163416_options_orders.json`

Opening order (single leg SELL to OPEN 790 PUT exp 2024‑07‑26)

```
{
  "id": "6696a566-d6de-4ae4-b645-0f553f5f54a1",
  "created_at": "2024-07-16T16:52:54.169096Z",
  "direction": "credit",
  "strategy": null,
  "form_source": "option_chain",
  "legs": [
    {
      "position_effect": "open",
      "side": "sell",
      "option_type": "put",
      "strike_price": "790.0000",
      "expiration_date": "2024-07-26"
    }
  ]
}
```

Roll #1 (CLOSE 07/26 → OPEN 08/02)

```
{
  "id": "66a120aa-4446-48d7-a452-6c8213605943",
  "created_at": "2024-07-24T15:41:30.552833Z",
  "direction": "credit",
  "strategy": "short_put_calendar_spread",
  "form_source": "strategy_roll",
  "legs": [
    {
      "position_effect": "close",
      "side": "buy",
      "option_type": "put",
      "strike_price": "790.0000",
      "expiration_date": "2024-07-26"
    },
    {
      "position_effect": "open",
      "side": "sell",
      "option_type": "put",
      "strike_price": "790.0000",
      "expiration_date": "2024-08-02"
    }
  ]
}
```

Roll #2 (CLOSE 08/02 → OPEN 08/09)

```
{
  "id": "66a91dce-ece3-4257-bacb-7ea49ce44494",
  "created_at": "2024-07-30T17:07:26.062704Z",
  "direction": "credit",
  "strategy": "short_put_calendar_spread",
  "form_source": "strategy_roll",
  "legs": [
    {
      "position_effect": "close",
      "side": "buy",
      "option_type": "put",
      "strike_price": "790.0000",
      "expiration_date": "2024-08-02"
    },
    {
      "position_effect": "open",
      "side": "sell",
      "option_type": "put",
      "strike_price": "790.0000",
      "expiration_date": "2024-08-09"
    }
  ]
}
```

Final close (single leg BUY to CLOSE 790 PUT exp 2024‑08‑09)

```
{
  "id": "66b3798b-d793-47f9-9d31-186cbfeb2333",
  "created_at": "2024-08-07T13:41:31.061894Z",
  "direction": "debit",
  "strategy": "long_put",
  "form_source": "strategy_detail",
  "legs": [
    {
      "position_effect": "close",
      "side": "buy",
      "option_type": "put",
      "strike_price": "790.0000",
      "expiration_date": "2024-08-09"
    }
  ]
}
```
