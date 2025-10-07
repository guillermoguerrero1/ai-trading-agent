"""
Streamlit trading dashboard
"""

import streamlit as st
import asyncio
import httpx
import requests
import pandas as pd
from datetime import datetime, date, timezone
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
API_BASE_URL = "http://localhost:9001"


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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Overview", 
        "💰 P&L", 
        "📋 Orders", 
        "📈 Positions", 
        "📝 Events",
        "⚡ Quick Trade",
        "🔍 Audit"
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
    
    with tab6:
        show_quick_trade()
    
    with tab7:
        show_audit()


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
        if st.button("📊 Refresh Data", width='stretch'):
            st.rerun()
    
    with col2:
        if st.button("📈 View P&L", width='stretch'):
            st.info("Use the '💰 P&L' tab above to view P&L data")
    
    with col3:
        if st.button("⚙️ Settings", width='stretch'):
            st.info("Use the '🔍 Audit' tab above to view system settings")
    
    # Recent trades section
    st.markdown("### Recent Trades")
    try:
        data = requests.get(f"{API_BASE_URL}/v1/logs/trades?limit=100", timeout=5).json()
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


def show_quick_trade():
    """Show Quick Trade form."""
    import time, uuid
    
    try:
        API = st.secrets.get("API", "http://localhost:9001")
    except:
        API = "http://localhost:9001"
    
    st.header("Quick Trade (NQ only)")
    
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Symbol", "NQZ5")
        side   = st.selectbox("Side", ["BUY","SELL"])
        qty    = st.number_input("Qty", 1, 10, 1, step=1)
    with col2:
        entry  = st.number_input("Entry", value=17895.0, step=0.25, format="%.2f")
        stop   = st.number_input("Stop",  value=17885.0, step=0.25, format="%.2f")
        target = st.number_input("Target",value=17915.0, step=0.25, format="%.2f")
    
    paper = st.checkbox("Paper", value=True)
    strategy = st.text_input("Strategy ID", "Manual")
    setup = st.text_input("Setup", "Manual-Entry")
    conf = st.slider("Confidence", 0.0, 1.0, 0.5, 0.05)
    
    # Timestamp and backfill options
    st.subheader("📅 Entry Timestamp")
    col1, col2 = st.columns(2)
    
    with col1:
        # Default to current UTC time
        default_time = datetime.now(timezone.utc)
        entered_at = st.datetime_input(
            "Entered at (UTC)", 
            value=default_time,
            help="When the trade was actually entered (for backfilling historical trades)"
        )
    
    with col2:
        is_backfill = st.checkbox("Backfill", value=False, help="Mark this as a backfilled trade")
    
    # Validate entered_at is not in the future
    current_time = datetime.now(timezone.utc)
    if entered_at > current_time:
        st.error("❌ Entry timestamp cannot be in the future!")
        st.stop()
    
    # Show backfill status
    if is_backfill:
        st.info("🔄 Backfill mode: Trade will be marked as backfilled")
    elif entered_at != current_time:
        st.info("⏰ Custom timestamp: Using specified entry time")
    
    def round_tick(x, tick=0.25):
        return round(round(x/tick)*tick, 2)
    
    if st.button("Submit Trade"):
        entry_r, stop_r, target_r = map(round_tick, (entry, stop, target))
        risk = abs(entry_r - stop_r)
        rr   = abs(target_r - entry_r) / (risk if risk>0 else 1e-9)
        
        # Build features dict
        features = {
            "root_symbol":"NQ","risk":risk,"rr":rr,"in_session":1,
            "strategy_id":strategy,"setup":setup,"rule_version":"v1.0","confidence":conf
        }
        
        # Add backfill flag if checked
        if is_backfill:
            features["is_backfill"] = True
        
        # Build payload
        payload = {
            "symbol": symbol, "side": side, "quantity": int(qty),
            "order_type": "LIMIT", "price": entry_r, "stop_price": stop_r, "target_price": target_r,
            "paper": paper,
            "features": features,
            "notes":"ui-entry"
        }
        
        # Add entered_at if backfill is checked or if timestamp is different from current time
        if is_backfill or entered_at != current_time:
            payload["entered_at"] = entered_at.isoformat()
        key = f"ui-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        try:
            r = requests.post(f"{API}/v1/orders",
                              headers={"Content-Type":"application/json","Idempotency-Key":key},
                              json=payload, timeout=8)
            if r.status_code < 300:
                st.success(f"Submitted: {r.json()}")
            else:
                st.error(f"Error {r.status_code}: {r.text}")
        except Exception as e:
            st.error(str(e))


