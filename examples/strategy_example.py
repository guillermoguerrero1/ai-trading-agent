#!/usr/bin/env python3
"""
Example strategy integration for AI Trading Agent

This example shows how to integrate a trading strategy with the AI Trading Agent system.
"""

import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
import json


class ExampleStrategy:
    """Example trading strategy."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize strategy.
        
        Args:
            api_base_url: API base URL
        """
        self.api_base_url = api_base_url
        self.client = httpx.AsyncClient()
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get market data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Market data
        """
        # In a real implementation, this would fetch from a market data provider
        # For this example, we'll simulate market data
        return {
            "symbol": symbol,
            "price": 150.0,
            "volume": 1000000,
            "timestamp": datetime.utcnow().isoformat(),
            "indicators": {
                "sma_20": 148.5,
                "sma_50": 145.0,
                "rsi": 65.0,
                "macd": 2.5,
                "bollinger_upper": 155.0,
                "bollinger_lower": 142.0
            }
        }
    
    async def analyze_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze market data and generate trading signal.
        
        Args:
            market_data: Market data
            
        Returns:
            Trading signal or None
        """
        symbol = market_data["symbol"]
        price = market_data["price"]
        indicators = market_data["indicators"]
        
        # Simple momentum strategy
        sma_20 = indicators["sma_20"]
        sma_50 = indicators["sma_50"]
        rsi = indicators["rsi"]
        
        # Buy signal: price above SMA20, SMA20 above SMA50, RSI not overbought
        if price > sma_20 and sma_20 > sma_50 and rsi < 70:
            return {
                "signal_type": "BUY",
                "symbol": symbol,
                "quantity": 100,
                "price": price,
                "confidence": 0.8,
                "metadata": {
                    "strategy": "momentum",
                    "timeframe": "1h",
                    "indicators": {
                        "sma_20": sma_20,
                        "sma_50": sma_50,
                        "rsi": rsi
                    },
                    "reason": "Price above SMA20, SMA20 above SMA50, RSI not overbought"
                }
            }
        
        # Sell signal: price below SMA20, RSI overbought
        elif price < sma_20 and rsi > 80:
            return {
                "signal_type": "SELL",
                "symbol": symbol,
                "quantity": 100,
                "price": price,
                "confidence": 0.7,
                "metadata": {
                    "strategy": "momentum",
                    "timeframe": "1h",
                    "indicators": {
                        "sma_20": sma_20,
                        "sma_50": sma_50,
                        "rsi": rsi
                    },
                    "reason": "Price below SMA20, RSI overbought"
                }
            }
        
        return None
    
    async def submit_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Submit trading signal to the API.
        
        Args:
            signal: Trading signal
            
        Returns:
            True if successful
        """
        try:
            response = await self.client.post(
                f"{self.api_base_url}/v1/signal/",
                json=signal
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ Signal submitted successfully: {result}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to submit signal: {e}")
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status.
        
        Returns:
            System status
        """
        try:
            response = await self.client.get(f"{self.api_base_url}/v1/health/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get system status: {e}")
            return {}
    
    async def get_positions(self) -> Dict[str, Any]:
        """
        Get current positions.
        
        Returns:
            Current positions
        """
        try:
            response = await self.client.get(f"{self.api_base_url}/v1/pnl/positions")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get positions: {e}")
            return {}
    
    async def get_daily_pnl(self) -> Dict[str, Any]:
        """
        Get daily P&L.
        
        Returns:
            Daily P&L
        """
        try:
            response = await self.client.get(f"{self.api_base_url}/v1/pnl/daily")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get daily P&L: {e}")
            return {}
    
    async def run_strategy(self, symbols: list[str], interval: int = 60):
        """
        Run the trading strategy.
        
        Args:
            symbols: List of symbols to trade
            interval: Check interval in seconds
        """
        print(f"🚀 Starting strategy for symbols: {symbols}")
        print(f"⏰ Check interval: {interval} seconds")
        print("")
        
        while True:
            try:
                # Check system status
                status = await self.get_system_status()
                if status.get("status") != "healthy":
                    print("⚠️ System not healthy, skipping this cycle")
                    await asyncio.sleep(interval)
                    continue
                
                print(f"📊 Analyzing {len(symbols)} symbols at {datetime.now().strftime('%H:%M:%S')}")
                
                for symbol in symbols:
                    try:
                        # Get market data
                        market_data = await self.get_market_data(symbol)
                        
                        # Analyze signal
                        signal = await self.analyze_signal(market_data)
                        
                        if signal:
                            print(f"📈 Signal generated for {symbol}: {signal['signal_type']} {signal['quantity']} @ ${signal['price']:.2f}")
                            
                            # Submit signal
                            success = await self.submit_signal(signal)
                            if success:
                                print(f"✅ Signal submitted for {symbol}")
                            else:
                                print(f"❌ Failed to submit signal for {symbol}")
                        else:
                            print(f"⏸️ No signal for {symbol}")
                    
                    except Exception as e:
                        print(f"❌ Error processing {symbol}: {e}")
                
                # Show current status
                positions = await self.get_positions()
                pnl = await self.get_daily_pnl()
                
                if positions.get("positions"):
                    print(f"📈 Current positions: {len(positions['positions'])}")
                
                if pnl.get("total_pnl") is not None:
                    print(f"💰 Daily P&L: ${pnl.get('total_pnl', 0):.2f}")
                
                print("-" * 50)
                
                # Wait for next cycle
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Strategy stopped by user")
                break
            except Exception as e:
                print(f"❌ Strategy error: {e}")
                await asyncio.sleep(interval)
    
    async def close(self):
        """Close the strategy."""
        await self.client.aclose()


async def main():
    """Main function."""
    print("🤖 AI Trading Agent Strategy Example")
    print("====================================")
    print("")
    
    # Create strategy instance
    strategy = ExampleStrategy()
    
    try:
        # Check if API is available
        status = await strategy.get_system_status()
        if not status:
            print("❌ API not available. Please start the AI Trading Agent API first.")
            print("   Run: make run-api")
            return
        
        print("✅ API is available")
        print("")
        
        # Define symbols to trade
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        
        # Run strategy
        await strategy.run_strategy(symbols, interval=30)  # Check every 30 seconds
        
    except KeyboardInterrupt:
        print("\n🛑 Strategy stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await strategy.close()


if __name__ == "__main__":
    asyncio.run(main())
