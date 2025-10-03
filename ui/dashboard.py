"""
Streamlit trading dashboard
"""

import streamlit as st
import asyncio
import httpx
import requests
import pandas as pd
from datetime import datetime, date
from typing import Dict, Any, List
import json

# Configure page
st.set_page_config(
    page_title="AI Trading Agent Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API configuration
API_BASE_URL = "http://localhost:8000"


@st.cache_data(ttl=5)
def fetch_data(endpoint: str) -> Dict[str, Any]:
    """
    Fetch data from API endpoint.
    
    Args:
        endpoint: API endpoint
        
    Returns:
        API response data
    """
    try:
        with httpx.Client() as client:
            response = client.get(f"{API_BASE_URL}{endpoint}")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch data from {endpoint}: {str(e)}")
        return {}


def main():
    """Main dashboard function."""
    st.title("🤖 AI Trading Agent Dashboard")
    st.markdown("Real-time monitoring and control of your AI trading system")
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Controls")
        
        # Trading status
        st.subheader("Trading Status")
        status_data = fetch_data("/v1/health/")
        if status_data.get("status") == "healthy":
            st.success("✅ System Healthy")
        else:
            st.error("❌ System Unhealthy")
        
        # Halt/Resume controls
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🛑 Halt Trading", type="primary"):
                # TODO: Implement halt trading
                st.warning("Halt trading not implemented yet")
        
        with col2:
            if st.button("▶️ Resume Trading"):
                # TODO: Implement resume trading
                st.info("Resume trading not implemented yet")
        
        # Configuration
        st.subheader("⚙️ Configuration")
        if st.button("📊 View Config"):
            config_data = fetch_data("/v1/config/")
            st.json(config_data)
    
    # Main content
    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "💰 P&L", 
        "📋 Orders", 
        "📈 Positions", 
        "📝 Events"
    ])
    
    with tab1:
        show_overview()
    
    with tab2:
        show_pnl()
    
    with tab3:
        show_orders()
    
    with tab4:
        show_positions()
    
    with tab5:
        show_events()


def show_overview():
    """Show overview tab."""
    st.header("📊 System Overview")
    
    # Get system status
    status_data = fetch_data("/v1/health/")
    
    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="System Status",
            value="Healthy" if status_data.get("status") == "healthy" else "Unhealthy",
            delta=None
        )
    
    with col2:
        st.metric(
            label="Uptime",
            value="99.9%",
            delta="+0.1%"
        )
    
    with col3:
        st.metric(
            label="Active Orders",
            value="0",
            delta="0"
        )
    
    with col4:
        st.metric(
            label="Total Positions",
            value="0",
            delta="0"
        )
    
    # Broker status
    st.subheader("🔌 Broker Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**Paper Broker** - Active")
        st.write("Mode: Simulation")
        st.write("Status: Connected")
    
    with col2:
        st.warning("**Live Brokers** - Inactive")
        st.write("Tradovate: Not configured")
        st.write("IBKR: Not configured")
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Refresh Data", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("📈 View P&L", use_container_width=True):
            st.switch_page("P&L")
    
    with col3:
        if st.button("⚙️ Settings", use_container_width=True):
            st.switch_page("Settings")
    
    # Recent trades section
    st.markdown("### Recent Trades")
    try:
        data = requests.get(f"{API_BASE_URL}/v1/logs/trades?limit=20", timeout=5).json()
        if isinstance(data, list) and data:
            df = pd.DataFrame(data)
            cols = ["created_at","symbol","side","qty","entry_price","exit_price","pnl_usd","r_multiple","outcome"]
            st.dataframe(df[[c for c in cols if c in df.columns]])
        else:
            st.write("No trades yet.")
    except Exception:
        st.write("Could not load trades.")


def show_pnl():
    """Show P&L tab."""
    st.header("💰 P&L Analysis")
    
    # Get daily P&L
    pnl_data = fetch_data("/v1/pnl/daily")
    
    if pnl_data:
        # P&L metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Today's P&L",
                value=f"${pnl_data.get('total_pnl', 0):.2f}",
                delta=f"${pnl_data.get('net_pnl', 0):.2f}"
            )
        
        with col2:
            st.metric(
                label="Realized P&L",
                value=f"${pnl_data.get('realized_pnl', 0):.2f}",
                delta=None
            )
        
        with col3:
            st.metric(
                label="Unrealized P&L",
                value=f"${pnl_data.get('unrealized_pnl', 0):.2f}",
                delta=None
            )
        
        with col4:
            st.metric(
                label="Commission",
                value=f"${pnl_data.get('commission', 0):.2f}",
                delta=None
            )
        
        # Trading statistics
        st.subheader("📈 Trading Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Total Trades",
                value=pnl_data.get('trades_count', 0),
                delta=None
            )
        
        with col2:
            st.metric(
                label="Win Rate",
                value=f"{pnl_data.get('win_rate', 0):.1%}",
                delta=None
            )
        
        with col3:
            st.metric(
                label="Avg Win",
                value=f"${pnl_data.get('avg_win', 0):.2f}",
                delta=None
            )
    else:
        st.warning("No P&L data available")
    
    # P&L chart placeholder
    st.subheader("📊 P&L Chart")
    st.info("P&L chart will be implemented with real data visualization")


