"""
Robinhood API integration service
Enhanced version of the original OptionsFetcher with async support
"""

import robin_stocks.robinhood as rh
import pandas as pd
import logging
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from app.core.config import settings
from app.core.redis import cache
from app.schemas.options import OptionType, TransactionSide, PositionEffect, Direction

logger = logging.getLogger(__name__)


class RobinhoodService:
    """Enhanced Robinhood API service with async support"""
    
    def __init__(self):
        self.debug_dir = "debug_data"
        os.makedirs(self.debug_dir, exist_ok=True)
        self._authenticated = False
        self.username = None
        self.robinhood_user_id = None  # Store Robinhood user ID
        
        # Auto-authenticate if credentials are provided
        if settings.ROBINHOOD_USERNAME and settings.ROBINHOOD_PASSWORD:
            asyncio.create_task(self._auto_authenticate())
    
    async def test_connectivity(self) -> bool:
        """Test connectivity to Robinhood API"""
        try:
            import requests
            response = requests.get("https://robinhood.com/", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connectivity test failed: {e}")
            return False
    
    async def _auto_authenticate(self):
        """Auto-authenticate using environment variables"""
        try:
            if not self._authenticated and settings.ROBINHOOD_USERNAME and settings.ROBINHOOD_PASSWORD:
                logger.info("Attempting auto-authentication with environment credentials")
                result = await self.authenticate(
                    settings.ROBINHOOD_USERNAME,
                    settings.ROBINHOOD_PASSWORD
                )
                if result["success"]:
                    logger.info("Auto-authentication successful")
                else:
                    logger.warning(f"Auto-authentication failed: {result['message']}")
        except Exception as e:
            logger.error(f"Auto-authentication error: {str(e)}")
    
    async def authenticate(self, username: str, password: str, mfa_code: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate with Robinhood - let robin-stocks handle push notifications internally"""
        try:
            logger.info(f"Attempting login for user: {username}")
            
            # Run in thread pool since robin-stocks is synchronous
            loop = asyncio.get_event_loop()
            
            # Clear any existing session first
            try:
                await loop.run_in_executor(None, rh.logout)
            except:
                pass
            
            # Simple login - let robin-stocks handle everything (including push notifications)
            logger.info("Calling robin-stocks login - library will handle MFA/push notifications")
            
            def do_login():
                return rh.login(username, password, mfa_code=mfa_code)
            
            login_result = await loop.run_in_executor(None, do_login)
            
            logger.info(f"Login completed with result: {login_result}")
            
            # Check if login was successful
            if login_result and login_result.get('access_token'):
                self._authenticated = True
                self.username = username
                
                # Get user ID from Robinhood API
                try:
                    user_id = await self._get_robinhood_user_id()
                    self.robinhood_user_id = user_id
                    logger.info(f"Retrieved Robinhood user ID: {user_id}")
                except Exception as e:
                    logger.warning(f"Could not retrieve Robinhood user ID: {str(e)}")
                    self.robinhood_user_id = None
                
                logger.info(f"Successfully logged in user: {username}")
                return {"success": True, "message": "Login successful"}
            else:
                logger.warning(f"Login failed for user: {username}")
                return {"success": False, "message": "Login failed - please check your credentials and try again"}
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return {"success": False, "message": f"Authentication error: {str(e)}"}
    
    async def logout(self) -> Dict[str, Any]:
        """Logout from Robinhood"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, rh.logout)
            self._authenticated = False
            self.username = None
            self.robinhood_user_id = None
            logger.info("User logged out successfully")
            return {"success": True, "message": "Logged out successfully"}
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return {"success": False, "message": f"Logout failed: {str(e)}"}
    
    async def is_logged_in(self) -> bool:
        """Check both our internal state and robin-stocks state"""
        try:
            # Try to make a simple API call to verify active session
            loop = asyncio.get_event_loop()
            profile = await loop.run_in_executor(None, rh.load_account_profile)
            if profile:
                self._authenticated = True
                return True
            else:
                self._authenticated = False
                return False
        except Exception:
            self._authenticated = False
            return False
    
    def get_username(self) -> Optional[str]:
        """Get the current username"""
        return self.username
    
    def get_robinhood_user_id(self) -> Optional[str]:
        """Get the Robinhood user ID"""
        return self.robinhood_user_id
    
    async def verify_session(self) -> Dict[str, Any]:
        """Verify that the current session is still valid"""
        try:
            # Try a simple API call that requires authentication
            loop = asyncio.get_event_loop()
            profile = await loop.run_in_executor(None, rh.load_account_profile)
            if profile:
                return {"success": True, "message": "Session valid"}
            else:
                return {"success": False, "message": "Session expired"}
        except Exception as e:
            logger.warning(f"Session verification failed: {str(e)}")
            return {"success": False, "message": "Session invalid"}
    
    
    def _dump_json_data(self, data: Any, filename: str) -> Optional[str]:
        """Dump JSON data to file for debugging"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.debug_dir, f"{timestamp}_{filename}")
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Dumped debug data to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to dump JSON data: {str(e)}")
            return None
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        cache_key = "portfolio:summary"
        
        # Try cache first
        cached_data = await cache.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            loop = asyncio.get_event_loop()
            
            # Get portfolio data
            portfolio_data = await loop.run_in_executor(None, rh.load_portfolio_profile)
            account_data = await loop.run_in_executor(None, rh.get_account)
            
            # Debug dump
            self._dump_json_data(portfolio_data, "portfolio_summary.json")
            
            if not portfolio_data:
                return {"success": False, "message": "No portfolio data available"}
            
            # Parse portfolio metrics
            total_value = float(portfolio_data.get('total_return_today', 0))
            total_return = float(portfolio_data.get('total_return_today', 0))
            day_return = float(portfolio_data.get('total_return_today', 0))
            
            summary = {
                "success": True,
                "data": {
                    "total_value": total_value,
                    "total_return": total_return,
                    "day_return": day_return,
                    "raw_data": portfolio_data
                }
            }
            
            # Cache for 5 minutes
            await cache.set(cache_key, summary, ttl=settings.CACHE_TTL_POSITIONS)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error fetching portfolio summary: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def get_stock_positions(self) -> Dict[str, Any]:
        """Get stock positions"""
        cache_key = "stocks:positions"
        
        # Try cache first
        cached_data = await cache.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            loop = asyncio.get_event_loop()
            positions = await loop.run_in_executor(None, rh.get_open_stock_positions)
            
            # Debug dump
            self._dump_json_data(positions, "stock_positions.json")
            
            if not positions:
                return {"success": True, "data": []}
            
            position_data = []
            for position in positions:
                try:
                    # Extract position data
                    symbol = position.get('symbol', 'UNKNOWN')
                    quantity = float(position.get('quantity', 0))
                    average_buy_price = float(position.get('average_buy_price', 0))
                    
                    # Get current price
                    current_price = 0
                    try:
                        price_data = await loop.run_in_executor(
                            None, lambda: rh.get_latest_price(symbol)
                        )
                        if price_data and len(price_data) > 0:
                            current_price = float(price_data[0])
                    except Exception:
                        current_price = average_buy_price
                    
                    # Calculate metrics
                    market_value = quantity * current_price
                    total_cost = quantity * average_buy_price
                    total_return = market_value - total_cost
                    percent_change = ((current_price - average_buy_price) / average_buy_price * 100) if average_buy_price > 0 else 0
                    
                    pos_data = {
                        "symbol": symbol,
                        "quantity": quantity,
                        "average_buy_price": average_buy_price,
                        "current_price": current_price,
                        "market_value": market_value,
                        "total_cost": total_cost,
                        "total_return": total_return,
                        "percent_change": percent_change,
                        "raw_data": position
                    }
                    
                    position_data.append(pos_data)
                    
                except Exception as e:
                    logger.error(f"Error processing stock position: {str(e)}")
                    continue
            
            result = {"success": True, "data": position_data}
            
            # Cache for 5 minutes
            await cache.set(cache_key, result, ttl=settings.CACHE_TTL_POSITIONS)
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching stock positions: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def get_options_positions(self) -> Dict[str, Any]:
        """Get options positions with enhanced analysis"""
        cache_key = "options:positions"
        
        # Try cache first
        cached_data = await cache.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            loop = asyncio.get_event_loop()
            positions = await loop.run_in_executor(None, rh.get_open_option_positions)
            
            # Debug dump
            self._dump_json_data(positions, "options_positions.json")
            
            if not positions:
                return {"success": True, "data": []}
            
            position_data = []
            for position in positions:
                try:
                    # Extract basic position info
                    quantity = float(position.get('quantity', 0))
                    average_price = float(position.get('average_price', 0))
                    
                    # Get clearing cost basis (processed_premium equivalent)
                    clearing_cost_basis = float(position.get('clearing_cost_basis', 0))
                    clearing_direction = position.get('clearing_direction', '')
                    
                    # Get option instrument details
                    instrument_url = position.get('option', '')
                    if not instrument_url:
                        continue
                    
                    instrument_id = instrument_url.split('/')[-2] if '/' in instrument_url else ''
                    instrument_data = await loop.run_in_executor(
                        None, lambda: rh.get_option_instrument_data_by_id(instrument_id)
                    )
                    
                    if not instrument_data:
                        continue
                    
                    # Extract option details
                    strike_price = float(instrument_data.get('strike_price', 0))
                    expiration_date = instrument_data.get('expiration_date', '')
                    option_type = instrument_data.get('type', '')
                    underlying_symbol = self._extract_underlying_symbol(instrument_data)
                    
                    # Get current option price and Greeks
                    current_price = 0
                    greeks = {
                        "delta": 0.0,
                        "gamma": 0.0, 
                        "theta": 0.0,
                        "vega": 0.0,
                        "rho": 0.0,
                        "implied_volatility": 0.0,
                        "open_interest": 0
                    }
                    
                    try:
                        market_data = await loop.run_in_executor(
                            None, lambda: rh.get_option_market_data_by_id(instrument_id)
                        )
                        if market_data and len(market_data) > 0:
                            data = market_data[0]
                            current_price = float(data.get('adjusted_mark_price', 0))
                            
                            # Extract Greeks from market data
                            greeks = {
                                "delta": float(data.get('delta', 0)) if data.get('delta') else 0.0,
                                "gamma": float(data.get('gamma', 0)) if data.get('gamma') else 0.0,
                                "theta": float(data.get('theta', 0)) if data.get('theta') else 0.0,
                                "vega": float(data.get('vega', 0)) if data.get('vega') else 0.0,
                                "rho": float(data.get('rho', 0)) if data.get('rho') else 0.0,
                                "implied_volatility": float(data.get('implied_volatility', 0)) if data.get('implied_volatility') else 0.0,
                                "open_interest": int(data.get('open_interest', 0)) if data.get('open_interest') else 0
                            }
                    except Exception as e:
                        logger.debug(f"Failed to get market data for option {instrument_id}: {str(e)}")
                        current_price = abs(average_price) if average_price else 0
                    
                    # Determine position type and transaction details
                    contracts = abs(quantity)
                    position_type_field = position.get('type', '').lower()
                    is_long_position = position_type_field == 'long'
                    
                    if is_long_position:
                        transaction_side = TransactionSide.BUY
                        position_effect = PositionEffect.OPEN
                        direction = Direction.DEBIT
                    else:
                        transaction_side = TransactionSide.SELL
                        position_effect = PositionEffect.OPEN
                        direction = Direction.CREDIT
                    
                    # Market value is always positive - represents current market value of the position
                    market_value = contracts * current_price * 100
                    logger.info(f"{underlying_symbol} ({position_type_field.upper()}): {contracts} * {current_price} * 100 = {market_value}")
                    
                    if clearing_cost_basis > 0:
                        # Use clearing cost basis for accurate P&L
                        if clearing_direction == 'credit':
                            # Short position: you received credit, now owe the current market value
                            total_cost = -clearing_cost_basis  # negative because you received money
                            total_return = clearing_cost_basis - market_value  # credit received - cost to close
                            credit_per_share = clearing_cost_basis / (contracts * 100)
                            percent_change = ((credit_per_share - current_price) / credit_per_share * 100) if credit_per_share > 0 else 0
                            display_average_price = clearing_cost_basis / (contracts * 100)
                        else:  # debit
                            total_cost = clearing_cost_basis
                            total_return = market_value - clearing_cost_basis
                            premium_per_share = clearing_cost_basis / (contracts * 100)
                            percent_change = ((current_price - premium_per_share) / premium_per_share * 100) if premium_per_share > 0 else 0
                            display_average_price = clearing_cost_basis / (contracts * 100)
                    else:
                        # Fallback to old method
                        if is_long_position:
                            # Long position: you paid debit, current value is what you can sell for
                            total_cost = contracts * average_price * 100
                            total_return = market_value - total_cost
                            percent_change = ((current_price - average_price) / average_price * 100) if average_price > 0 else 0
                            display_average_price = average_price
                        else:
                            # Short position: you received credit, current market value is cost to close
                            credit_received = abs(average_price)
                            credit_total = contracts * credit_received * 100
                            total_cost = -credit_total  # negative because you received money
                            total_return = credit_total - market_value  # credit received - cost to close
                            credit_per_share = credit_received
                            percent_change = ((credit_per_share - current_price) / credit_per_share * 100) if credit_per_share > 0 else 0
                            display_average_price = credit_received
                    
                    # Determine strategy
                    strategy = self._determine_strategy(underlying_symbol, option_type, transaction_side, position_effect)
                    
                    # Calculate days to expiry
                    days_to_expiry = self._calculate_days_to_expiry(expiration_date)
                    
                    pos_data = {
                        "underlying_symbol": underlying_symbol,
                        "strike_price": strike_price,
                        "expiration_date": expiration_date,
                        "option_type": option_type,
                        "transaction_side": transaction_side.value,
                        "position_effect": position_effect.value,
                        "direction": clearing_direction or direction.value,
                        "quantity": quantity,
                        "contracts": contracts,
                        "position_type": "long" if is_long_position else "short",
                        "average_price": display_average_price,
                        "current_price": current_price,
                        "market_value": market_value,
                        "total_cost": total_cost,
                        "total_return": total_return,
                        "percent_change": percent_change,
                        "days_to_expiry": days_to_expiry,
                        "clearing_cost_basis": clearing_cost_basis,
                        "clearing_direction": clearing_direction,
                        "strategy": strategy,
                        "greeks": greeks,
                        "raw_data": position
                    }
                    
                    position_data.append(pos_data)
                    
                except Exception as e:
                    logger.error(f"Error processing options position: {str(e)}")
                    continue
            
            result = {"success": True, "data": position_data}
            
            # Cache for 5 minutes
            await cache.set(cache_key, result, ttl=settings.CACHE_TTL_POSITIONS)
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching options positions: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def get_options_orders(self, limit: int = 50, since_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get options orders with legs and executions"""
        # Include all parameters in cache key
        since_key = since_time.isoformat() if since_time else "all"
        cache_key = f"options:orders:{limit}:{since_key}"
        
        # Try cache first
        cached_data = await cache.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            loop = asyncio.get_event_loop()
            # Add timeout to prevent hanging
            orders = await asyncio.wait_for(
                loop.run_in_executor(None, rh.get_all_option_orders),
                timeout=60.0  # 60 second timeout
            )
            
            # Debug dump
            self._dump_json_data(orders, "options_orders.json")
            
            if not orders:
                return {"success": True, "data": []}
            
            # Filter by time if provided
            if since_time:
                filtered_orders = []
                for order in orders:
                    try:
                        order_time = datetime.fromisoformat(order.get('created_at', '').replace('Z', '+00:00'))
                        if order_time >= since_time:
                            filtered_orders.append(order)
                    except (ValueError, TypeError):
                        filtered_orders.append(order)
                orders = filtered_orders
            
            # Limit results
            orders = orders[:limit]
            
            order_data = []
            for order in orders:
                try:
                    order_info = await self._process_options_order(order)
                    order_data.append(order_info)
                except Exception as e:
                    logger.error(f"Error processing options order: {str(e)}")
                    continue
            
            result = {"success": True, "data": order_data}
            
            # Cache for 1 hour
            await cache.set(cache_key, result, ttl=settings.CACHE_TTL_ORDERS)
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching options orders: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def _process_options_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single options order with legs and executions"""
        loop = asyncio.get_event_loop()
        
        # Basic order info
        order_info = {
            "order_id": order.get('id', ''),
            "underlying_symbol": "UNKNOWN",
            "strike_price": 0.0,
            "expiration_date": "",
            "option_type": "",
            "transaction_side": "",
            "position_effect": "",
            "direction": order.get('direction', ''),
            "quantity": float(order.get('quantity', 0)),
            "price": float(order.get('price', 0)) if order.get('price') else 0,
            "premium": float(order.get('premium', 0)) if order.get('premium') else 0,
            "processed_premium": float(order.get('processed_premium', 0)) if order.get('processed_premium') else 0,
            "processed_premium_direction": order.get('processed_premium_direction', ''),
            "state": order.get('state', ''),
            "created_at": order.get('created_at', ''),
            "updated_at": order.get('updated_at', ''),
            "type": order.get('type', 'limit'),
            "legs_count": 0,
            "legs_details": [],
            "executions_count": 0,
            # New fields for rolled options detection
            "chain_id": order.get('chain_id', ''),
            "chain_symbol": order.get('chain_symbol', ''),
            "closing_strategy": order.get('closing_strategy'),
            "opening_strategy": order.get('opening_strategy'),
            "strategy": order.get('strategy', '')
        }
        
        # Process legs
        legs = order.get('legs', [])
        if legs:
            order_info["legs_count"] = len(legs)
            leg_details = []
            
            for i, leg in enumerate(legs):
                leg_detail = {
                    "leg_index": i,
                    "side": leg.get('side', ''),
                    "position_effect": leg.get('position_effect', ''),
                    "option_type": leg.get('option_type', ''),
                    "quantity": float(leg.get('quantity', 0)),
                    "ratio_quantity": float(leg.get('ratio_quantity', 0)),
                    "instrument_url": leg.get('option', ''),
                    "underlying_symbol": "UNKNOWN",
                    "strike_price": 0.0,
                    "expiration_date": "",
                    "instrument_id": "",
                    "executions_count": len(leg.get('executions', []))
                }
                
                # Get instrument details
                instrument_url = leg.get('option', '')
                if instrument_url:
                    try:
                        instrument_id = instrument_url.split('/')[-2] if '/' in instrument_url else ''
                        leg_detail["instrument_id"] = instrument_id
                        
                        instrument_data = await loop.run_in_executor(
                            None, lambda: rh.get_option_instrument_data_by_id(instrument_id)
                        )
                        
                        if instrument_data:
                            leg_detail.update({
                                "underlying_symbol": self._extract_underlying_symbol(instrument_data),
                                "strike_price": float(instrument_data.get('strike_price', 0)),
                                "expiration_date": instrument_data.get('expiration_date', ''),
                                "option_type": leg.get('option_type', '') or instrument_data.get('type', ''),
                            })
                    except Exception as e:
                        logger.warning(f"Could not get instrument data for leg {i}: {str(e)}")
                
                leg_details.append(leg_detail)
            
            order_info["legs_details"] = leg_details
            
            # Use first leg for primary order info
            if leg_details:
                first_leg = leg_details[0]
                order_info.update({
                    "transaction_side": first_leg.get('side', ''),
                    "position_effect": first_leg.get('position_effect', ''),
                    "option_type": first_leg.get('option_type', ''),
                    "underlying_symbol": first_leg.get('underlying_symbol', 'UNKNOWN'),
                    "strike_price": first_leg.get('strike_price', 0.0),
                    "expiration_date": first_leg.get('expiration_date', ''),
                })
                
                # Determine strategy for the order
                strategy = self._determine_strategy(
                    first_leg.get('underlying_symbol', 'UNKNOWN'),
                    first_leg.get('option_type', ''),
                    first_leg.get('side', ''),
                    first_leg.get('position_effect', '')
                )
                order_info["strategy"] = strategy
        
        return order_info
    
    def _extract_underlying_symbol(self, instrument_data: Dict[str, Any]) -> str:
        """Extract underlying symbol from instrument data"""
        if not instrument_data:
            return "UNKNOWN"
        
        # Try chain_symbol first
        if 'chain_symbol' in instrument_data and instrument_data['chain_symbol']:
            return instrument_data['chain_symbol']
        
        # Try direct symbol field
        if 'symbol' in instrument_data and instrument_data['symbol']:
            return instrument_data['symbol']
        
        # Try to extract from chain URL
        chain_url = instrument_data.get('chain', '')
        if chain_url and '/chains/' in chain_url:
            try:
                parts = chain_url.split('/chains/')
                if len(parts) > 1:
                    chain_part = parts[1].split('/')[0]
                    if chain_part and len(chain_part) <= 6 and chain_part.replace('-', '').isalnum():
                        return chain_part.upper().replace('-', '.')
            except Exception:
                pass
        
        return "UNKNOWN"
    
    def _determine_strategy(self, underlying_symbol: str, option_type: str, transaction_side: str, position_effect: str) -> str:
        """Determine the options trading strategy with enhanced categorization"""
        try:
            if not option_type or not transaction_side:
                return "UNKNOWN"
            
            option_type = option_type.lower()
            transaction_side = transaction_side.lower()
            position_effect = position_effect.lower() if position_effect else ""
            
            # Enhanced strategy classification
            if option_type == 'call':
                if transaction_side == 'buy':
                    if position_effect == 'open':
                        return "BUY CALL"  # Long call - bullish
                    elif position_effect == 'close':
                        return "BUY TO CLOSE CALL"  # Closing short call
                    else:
                        return "LONG CALL"
                elif transaction_side == 'sell':
                    if position_effect == 'open':
                        return "SELL CALL"  # Short call - bearish/neutral
                    elif position_effect == 'close':
                        return "SELL TO CLOSE CALL"  # Closing long call
                    else:
                        return "SHORT CALL"
            elif option_type == 'put':
                if transaction_side == 'buy':
                    if position_effect == 'open':
                        return "BUY PUT"  # Long put - bearish
                    elif position_effect == 'close':
                        return "BUY TO CLOSE PUT"  # Closing short put
                    else:
                        return "LONG PUT"
                elif transaction_side == 'sell':
                    if position_effect == 'open':
                        return "SELL PUT"  # Short put - bullish/neutral
                    elif position_effect == 'close':
                        return "SELL TO CLOSE PUT"  # Closing long put  
                    else:
                        return "SHORT PUT"
            
            return "SINGLE LEG"
            
        except Exception as e:
            logger.error(f"Error determining strategy: {str(e)}")
            return "UNKNOWN"
    
    def _calculate_days_to_expiry(self, expiration_date: str) -> int:
        """Calculate days until option expiration"""
        try:
            if not expiration_date:
                return 0
            exp_date = datetime.strptime(expiration_date, '%Y-%m-%d')
            today = datetime.now()
            return max(0, (exp_date - today).days)
        except Exception:
            return 0
    
    async def get_portfolio_greeks(self) -> Dict[str, Any]:
        """Calculate portfolio-level Greeks exposure"""
        try:
            # Get all options positions
            options_result = await self.get_options_positions()
            if not options_result.get("success", False):
                return {"success": False, "message": "Failed to fetch options positions"}
            
            positions = options_result["data"]
            
            # Calculate aggregate Greeks
            portfolio_greeks = {
                "net_delta": 0.0,
                "net_gamma": 0.0,
                "net_theta": 0.0,
                "net_vega": 0.0,
                "net_rho": 0.0,
                "total_positions": len(positions),
                "long_delta": 0.0,
                "short_delta": 0.0,
                "daily_theta_decay": 0.0,
                "vega_exposure": 0.0
            }
            
            for position in positions:
                contracts = position.get("contracts", 0)
                position_type = position.get("position_type", "")
                greeks = position.get("greeks", {})
                
                # Adjust Greeks based on position size and direction
                delta = greeks.get("delta", 0) * contracts * 100  # Delta per $1 move
                gamma = greeks.get("gamma", 0) * contracts * 100  # Gamma per $1 move
                theta = greeks.get("theta", 0) * contracts  # Theta per day
                vega = greeks.get("vega", 0) * contracts  # Vega per 1% IV change
                rho = greeks.get("rho", 0) * contracts  # Rho per 1% rate change
                
                # Adjust for short positions (Greeks flip sign)
                if position_type == "short":
                    delta = -delta
                    gamma = -gamma
                    theta = -theta
                    vega = -vega
                    rho = -rho
                
                # Aggregate portfolio Greeks
                portfolio_greeks["net_delta"] += delta
                portfolio_greeks["net_gamma"] += gamma
                portfolio_greeks["net_theta"] += theta
                portfolio_greeks["net_vega"] += vega
                portfolio_greeks["net_rho"] += rho
                
                # Track long/short delta separately
                if delta > 0:
                    portfolio_greeks["long_delta"] += delta
                else:
                    portfolio_greeks["short_delta"] += abs(delta)
                
                # Daily theta decay (how much portfolio loses per day from time decay)
                portfolio_greeks["daily_theta_decay"] += abs(theta)
                
                # Vega exposure (sensitivity to volatility changes)
                portfolio_greeks["vega_exposure"] += abs(vega)
            
            # Calculate risk metrics
            portfolio_greeks["delta_neutral"] = abs(portfolio_greeks["net_delta"]) < 10  # Within $10 delta
            portfolio_greeks["theta_positive"] = portfolio_greeks["net_theta"] > 0  # Benefiting from time decay
            
            return {"success": True, "data": portfolio_greeks}
            
        except Exception as e:
            logger.error(f"Error calculating portfolio Greeks: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def get_ticker_performance_analysis(self) -> Dict[str, Any]:
        """Analyze performance by ticker combining positions and orders"""
        try:
            # Get current positions
            positions_result = await self.get_options_positions()
            if not positions_result.get("success", False):
                return {"success": False, "message": "Failed to fetch options positions"}
            
            # Get historical orders
            orders_result = await self.get_options_orders(limit=100)
            if not orders_result.get("success", False):
                return {"success": False, "message": "Failed to fetch options orders"}
            
            positions = positions_result["data"]
            orders = orders_result["data"]
            
            logger.info(f"Processing {len(positions)} positions and {len(orders)} orders for ticker performance analysis")
            
            # Group performance by ticker
            ticker_stats = {}
            
            # Process current positions
            for position in positions:
                symbol = position.get("underlying_symbol", "UNKNOWN")
                if symbol not in ticker_stats:
                    ticker_stats[symbol] = {
                        "symbol": symbol,
                        "total_trades": 0,
                        "total_return": 0.0,
                        "total_cost": 0.0,
                        "winners": 0,
                        "losers": 0,
                        "current_positions": 0,
                        "historical_positions": 0
                    }
                
                stats = ticker_stats[symbol]
                stats["current_positions"] += 1
                stats["total_return"] += position.get("total_return", 0)
                stats["total_cost"] += abs(position.get("total_cost", 0))
                
                if position.get("total_return", 0) > 0:
                    stats["winners"] += 1
                elif position.get("total_return", 0) < 0:
                    stats["losers"] += 1
            
            # Process historical orders (filled only)
            filled_orders = [order for order in orders if order.get("state", "") == "filled"]
            
            for order in filled_orders:
                symbol = order.get("underlying_symbol", "UNKNOWN")
                if symbol not in ticker_stats:
                    ticker_stats[symbol] = {
                        "symbol": symbol,
                        "total_trades": 0,
                        "total_return": 0.0,
                        "total_cost": 0.0,
                        "winners": 0,
                        "losers": 0,
                        "current_positions": 0,
                        "historical_positions": 0
                    }
                
                stats = ticker_stats[symbol]
                stats["total_trades"] += 1
                stats["historical_positions"] += 1
                
                # Estimate profit/loss from filled orders
                premium = order.get("processed_premium", 0) or order.get("premium", 0)
                if premium > 0:
                    stats["total_cost"] += premium
            
            # Calculate derived metrics
            for symbol, stats in ticker_stats.items():
                total_positions = stats["winners"] + stats["losers"]
                stats["win_rate"] = (stats["winners"] / total_positions * 100) if total_positions > 0 else 0
                stats["return_percentage"] = (stats["total_return"] / stats["total_cost"] * 100) if stats["total_cost"] > 0 else 0
                stats["avg_return_per_trade"] = (stats["total_return"] / stats["total_trades"]) if stats["total_trades"] > 0 else 0
            
            # Sort by total return descending
            sorted_stats = sorted(ticker_stats.values(), key=lambda x: x["total_return"], reverse=True)
            
            logger.info(f"Ticker performance analysis complete: {len(sorted_stats)} tickers found")
            if sorted_stats:
                logger.info(f"Top ticker: {sorted_stats[0]['symbol']} with return ${sorted_stats[0]['total_return']:.2f}")
            
            return {"success": True, "data": sorted_stats}
            
        except Exception as e:
            logger.error(f"Error analyzing ticker performance: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def calculate_options_pnl_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate comprehensive options P&L summary with cached data and background processing"""
        try:
            logger.info("Starting P&L summary calculation...")
            
            # Import here to avoid circular imports
            from app.services.options_pnl_background_service import pnl_background_service
            
            # Try to get user_id - in a real implementation, this would come from auth
            # For now, we'll use a dummy UUID or the first user we find
            if not user_id:
                import uuid
                user_id = uuid.uuid4()  # This should be replaced with actual user from auth
            
            # Try to get cached data first
            cached_data = await pnl_background_service.get_cached_pnl(user_id)
            
            # Get current positions for unrealized P&L (always fresh)
            positions_result = await self.get_options_positions()
            if not positions_result.get("success", False):
                logger.error("Failed to fetch options positions")
                return {"success": False, "message": "Failed to fetch options positions"}
            
            positions = positions_result["data"]
            logger.info(f"Fetched {len(positions)} positions")
            
            # Calculate current unrealized P&L (fast)
            unrealized_data = self._calculate_unrealized_pnl(positions)
            logger.info(f"Calculated unrealized P&L: {unrealized_data['total_pnl']}")
            
            # Use cached realized data if available, otherwise use empty data and trigger background processing
            if cached_data and cached_data["calculation_info"]["status"] == "completed":
                logger.info("Using cached realized P&L data")
                cached_analytics = cached_data["analytics"]
                realized_data = {
                    "total_pnl": cached_analytics["realized_pnl"],
                    "trade_count": cached_analytics["realized_trades"],
                    "winning_trades": cached_analytics["winning_trades"] - unrealized_data["winning_positions"],
                    "losing_trades": cached_analytics["losing_trades"] - unrealized_data["losing_positions"],
                    "largest_winner": cached_analytics["largest_winner"],
                    "largest_loser": cached_analytics["largest_loser"],
                    "yearly_breakdown": cached_data["yearly_breakdown"],
                    "symbol_breakdown": {
                        symbol["symbol"]: {
                            "total_pnl": symbol["realized_pnl"],
                            "trade_count": symbol["realized_trades"],
                            "winning_trades": symbol["winning_trades"] - 
                                (unrealized_data["symbol_breakdown"].get(symbol["symbol"], {}).get("winning_positions", 0)),
                            "losing_trades": symbol["losing_trades"] - 
                                (unrealized_data["symbol_breakdown"].get(symbol["symbol"], {}).get("losing_positions", 0))
                        }
                        for symbol in cached_data["symbol_breakdown"]
                        if symbol["realized_trades"] > 0
                    }
                }
            else:
                logger.info("No cached realized P&L data available, using empty data and triggering background processing")
                # Trigger background processing for this user
                await pnl_background_service.trigger_user_pnl_processing(user_id)
                
                # Use empty realized data for now
                realized_data = {
                    "total_pnl": 0.0,
                    "trade_count": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "largest_winner": 0.0,
                    "largest_loser": 0.0,
                    "yearly_breakdown": [],
                    "symbol_breakdown": {}
                }
            
            # Combine results
            total_pnl = realized_data["total_pnl"] + unrealized_data["total_pnl"]
            total_trades = realized_data["trade_count"] + unrealized_data["position_count"]
            
            winning_trades = realized_data["winning_trades"] + unrealized_data["winning_positions"]
            losing_trades = realized_data["losing_trades"] + unrealized_data["losing_positions"]
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            pnl_summary = {
                "total_pnl": round(total_pnl, 2),
                "realized_pnl": round(realized_data["total_pnl"], 2),
                "unrealized_pnl": round(unrealized_data["total_pnl"], 2),
                "total_trades": total_trades,
                "realized_trades": realized_data["trade_count"],
                "open_positions": unrealized_data["position_count"],
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "largest_winner": round(max(realized_data["largest_winner"], unrealized_data["largest_winner"]), 2),
                "largest_loser": round(min(realized_data["largest_loser"], unrealized_data["largest_loser"]), 2),
                "avg_trade_pnl": round(total_pnl / total_trades, 2) if total_trades > 0 else 0,
                "realized_breakdown": realized_data["yearly_breakdown"],
                "symbol_breakdown": self._combine_symbol_pnl(realized_data["symbol_breakdown"], unrealized_data["symbol_breakdown"]),
                "cache_info": cached_data["calculation_info"] if cached_data else {
                    "status": "processing",
                    "message": "Realized P&L calculation started in background"
                }
            }
            
            logger.info("P&L summary calculation completed successfully")
            return {"success": True, "data": pnl_summary}
            
        except Exception as e:
            logger.error(f"Error calculating options P&L summary: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def _calculate_unrealized_pnl(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate unrealized P&L from current positions"""
        total_pnl = 0.0
        position_count = len(positions)
        winning_positions = 0
        losing_positions = 0
        largest_winner = 0.0
        largest_loser = 0.0
        symbol_breakdown = {}
        
        for position in positions:
            pnl = position.get("total_return", 0)
            symbol = position.get("underlying_symbol", "UNKNOWN")
            
            total_pnl += pnl
            
            if pnl > 0:
                winning_positions += 1
                largest_winner = max(largest_winner, pnl)
            elif pnl < 0:
                losing_positions += 1
                largest_loser = min(largest_loser, pnl)
            
            # Symbol breakdown
            if symbol not in symbol_breakdown:
                symbol_breakdown[symbol] = {
                    "symbol": symbol,
                    "total_pnl": 0.0,
                    "position_count": 0,
                    "winning_positions": 0,
                    "losing_positions": 0
                }
            
            symbol_breakdown[symbol]["total_pnl"] += pnl
            symbol_breakdown[symbol]["position_count"] += 1
            if pnl > 0:
                symbol_breakdown[symbol]["winning_positions"] += 1
            elif pnl < 0:
                symbol_breakdown[symbol]["losing_positions"] += 1
        
        return {
            "total_pnl": total_pnl,
            "position_count": position_count,
            "winning_positions": winning_positions,
            "losing_positions": losing_positions,
            "largest_winner": largest_winner,
            "largest_loser": largest_loser,
            "symbol_breakdown": symbol_breakdown
        }
    
    async def _calculate_realized_pnl(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate realized P&L from filled orders by matching opens and closes"""
        # Filter to filled orders only
        filled_orders = [order for order in orders if order.get("state") == "filled"]
        
        # Match opening and closing orders
        matched_trades = self._match_opening_closing_orders(filled_orders)
        
        total_pnl = 0.0
        trade_count = len(matched_trades)
        winning_trades = 0
        losing_trades = 0
        largest_winner = 0.0
        largest_loser = 0.0
        yearly_breakdown = {}
        symbol_breakdown = {}
        
        for trade in matched_trades:
            pnl = trade["pnl"]
            symbol = trade["symbol"]
            close_year = trade.get("close_year", datetime.now().year)
            
            total_pnl += pnl
            
            if pnl > 0:
                winning_trades += 1
                largest_winner = max(largest_winner, pnl)
            elif pnl < 0:
                losing_trades += 1
                largest_loser = min(largest_loser, pnl)
            
            # Yearly breakdown
            if close_year not in yearly_breakdown:
                yearly_breakdown[close_year] = {
                    "year": close_year,
                    "realized_pnl": 0.0,
                    "trade_count": 0,
                    "winning_trades": 0,
                    "losing_trades": 0
                }
            
            yearly_breakdown[close_year]["realized_pnl"] += pnl
            yearly_breakdown[close_year]["trade_count"] += 1
            if pnl > 0:
                yearly_breakdown[close_year]["winning_trades"] += 1
            elif pnl < 0:
                yearly_breakdown[close_year]["losing_trades"] += 1
            
            # Symbol breakdown
            if symbol not in symbol_breakdown:
                symbol_breakdown[symbol] = {
                    "symbol": symbol,
                    "total_pnl": 0.0,
                    "trade_count": 0,
                    "winning_trades": 0,
                    "losing_trades": 0
                }
            
            symbol_breakdown[symbol]["total_pnl"] += pnl
            symbol_breakdown[symbol]["trade_count"] += 1
            if pnl > 0:
                symbol_breakdown[symbol]["winning_trades"] += 1
            elif pnl < 0:
                symbol_breakdown[symbol]["losing_trades"] += 1
        
        # Calculate win rates for yearly breakdown
        for year_data in yearly_breakdown.values():
            total = year_data["winning_trades"] + year_data["losing_trades"]
            year_data["win_rate"] = (year_data["winning_trades"] / total * 100) if total > 0 else 0
        
        return {
            "total_pnl": total_pnl,
            "trade_count": trade_count,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "largest_winner": largest_winner,
            "largest_loser": largest_loser,
            "yearly_breakdown": sorted(yearly_breakdown.values(), key=lambda x: x["year"]),
            "symbol_breakdown": symbol_breakdown
        }
    
    def _match_opening_closing_orders(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Match opening and closing orders to calculate realized P&L"""
        from collections import defaultdict
        
        trades = []
        
        # Group orders by symbol + strike + expiry + option_type
        position_groups = defaultdict(list)
        
        for order in orders:
            symbol = order.get("underlying_symbol", "")
            strike = order.get("strike_price", 0)
            expiry = order.get("expiration_date", "")
            option_type = order.get("option_type", "")
            
            if not symbol or not strike:
                continue
                
            key = (symbol, str(strike), expiry, option_type)
            position_groups[key].append(order)
        
        # Match opening and closing orders within each group
        for key, group_orders in position_groups.items():
            # Sort by creation date
            group_orders.sort(key=lambda x: x.get("created_at", ""))
            
            open_orders = []
            
            for order in group_orders:
                position_effect = order.get("position_effect", "")
                processed_premium = order.get("processed_premium", 0) or order.get("premium", 0)
                
                if position_effect == "open":
                    open_orders.append(order)
                elif position_effect == "close" and open_orders:
                    # Match with the first open order (FIFO)
                    open_order = open_orders.pop(0)
                    
                    # Calculate P&L
                    pnl = self._calculate_trade_pnl(open_order, order)
                    
                    # Extract close date for yearly breakdown
                    close_date = order.get("created_at", "")
                    close_year = datetime.now().year
                    if close_date:
                        try:
                            close_year = datetime.fromisoformat(close_date.replace('Z', '+00:00')).year
                        except:
                            pass
                    
                    trades.append({
                        "symbol": order.get("underlying_symbol", ""),
                        "strike_price": order.get("strike_price", 0),
                        "expiration_date": order.get("expiration_date", ""),
                        "option_type": order.get("option_type", ""),
                        "open_date": open_order.get("created_at", ""),
                        "close_date": order.get("created_at", ""),
                        "close_year": close_year,
                        "contracts": abs(order.get("quantity", 0)),
                        "opening_premium": open_order.get("processed_premium", 0) or open_order.get("premium", 0),
                        "closing_premium": order.get("processed_premium", 0) or order.get("premium", 0),
                        "pnl": pnl
                    })
        
        return trades
    
    def _calculate_trade_pnl(self, open_order: Dict[str, Any], close_order: Dict[str, Any]) -> float:
        """Calculate P&L for a matched open/close trade pair"""
        try:
            open_premium = float(open_order.get("processed_premium", 0) or open_order.get("premium", 0))
            close_premium = float(close_order.get("processed_premium", 0) or close_order.get("premium", 0))
            contracts = abs(float(close_order.get("quantity", 0)))
            
            # Determine if this was a long or short position based on direction
            open_direction = open_order.get("direction", "").lower()
            close_direction = close_order.get("direction", "").lower()
            
            if open_direction == "debit":
                # Long position: paid to open, received to close
                # P&L = (close_premium - open_premium) * contracts * 100
                pnl = (close_premium - open_premium) * contracts * 100
            elif open_direction == "credit":
                # Short position: received to open, paid to close
                # P&L = (open_premium - close_premium) * contracts * 100
                pnl = (open_premium - close_premium) * contracts * 100
            else:
                # Fallback: assume based on processed_premium_direction
                open_dir = open_order.get("processed_premium_direction", "").lower()
                if open_dir == "credit":
                    pnl = (open_premium - close_premium) * contracts * 100
                else:
                    pnl = (close_premium - open_premium) * contracts * 100
            
            return pnl
            
        except Exception as e:
            logger.error(f"Error calculating trade P&L: {str(e)}")
            return 0.0
    
    def _combine_symbol_pnl(self, realized_breakdown: Dict, unrealized_breakdown: Dict) -> List[Dict[str, Any]]:
        """Combine realized and unrealized P&L by symbol"""
        combined = {}
        
        # Add realized data
        for symbol, data in realized_breakdown.items():
            combined[symbol] = {
                "symbol": symbol,
                "total_pnl": data["total_pnl"],
                "realized_pnl": data["total_pnl"],
                "unrealized_pnl": 0.0,
                "total_trades": data["trade_count"],
                "realized_trades": data["trade_count"],
                "open_positions": 0,
                "winning_trades": data["winning_trades"],
                "losing_trades": data["losing_trades"]
            }
        
        # Add unrealized data
        for symbol, data in unrealized_breakdown.items():
            if symbol not in combined:
                combined[symbol] = {
                    "symbol": symbol,
                    "total_pnl": data["total_pnl"],
                    "realized_pnl": 0.0,
                    "unrealized_pnl": data["total_pnl"],
                    "total_trades": data["position_count"],
                    "realized_trades": 0,
                    "open_positions": data["position_count"],
                    "winning_trades": data["winning_positions"],
                    "losing_trades": data["losing_positions"]
                }
            else:
                combined[symbol]["total_pnl"] += data["total_pnl"]
                combined[symbol]["unrealized_pnl"] = data["total_pnl"]
                combined[symbol]["total_trades"] += data["position_count"]
                combined[symbol]["open_positions"] = data["position_count"]
                combined[symbol]["winning_trades"] += data["winning_positions"]
                combined[symbol]["losing_trades"] += data["losing_positions"]
        
        # Calculate win rates and sort by total P&L
        symbol_list = []
        for symbol_data in combined.values():
            total_trades = symbol_data["winning_trades"] + symbol_data["losing_trades"]
            symbol_data["win_rate"] = (symbol_data["winning_trades"] / total_trades * 100) if total_trades > 0 else 0
            symbol_data["avg_trade_pnl"] = symbol_data["total_pnl"] / symbol_data["total_trades"] if symbol_data["total_trades"] > 0 else 0
            symbol_list.append(symbol_data)
        
        return sorted(symbol_list, key=lambda x: x["total_pnl"], reverse=True)

    async def _get_robinhood_user_id(self) -> Optional[str]:
        """Get Robinhood user ID from API"""
        try:
            loop = asyncio.get_event_loop()
            
            # Try to get user profile first
            user_profile = await loop.run_in_executor(None, rh.load_user_profile)
            if user_profile and user_profile.get('id'):
                return user_profile['id']
            
            # Fallback to account profile
            account_profile = await loop.run_in_executor(None, rh.load_account_profile)
            if account_profile and account_profile.get('id'):
                return account_profile['id']
            
            logger.warning("Could not retrieve Robinhood user ID from API")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Robinhood user ID: {str(e)}")
            return None