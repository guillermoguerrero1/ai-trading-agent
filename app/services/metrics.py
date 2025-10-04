"""
Prometheus metrics service for AI Trading Agent
"""

import time
from typing import Dict, Any
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
import structlog

logger = structlog.get_logger(__name__)

class MetricsService:
    """Service for tracking Prometheus metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        
        # Trading metrics
        self.orders_ok = Counter(
            'trading_orders_ok_total',
            'Total number of successful orders',
            ['symbol', 'side']
        )
        
        self.orders_blocked = Counter(
            'trading_orders_blocked_total',
            'Total number of blocked orders',
            ['symbol', 'side', 'reason']
        )
        
        self.halts = Counter(
            'trading_halts_total',
            'Total number of trading halts',
            ['reason']
        )
        
        self.model_blocks = Counter(
            'trading_model_blocks_total',
            'Total number of model blocks',
            ['model_version', 'reason']
        )
        
        # System metrics
        self.process_uptime = Gauge(
            'trading_process_uptime_seconds',
            'Process uptime in seconds'
        )
        
        self.process_version = Gauge(
            'trading_process_version_info',
            'Process version information',
            ['version', 'environment']
        )
        
        # Initialize version info
        self.process_version.labels(
            version='0.1.0',
            environment='development'
        ).set(1)
        
        logger.info("Metrics service initialized")
    
    def record_order_ok(self, symbol: str, side: str) -> None:
        """Record a successful order."""
        self.orders_ok.labels(symbol=symbol, side=side).inc()
        logger.debug("Order OK recorded", symbol=symbol, side=side)
    
    def record_order_blocked(self, symbol: str, side: str, reason: str) -> None:
        """Record a blocked order."""
        self.orders_blocked.labels(symbol=symbol, side=side, reason=reason).inc()
        logger.debug("Order blocked recorded", symbol=symbol, side=side, reason=reason)
    
    def record_halt(self, reason: str) -> None:
        """Record a trading halt."""
        self.halts.labels(reason=reason).inc()
        logger.info("Trading halt recorded", reason=reason)
    
    def record_model_block(self, model_version: str, reason: str) -> None:
        """Record a model block."""
        self.model_blocks.labels(model_version=model_version, reason=reason).inc()
        logger.debug("Model block recorded", model_version=model_version, reason=reason)
    
    def update_uptime(self) -> None:
        """Update process uptime metric."""
        uptime = time.time() - self.start_time
        self.process_uptime.set(uptime)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        self.update_uptime()
        return generate_latest()
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as a dictionary for debugging."""
        return {
            'start_time': self.start_time,
            'uptime_seconds': time.time() - self.start_time,
            'counters': {
                'orders_ok': dict(self.orders_ok._metrics),
                'orders_blocked': dict(self.orders_blocked._metrics),
                'halts': dict(self.halts._metrics),
                'model_blocks': dict(self.model_blocks._metrics),
            }
        }

# Global metrics service instance
_metrics_service = None

def get_metrics_service() -> MetricsService:
    """Get the global metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