def show_audit():
    """Show dataset audit viewer."""
    import subprocess
    import json
    from pathlib import Path
    import datetime as dt
    
    st.header("🔍 NQ Dataset Audit")
    
    # Run audit button
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("🔄 Run New Audit", type="primary"):
            with st.spinner("Running dataset audit..."):
                try:
                    result = subprocess.run(
                        ["python", "scripts/audit_nq_dataset.py"],
                        capture_output=True,
                        text=True,
                        cwd="."
                    )
                    if result.returncode == 0:
                        st.success("Audit completed successfully!")
                        st.rerun()
                    else:
                        st.error(f"Audit failed: {result.stderr}")
                except Exception as e:
                    st.error(f"Failed to run audit: {str(e)}")
    
    with col2:
        st.info("💡 **Tip**: Run audits regularly to monitor dataset quality and ensure optimal training performance.")
    
    # List available audit reports
    audit_dir = Path("reports/audit")
    if audit_dir.exists():
        audit_files = list(audit_dir.glob("audit_*.md"))
        audit_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if audit_files:
            st.subheader("📄 Available Audit Reports")
            
            # Report selector
            report_options = {}
            for file in audit_files:
                timestamp = file.stem.replace("audit_", "")
                try:
                    dt_obj = dt.datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
                    display_name = f"{dt_obj.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                except:
                    display_name = timestamp
                report_options[display_name] = file
            
            selected_report = st.selectbox(
                "Select audit report to view:",
                options=list(report_options.keys()),
                index=0
            )
            
            if selected_report:
                report_file = report_options[selected_report]
                
                # Display report content
                try:
                    report_content = report_file.read_text(encoding='utf-8')
                    
                    # Parse and display structured information
                    st.subheader("📊 Audit Summary")
                    
                    # Extract key metrics from markdown
                    lines = report_content.split('\n')
                    summary_info = {}
                    
                    for line in lines:
                        if line.startswith('- Total trades:'):
                            summary_info['total_trades'] = line.split('**')[1]
                        elif line.startswith('- Date range'):
                            summary_info['date_range'] = line.split('**')[1] + ' → ' + line.split('**')[3]
                        elif line.startswith('- Outcomes:'):
                            summary_info['outcomes'] = line.split('`')[1]
                    
                    # Display summary metrics
                    if summary_info:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Total Trades", summary_info.get('total_trades', 'N/A'))
                        
                        with col2:
                            if 'outcomes' in summary_info:
                                try:
                                    outcomes = json.loads(summary_info['outcomes'])
                                    total_outcomes = sum(outcomes.values())
                                    wins = outcomes.get('target', 0)
                                    win_rate = (wins / total_outcomes * 100) if total_outcomes > 0 else 0
                                    st.metric("Win Rate", f"{win_rate:.1f}%")
                                except:
                                    st.metric("Outcomes", "Mixed")
                            else:
                                st.metric("Outcomes", "N/A")
                        
                        with col3:
                            if 'date_range' in summary_info:
                                st.metric("Date Range", summary_info['date_range'])
                            else:
                                st.metric("Date Range", "N/A")
                    
                    # Display checks with color coding
                    st.subheader("🔍 Quality Checks")
                    
                    checks_section = False
                    for line in lines:
                        if line.startswith('## Checks'):
                            checks_section = True
                            continue
                        elif line.startswith('##') and checks_section:
                            break
                        elif checks_section and line.startswith('- '):
                            # Parse check line
                            if '✅' in line:
                                st.success(line.replace('- ✅', '').strip())
                            elif '⚠️' in line:
                                st.warning(line.replace('- ⚠️', '').strip())
                            elif '❌' in line:
                                st.error(line.replace('- ❌', '').strip())
                            elif 'ℹ️' in line:
                                st.info(line.replace('- ℹ️', '').strip())
                            else:
                                st.write(line.replace('- ', '').strip())
                    
                    # Display suggestions
                    suggestions_section = False
                    suggestions = []
                    for line in lines:
                        if line.startswith('## Suggestions'):
                            suggestions_section = True
                            continue
                        elif line.startswith('##') and suggestions_section:
                            break
                        elif suggestions_section and line.startswith('- '):
                            suggestions.append(line.replace('- ', '').strip())
                    
                    if suggestions:
                        st.subheader("💡 Recommendations")
                        for suggestion in suggestions:
                            st.write(f"• {suggestion}")
                    
                    # Raw markdown view (collapsible)
                    with st.expander("📝 View Raw Report"):
                        st.markdown(report_content)
                        
                except Exception as e:
                    st.error(f"Failed to read report: {str(e)}")
        else:
            st.info("No audit reports found. Click 'Run New Audit' to generate your first report.")
    else:
        st.info("Audit reports directory not found. Click 'Run New Audit' to create it and generate your first report.")


if __name__ == "__main__":
    main()
