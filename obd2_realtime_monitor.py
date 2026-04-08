#!/usr/bin/env python3
"""
OBD2 Real-Time Monitor for WRXDash
Monitors critical engine parameters for knock detection, overheating, and fuel conditions
"""

import obd
import time
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
import threading
import queue
import statistics

class OBD2RealtimeMonitor:
    def __init__(self, connection_string: str = "/dev/ttyUSB0", log_level: str = "INFO"):
        """Initialize the OBD2 real-time monitor"""
        self.connection_string = connection_string
        self.connection = None
        self.running = False
        self.log_level = log_level
        
        # Critical thresholds for WRX engine
        self.thresholds = {
            'knock_retard': 5.0,  # degrees of knock retard
            'coolant_temp': 105,  # Celsius - overheating threshold
            'intake_temp': 60,    # Celsius - intake air temp warning
            'fuel_trim_long': 8.0, # % - lean condition
            'fuel_trim_short': 8.0, # % - immediate fuel correction
            'fuel_pressure': 50,   # PSI - minimum fuel pressure
            'boost_pressure': 18,  # PSI - stock turbo max
            'rpm_limit': 6500      # RPM - redline
        }
        
        # Data buffers for trend analysis
        self.data_buffer = {
            'knock_retard': [],
            'coolant_temp': [],
            'fuel_trim_long': [],
            'boost_pressure': []
        }
        
        self.buffer_size = 10  # Keep last 10 readings
        
        # Alert system
        self.alerts_queue = queue.Queue()
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler('/opt/wrxdash/logs/realtime_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """Establish OBD2 connection"""
        try:
            self.logger.info(f"Connecting to OBD2 device: {self.connection_string}")
            self.connection = obd.OBD(self.connection_string)
            
            if self.connection.is_connected():
                self.logger.info("OBD2 connection established successfully")
                return True
            else:
                self.logger.error("Failed to establish OBD2 connection")
                return False
                
        except Exception as e:
            self.logger.error(f"OBD2 connection error: {e}")
            return False
            
    def get_critical_parameters(self) -> Dict:
        """Fetch critical engine parameters"""
        if not self.connection or not self.connection.is_connected():
            return {}
            
        try:
            # Critical PIDs for WRX monitoring
            critical_pids = {
                'coolant_temp': obd.commands.COOLANT_TEMP,
                'intake_temp': obd.commands.INTAKE_TEMP,
                'rpm': obd.commands.RPM,
                'speed': obd.commands.SPEED,
                'fuel_pressure': obd.commands.FUEL_PRESSURE,
                'boost_pressure': obd.commands.BOOST_PRESSURE,
                'knock_retard': obd.commands.KNOCK_RETARD,
                'fuel_trim_long': obd.commands.LONG_FUEL_TRIM,
                'fuel_trim_short': obd.commands.SHORT_FUEL_TRIM,
                'maf_rate': obd.commands.MAF,
                'throttle_pos': obd.commands.THROTTLE_POS,
                'timing_advance': obd.commands.TIMING_ADVANCE
            }
            
            data = {}
            for param_name, pid in critical_pids.items():
                response = self.connection.query(pid)
                if response.value is not None:
                    data[param_name] = {
                        'value': float(response.value.magnitude),
                        'unit': str(response.value.units),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    data[param_name] = {
                        'value': None,
                        'unit': 'N/A',
                        'timestamp': datetime.now().isoformat()
                    }
                    
            return data
            
        except Exception as e:
            self.logger.error(f"Error reading parameters: {e}")
            return {}
            
    def check_thresholds(self, data: Dict) -> List[str]:
        """Check if any parameters exceed critical thresholds"""
        alerts = []
        
        # Check knock retard (most critical for turbo engines)
        if data.get('knock_retard', {}).get('value'):
            knock_value = data['knock_retard']['value']
            if knock_value > self.thresholds['knock_retard']:
                alerts.append(f"🚨 KNOCK DETECTED: {knock_value:.1f}° retard (>{self.thresholds['knock_retard']}°)")
                
        # Check coolant temperature (overheating protection)
        if data.get('coolant_temp', {}).get('value'):
            coolant_value = data['coolant_temp']['value']
            if coolant_value > self.thresholds['coolant_temp']:
                alerts.append(f"🌡️ OVERHEATING: {coolant_value:.1f}°C coolant temp (>{self.thresholds['coolant_temp']}°C)")
                
        # Check intake temperature (heat soak indicator)
        if data.get('intake_temp', {}).get('value'):
            intake_value = data['intake_temp']['value']
            if intake_value > self.thresholds['intake_temp']:
                alerts.append(f"🔥 HEAT SOAK: {intake_value:.1f}°C intake temp (>{self.thresholds['intake_temp']}°C)")
                
        # Check fuel trim (lean condition)
        if data.get('fuel_trim_long', {}).get('value'):
            fuel_trim = data['fuel_trim_long']['value']
            if abs(fuel_trim) > self.thresholds['fuel_trim_long']:
                condition = "LEAN" if fuel_trim > 0 else "RICH"
                alerts.append(f"⛽ FUEL TRIM: {condition} {fuel_trim:.1f}% (>{self.thresholds['fuel_trim_long']}%)")
                
        # Check boost pressure (turbo safety)
        if data.get('boost_pressure', {}).get('value'):
            boost_value = data['boost_pressure']['value']
            if boost_value > self.thresholds['boost_pressure']:
                alerts.append(f"🏁 HIGH BOOST: {boost_value:.1f} PSI (>{self.thresholds['boost_pressure']} PSI)")
                
        return alerts
        
    def update_buffers(self, data: Dict):
        """Update data buffers for trend analysis"""
        for param in ['knock_retard', 'coolant_temp', 'fuel_trim_long', 'boost_pressure']:
            if data.get(param, {}).get('value') is not None:
                value = data[param]['value']
                self.data_buffer[param].append(value)
                
                # Keep buffer size limited
                if len(self.data_buffer[param]) > self.buffer_size:
                    self.data_buffer[param].pop(0)
                    
    def analyze_trends(self) -> Dict:
        """Analyze trends in buffered data"""
        trends = {}
        
        for param, values in self.data_buffer.items():
            if len(values) >= 3:  # Need at least 3 points for trend
                if len(values) >= 2:
                    recent_avg = statistics.mean(values[-3:])  # Last 3 readings
                    older_avg = statistics.mean(values[:-3])   # Previous readings
                    
                    if recent_avg > older_avg:
                        trend = "INCREASING"
                    elif recent_avg < older_avg:
                        trend = "DECREASING"
                    else:
                        trend = "STABLE"
                        
                    trends[param] = {
                        'trend': trend,
                        'recent_avg': round(recent_avg, 2),
                        'change': round(recent_avg - older_avg, 2)
                    }
                    
        return trends
        
    def log_data(self, data: Dict):
        """Log data to files for analysis"""
        try:
            # Real-time log file
            with open('/opt/wrxdash/logs/realtime_data.jsonl', 'a') as f:
                json.dump(data, f)
                f.write('\n')
                
            # Critical events log
            alerts = self.check_thresholds(data)
            if alerts:
                for alert in alerts:
                    self.logger.warning(alert)
                    
                # Log critical event
                critical_event = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'CRITICAL_ALERT',
                    'data': data,
                    'alerts': alerts
                }
                with open('/opt/wrxdash/logs/critical_events.jsonl', 'a') as f:
                    json.dump(critical_event, f)
                    f.write('\n')
                    
        except Exception as e:
            self.logger.error(f"Error logging data: {e}")
            
    def start_monitoring(self, interval: float = 1.0):
        """Start real-time monitoring loop"""
        if not self.connect():
            return False
            
        self.running = True
        self.logger.info("Starting real-time monitoring...")
        
        try:
            while self.running:
                # Get current data
                data = self.get_critical_parameters()
                
                if data:
                    # Add timestamp
                    data['monitor_timestamp'] = datetime.now().isoformat()
                    
                    # Update buffers and check for trends
                    self.update_buffers(data)
                    trends = self.analyze_trends()
                    
                    # Add trend information
                    data['trends'] = trends
                    
                    # Log data
                    self.log_data(data)
                    
                    # Check for alerts
                    alerts = self.check_thresholds(data)
                    if alerts:
                        print("\n" + "="*50)
                        for alert in alerts:
                            print(alert)
                        print("="*50)
                        
                    # Print current status
                    self.print_status(data, trends)
                    
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
        finally:
            self.stop_monitoring()
            
    def stop_monitoring(self):
        """Stop monitoring and cleanup"""
        self.running = False
        if self.connection:
            self.connection.close()
        self.logger.info("Monitoring stopped")
        
    def print_status(self, data: Dict, trends: Dict):
        """Print current status to console"""
        print(f"\r{datetime.now().strftime('%H:%M:%S')}", end="")
        
        # Key parameters
        key_params = ['rpm', 'boost_pressure', 'coolant_temp', 'knock_retard']
        for param in key_params:
            if data.get(param, {}).get('value') is not None:
                value = data[param]['value']
                unit = data[param]['unit']
                print(f" {param}: {value:.1f}{unit}", end="")
                
        # Trend indicators
        if trends:
            for param, trend_info in trends.items():
                if trend_info['trend'] in ['INCREASING', 'DECREASING']:
                    arrow = "↑" if trend_info['trend'] == 'INCREASING' else "↓"
                    print(f" {param}{arrow}", end="")
                    
        print("   ", end="", flush=True)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='OBD2 Real-Time Monitor for WRXDash')
    parser.add_argument('--device', default='/dev/ttyUSB0', help='OBD2 device path')
    parser.add_argument('--interval', type=float, default=1.0, help='Update interval in seconds')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    monitor = OBD2RealtimeMonitor(
        connection_string=args.device,
        log_level=args.log_level
    )
    
    try:
        monitor.start_monitoring(interval=args.interval)
    except KeyboardInterrupt:
        print("\nShutting down...")
        monitor.stop_monitoring()
