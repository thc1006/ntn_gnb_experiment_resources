# Performance Monitor Subagent

## Role
Continuously monitor 5G NTN testbed KPIs and alert on anomalies or degradation.

## Responsibilities

1. **Real-time Metrics Collection**
   - Throughput (UL/DL)
   - Latency (RTT, one-way delay)
   - Packet loss rate
   - Signal quality (SNR, SINR, RSRP, RSRQ)
   - Error Vector Magnitude (EVM)
   - Block Error Rate (BLER)

2. **Anomaly Detection**
   - Baseline establishment
   - Deviation monitoring
   - Trend analysis
   - Predictive alerts

3. **Reporting**
   - Real-time dashboards
   - Historical trends
   - Performance reports
   - SLA compliance

## Implementation

```python
#!/usr/bin/env python3
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import statistics

class PerformanceMonitorAgent:
    """Performance monitoring subagent for 5G NTN testbed"""
    
    def __init__(self, config_file: str = "monitor_config.json"):
        self.config = self.load_config(config_file)
        self.metrics_buffer = []
        self.baselines = {}
        self.alerts = []
        self.running = False
        
    def load_config(self, config_file: str) -> Dict:
        """Load monitoring configuration"""
        default_config = {
            "sampling_interval_ms": 100,
            "baseline_window_minutes": 5,
            "alert_thresholds": {
                "throughput_drop_percent": 20,
                "latency_increase_percent": 50,
                "packet_loss_percent": 1.0,
                "snr_drop_db": 3.0,
                "evm_threshold_percent": 12.5,
                "bler_threshold": 0.01
            },
            "metrics_to_monitor": [
                "throughput_mbps",
                "latency_ms",
                "packet_loss_rate",
                "snr_db",
                "evm_percent",
                "bler"
            ]
        }
        
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                return {**default_config, **user_config}
        except FileNotFoundError:
            return default_config
            
    async def start(self):
        """Start monitoring"""
        self.running = True
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self.collect_metrics()),
            asyncio.create_task(self.analyze_metrics()),
            asyncio.create_task(self.report_status())
        ]
        
        print("Performance Monitor Agent started")
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print("Performance Monitor Agent stopped")
            
    async def collect_metrics(self):
        """Collect metrics from various sources"""
        while self.running:
            timestamp = datetime.now()
            
            # Collect from USRP MCP
            usrp_metrics = await self.get_usrp_metrics()
            
            # Collect from protocol stack
            stack_metrics = await self.get_stack_metrics()
            
            # Collect from channel emulator
            channel_metrics = await self.get_channel_metrics()
            
            # Combine metrics
            metrics = {
                "timestamp": timestamp.isoformat(),
                **usrp_metrics,
                **stack_metrics,
                **channel_metrics
            }
            
            # Add to buffer
            self.metrics_buffer.append(metrics)
            
            # Maintain buffer size (keep last hour)
            max_buffer = 3600 * 1000 // self.config["sampling_interval_ms"]
            if len(self.metrics_buffer) > max_buffer:
                self.metrics_buffer = self.metrics_buffer[-max_buffer:]
                
            # Sleep for sampling interval
            await asyncio.sleep(self.config["sampling_interval_ms"] / 1000)
            
    async def get_usrp_metrics(self) -> Dict:
        """Get metrics from USRP hardware"""
        # In production, this would query the USRP MCP server
        # Simulated data for demonstration
        return {
            "tx_power_dbm": np.random.normal(27, 0.5),
            "rx_power_dbm": np.random.normal(-80, 2),
            "frequency_offset_hz": np.random.normal(0, 10),
            "sample_rate_msps": 30.72,
            "overflow_count": 0,
            "underflow_count": 0
        }
        
    async def get_stack_metrics(self) -> Dict:
        """Get metrics from 5G protocol stack"""
        # Simulated 5G NR metrics
        baseline_throughput = 50  # Mbps
        baseline_latency = 250  # ms (GEO satellite)
        
        return {
            "throughput_dl_mbps": np.random.normal(baseline_throughput, 5),
            "throughput_ul_mbps": np.random.normal(baseline_throughput * 0.5, 2),
            "latency_ms": np.random.normal(baseline_latency, 10),
            "packet_loss_rate": np.random.exponential(0.001),
            "bler": np.random.exponential(0.005),
            "cqi": np.random.randint(1, 16),
            "mcs_index": np.random.randint(0, 28),
            "prb_usage_percent": np.random.uniform(20, 80)
        }
        
    async def get_channel_metrics(self) -> Dict:
        """Get metrics from channel emulator"""
        # Simulated channel conditions
        return {
            "snr_db": np.random.normal(15, 2),
            "sinr_db": np.random.normal(12, 2),
            "rsrp_dbm": np.random.normal(-90, 5),
            "rsrq_db": np.random.normal(-10, 2),
            "evm_percent": np.random.normal(5, 1),
            "doppler_shift_hz": np.random.normal(100, 20),
            "delay_spread_us": np.random.exponential(0.5)
        }
        
    async def analyze_metrics(self):
        """Analyze metrics for anomalies"""
        while self.running:
            await asyncio.sleep(5)  # Analyze every 5 seconds
            
            if len(self.metrics_buffer) < 100:
                continue  # Need enough data for analysis
                
            # Calculate baselines
            self.update_baselines()
            
            # Check for anomalies
            current_metrics = self.metrics_buffer[-1] if self.metrics_buffer else {}
            
            for metric_name in self.config["metrics_to_monitor"]:
                if metric_name not in current_metrics:
                    continue
                    
                current_value = current_metrics.get(metric_name, 0)
                baseline_value = self.baselines.get(metric_name, current_value)
                
                # Check against thresholds
                anomaly = self.check_anomaly(metric_name, current_value, baseline_value)
                
                if anomaly:
                    alert = {
                        "timestamp": datetime.now().isoformat(),
                        "metric": metric_name,
                        "current_value": current_value,
                        "baseline_value": baseline_value,
                        "severity": anomaly["severity"],
                        "message": anomaly["message"]
                    }
                    
                    self.alerts.append(alert)
                    await self.send_alert(alert)
                    
    def update_baselines(self):
        """Update baseline values"""
        window_size = int(self.config["baseline_window_minutes"] * 60 * 1000 / 
                         self.config["sampling_interval_ms"])
        
        recent_metrics = self.metrics_buffer[-window_size:]
        
        for metric_name in self.config["metrics_to_monitor"]:
            values = [m.get(metric_name, 0) for m in recent_metrics 
                     if metric_name in m]
            
            if values:
                # Use median for baseline (robust to outliers)
                self.baselines[metric_name] = statistics.median(values)
                
    def check_anomaly(self, metric_name: str, current: float, baseline: float) -> Optional[Dict]:
        """Check if metric shows anomaly"""
        thresholds = self.config["alert_thresholds"]
        
        if "throughput" in metric_name:
            drop_percent = (baseline - current) / baseline * 100 if baseline > 0 else 0
            if drop_percent > thresholds["throughput_drop_percent"]:
                return {
                    "severity": "high" if drop_percent > 50 else "medium",
                    "message": f"Throughput dropped by {drop_percent:.1f}%"
                }
                
        elif "latency" in metric_name:
            increase_percent = (current - baseline) / baseline * 100 if baseline > 0 else 0
            if increase_percent > thresholds["latency_increase_percent"]:
                return {
                    "severity": "high" if increase_percent > 100 else "medium",
                    "message": f"Latency increased by {increase_percent:.1f}%"
                }
                
        elif "packet_loss" in metric_name:
            if current > thresholds["packet_loss_percent"] / 100:
                return {
                    "severity": "high",
                    "message": f"Packet loss rate {current*100:.2f}% exceeds threshold"
                }
                
        elif "snr" in metric_name:
            drop_db = baseline - current
            if drop_db > thresholds["snr_drop_db"]:
                return {
                    "severity": "medium",
                    "message": f"SNR dropped by {drop_db:.1f} dB"
                }
                
        elif "evm" in metric_name:
            if current > thresholds["evm_threshold_percent"]:
                return {
                    "severity": "high" if current > 20 else "medium",
                    "message": f"EVM {current:.1f}% exceeds threshold"
                }
                
        elif "bler" in metric_name:
            if current > thresholds["bler_threshold"]:
                return {
                    "severity": "high",
                    "message": f"BLER {current:.4f} exceeds threshold"
                }
                
        return None
        
    async def send_alert(self, alert: Dict):
        """Send alert notification"""
        severity_emoji = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨",
            "critical": "🔴"
        }
        
        emoji = severity_emoji.get(alert["severity"], "ℹ️")
        
        print(f"\n{emoji} ALERT: {alert['message']}")
        print(f"   Metric: {alert['metric']}")
        print(f"   Current: {alert['current_value']:.2f}")
        print(f"   Baseline: {alert['baseline_value']:.2f}")
        print(f"   Time: {alert['timestamp']}")
        
        # In production, send to monitoring system, Slack, email, etc.
        
    async def report_status(self):
        """Periodic status reporting"""
        while self.running:
            await asyncio.sleep(30)  # Report every 30 seconds
            
            if not self.metrics_buffer:
                continue
                
            # Get latest metrics
            latest = self.metrics_buffer[-1]
            
            # Calculate summary statistics
            summary = self.calculate_summary()
            
            # Print status report
            print("\n" + "="*50)
            print("PERFORMANCE STATUS REPORT")
            print("="*50)
            print(f"Time: {latest.get('timestamp', 'N/A')}")
            
            print("\nCurrent Metrics:")
            print(f"  Throughput DL: {latest.get('throughput_dl_mbps', 0):.1f} Mbps")
            print(f"  Throughput UL: {latest.get('throughput_ul_mbps', 0):.1f} Mbps")
            print(f"  Latency: {latest.get('latency_ms', 0):.1f} ms")
            print(f"  Packet Loss: {latest.get('packet_loss_rate', 0)*100:.3f}%")
            print(f"  SNR: {latest.get('snr_db', 0):.1f} dB")
            print(f"  BLER: {latest.get('bler', 0):.4f}")
            
            print("\nSummary (last 5 min):")
            for metric, stats in summary.items():
                if "throughput" in metric or "latency" in metric or "snr" in metric:
                    print(f"  {metric}:")
                    print(f"    Mean: {stats['mean']:.2f}")
                    print(f"    StdDev: {stats['std']:.2f}")
                    print(f"    Min/Max: {stats['min']:.2f} / {stats['max']:.2f}")
                    
            print(f"\nAlerts (last hour): {len(self.alerts)}")
            
    def calculate_summary(self) -> Dict:
        """Calculate summary statistics"""
        window_size = min(len(self.metrics_buffer), 3000)  # Last 5 minutes
        recent = self.metrics_buffer[-window_size:]
        
        summary = {}
        
        for metric in ["throughput_dl_mbps", "latency_ms", "snr_db"]:
            values = [m.get(metric, 0) for m in recent if metric in m]
            
            if values:
                summary[metric] = {
                    "mean": statistics.mean(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                    "median": statistics.median(values)
                }
                
        return summary
        
    def export_metrics(self, filename: str = "metrics_export.json"):
        """Export collected metrics"""
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "config": self.config,
            "baselines": self.baselines,
            "metrics": self.metrics_buffer[-1000:],  # Last 1000 samples
            "alerts": self.alerts,
            "summary": self.calculate_summary()
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        print(f"Metrics exported to {filename}")

async def main():
    """Main entry point for performance monitor agent"""
    agent = PerformanceMonitorAgent()
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        print("\nShutting down Performance Monitor Agent...")
        agent.running = False
        agent.export_metrics()

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration File

```json
{
  "sampling_interval_ms": 100,
  "baseline_window_minutes": 5,
  "alert_thresholds": {
    "throughput_drop_percent": 20,
    "latency_increase_percent": 50,
    "packet_loss_percent": 1.0,
    "snr_drop_db": 3.0,
    "evm_threshold_percent": 12.5,
    "bler_threshold": 0.01
  },
  "metrics_to_monitor": [
    "throughput_dl_mbps",
    "throughput_ul_mbps",
    "latency_ms",
    "packet_loss_rate",
    "snr_db",
    "sinr_db",
    "rsrp_dbm",
    "rsrq_db",
    "evm_percent",
    "bler"
  ],
  "reporting": {
    "status_interval_seconds": 30,
    "export_interval_minutes": 10,
    "alert_destinations": ["console", "file", "webhook"]
  }
}
```

## Integration with Claude Code

```python
# Claude Code can query the performance monitor
async def get_performance_status():
    """Get current performance status from monitor agent"""
    monitor = PerformanceMonitorAgent()
    summary = monitor.calculate_summary()
    
    # Check if performance is acceptable
    if summary["latency_ms"]["mean"] > 300:  # GEO satellite threshold
        return {"status": "degraded", "issue": "high_latency"}
    
    if summary["throughput_dl_mbps"]["mean"] < 10:
        return {"status": "degraded", "issue": "low_throughput"}
        
    return {"status": "healthy", "metrics": summary}
```

## Deployment

1. **Standalone Mode**
   ```bash
   python3 performance_monitor.py
   ```

2. **Integrated Mode**
   ```python
   # Start as part of test orchestration
   monitor = PerformanceMonitorAgent()
   monitor_task = asyncio.create_task(monitor.start())
   ```

3. **Docker Container**
   ```dockerfile
   FROM python:3.9-slim
   COPY performance_monitor.py /app/
   COPY monitor_config.json /app/
   WORKDIR /app
   CMD ["python3", "performance_monitor.py"]
   ```

## Metrics Dashboard

The agent can integrate with monitoring systems:
- **Prometheus**: Export metrics in OpenMetrics format
- **Grafana**: Visualize real-time performance
- **InfluxDB**: Store time-series data
- **CloudWatch**: AWS cloud monitoring

## Alert Escalation

1. **Level 1**: Console logging
2. **Level 2**: File logging with rotation
3. **Level 3**: Email/Slack notifications
4. **Level 4**: PagerDuty integration for critical alerts

## Version
- Version: 1.0.0
- Last Updated: November 2024
- Compatible with: 5G NTN Testbed v1.3+