def show_orders():
    """Show orders tab."""
    st.header("📋 Order Management")
    
    # Get orders
    orders_data = fetch_data("/v1/orders/")
    
    if orders_data:
        st.subheader("Recent Orders")
        
        # Display orders in a table
        if isinstance(orders_data, list) and orders_data:
            # Convert to DataFrame for better display
            import pandas as pd
            
            df = pd.DataFrame(orders_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No orders found")
    else:
        st.warning("Failed to load orders")
    
    # Order creation form
    st.subheader("📝 Create New Order")
    
    with st.form("order_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("Symbol", value="AAPL")
            quantity = st.number_input("Quantity", min_value=1, value=100)
            side = st.selectbox("Side", ["BUY", "SELL"])
        
        with col2:
            order_type = st.selectbox("Order Type", ["MARKET", "LIMIT"])
            price = st.number_input("Price", min_value=0.01, value=150.0, step=0.01)
            time_in_force = st.selectbox("Time in Force", ["DAY", "GTC"])
        
        submitted = st.form_submit_button("Submit Order")
        
        if submitted:
            # TODO: Implement order submission
            st.success("Order submitted successfully!")
            st.info("Order submission will be implemented with API integration")


def show_positions():
    """Show positions tab."""
    st.header("📈 Current Positions")
    
    # Get positions
    positions_data = fetch_data("/v1/pnl/positions")
    
    if positions_data and "positions" in positions_data:
        positions = positions_data["positions"]
        
        if positions:
            # Display positions
            import pandas as pd
            
            df = pd.DataFrame(positions)
            st.dataframe(df, use_container_width=True)
            
            # Position summary
            st.subheader("📊 Position Summary")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Total Positions",
                    value=len(positions),
                    delta=None
                )
            
            with col2:
                total_value = sum(pos.get("market_value", 0) for pos in positions)
                st.metric(
                    label="Total Value",
                    value=f"${total_value:.2f}",
                    delta=None
                )
            
            with col3:
                total_pnl = sum(pos.get("unrealized_pnl", 0) for pos in positions)
                st.metric(
                    label="Total Unrealized P&L",
                    value=f"${total_pnl:.2f}",
                    delta=None
                )
        else:
            st.info("No positions found")
    else:
        st.warning("Failed to load positions")


def show_events():
    """Show events tab."""
    st.header("📝 System Events")
    
    # Event log
    st.subheader("Recent Events")
    
    # Simulated events (in production, this would come from the API)
    events = [
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "type": "SYSTEM",
            "severity": "INFO",
            "message": "System started successfully",
            "source": "supervisor"
        },
        {
            "timestamp": "2024-01-01T10:01:00Z",
            "type": "ORDER",
            "severity": "LOW",
            "message": "Order submitted: AAPL BUY 100",
            "source": "order_api"
        },
        {
            "timestamp": "2024-01-01T10:02:00Z",
            "type": "TRADE",
            "severity": "LOW",
            "message": "Order executed: AAPL BUY 100 @ $150.00",
            "source": "supervisor"
        }
    ]
    
    # Display events
    for event in events:
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**{event['message']}**")
            
            with col2:
                severity_color = {
                    "INFO": "blue",
                    "LOW": "green", 
                    "MEDIUM": "orange",
                    "HIGH": "red",
                    "CRITICAL": "red"
                }.get(event['severity'], "gray")
                
                st.markdown(f":{severity_color}[{event['severity']}]")
            
            with col3:
                st.write(event['timestamp'])
            
            st.divider()
    
    # Event filters
    st.subheader("🔍 Event Filters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        event_type = st.selectbox("Event Type", ["All", "SYSTEM", "ORDER", "TRADE", "RISK", "ERROR"])
    
    with col2:
        severity = st.selectbox("Severity", ["All", "INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
    
    with col3:
        source = st.selectbox("Source", ["All", "supervisor", "order_api", "risk_guard"])


if __name__ == "__main__":
    main()
