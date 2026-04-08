#!/usr/bin/env python3
"""
Diagnostics Logger for WRXDash
Comprehensive logging system for ECU flash tune auditing
Logs all critical data for post-analysis and compliance
"""

import obd
import json
import csv
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sqlite3
import os
from pathlib import Path

class DiagnosticsLogger:
    def __init__(self, database_path: str = "/opt/wrxdash/data/wrxdash.db"):
        """Initialize the diagnostics logger"""
        self.database_path = database_path
        self.connection = None
        self.running = False
        self.logger_thread = None
        
        # Data collection intervals (seconds)
        self.intervals = {
            'fast': 0.5,      # Knock detection, boost pressure
            'normal': 2.0,    # Standard parameters
            'slow': 10.0      # Fuel trims, long-term data
        }
        
        # Initialize database
        self._init_database()
        
        # Setup logging
        self._setup_logging()
        
        # Data buffers
        self.last_collection = {
            'fast': 0,
            'normal': 0,
            'slow': 0
        }
        
    def _init_database(self):
        """Initialize SQLite database for long-term storage"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Create main data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS diagnostics_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    rpm REAL,
                    speed REAL,
                    coolant_temp REAL,
                    intake_temp REAL,
                    boost_pressure REAL,
                    fuel_pressure REAL,
                    knock_retard REAL,
                    fuel_trim_long REAL,
                    fuel_trim_short REAL,
                    maf_rate REAL,
                    throttle_pos REAL,
                    timing_advance REAL,
                    gear INTEGER,
                    load REAL,
                    notes TEXT
                )
            ''')
            
            # Create critical events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS critical_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    parameter TEXT,
                    value REAL,
                    threshold REAL,
                    additional_data TEXT
                )
            ''')
            
            # Create session info table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    vehicle_info TEXT,
                    ecu_info TEXT,
                    user_notes TEXT,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logging.info(f"Database initialized at {self.database_path}")
            
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
            raise
            
    def _setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path("/opt/wrxdash/logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'diagnostics_logger.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def start_session(self, vehicle_info: Dict = None, ecu_info: Dict = None) -> str:
        """Start a new logging session"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            session_data = {
                'id': session_id,
                'start_time': datetime.now().isoformat(),
                'vehicle_info': json.dumps(vehicle_info or {}),
                'ecu_info': json.dumps(ecu_info or {}),
                'user_notes': '',
                'status': 'active'
            }
            
            cursor.execute('''
                INSERT INTO sessions (id, start_time, vehicle_info, ecu_info, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_data['id'],
                session_data['start_time'],
                session_data['vehicle_info'],
                session_data['ecu_info'],
                session_data['status']
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Started logging session: {session_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Error starting session: {e}")
            raise
            
    def end_session(self, session_id: str, user_notes: str = ""):
        """End a logging session"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE sessions 
                SET end_time = ?, user_notes = ?, status = 'completed'
                WHERE id = ?
            ''', (datetime.now().isoformat(), user_notes, session_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Ended logging session: {session_id}")
            
        except Exception as e:
            self.logger.error(f"Error ending session: {e}")
            
    def collect_fast_data(self, obd_conn, session_id: str) -> Optional[Dict]:
        """Collect high-frequency data (every 0.5s)"""
        try:
            # Fast PIDs - critical for knock detection and boost monitoring
            fast_pids = {
                'rpm': obd.commands.RPM,
                'boost_pressure': obd.commands.BOOST_PRESSURE,
                'knock_retard': obd.commands.KNOCK_RETARD,
                'timing_advance': obd.commands.TIMING_ADVANCE
            }
            
            data = {'timestamp': datetime.now().isoformat()}
            
            for param, pid in fast_pids.items():
                response = obd_conn.query(pid)
                if response.value is not None:
                    data[param] = float(response.value.magnitude)
                else:
                    data[param] = None
                    
            return data
            
        except Exception as e:
            self.logger.error(f"Error collecting fast data: {e}")
            return None
            
    def collect_normal_data(self, obd_conn, session_id: str) -> Optional[Dict]:
        """Collect normal frequency data (every 2s)"""
        try:
            normal_pids = {
                'coolant_temp': obd.commands.COOLANT_TEMP,
                'intake_temp': obd.commands.INTAKE_TEMP,
                'speed': obd.commands.SPEED,
                'fuel_pressure': obd.commands.FUEL_PRESSURE,
                'throttle_pos': obd.commands.THROTTLE_POS,
                'maf_rate': obd.commands.MAF
            }
            
            data = {'timestamp': datetime.now().isoformat()}
            
            for param, pid in normal_pids.items():
                response = obd_conn.query(pid)
                if response.value is not None:
                    data[param] = float(response.value.magnitude)
                else:
                    data[param] = None
                    
            return data
            
        except Exception as e:
            self.logger.error(f"Error collecting normal data: {e}")
            return None
            
    def collect_slow_data(self, obd_conn, session_id: str) -> Optional[Dict]:
        """Collect low frequency data (every 10s)"""
        try:
            slow_pids = {
                'fuel_trim_long': obd.commands.LONG_FUEL_TRIM,
                'fuel_trim_short': obd.commands.SHORT_FUEL_TRIM
            }
            
            data = {'timestamp': datetime.now().isoformat()}
            
            for param, pid in slow_pids.items():
                response = obd_conn.query(pid)
                if response.value is not None:
                    data[param] = float(response.value.magnitude)
                else:
                    data[param] = None
                    
            return data
            
        except Exception as e:
            self.logger.error(f"Error collecting slow data: {e}")
            return None
            
    def check_critical_conditions(self, data: Dict) -> List[Dict]:
        """Check for critical conditions and log events"""
        critical_events = []
        
        # Critical thresholds
        thresholds = {
            'knock_retard': {'max': 5.0, 'type': 'knock'},
            'coolant_temp': {'max': 105.0, 'type': 'overheat'},
            'boost_pressure': {'max': 20.0, 'type': 'overboost'},
            'fuel_trim_long': {'max': 10.0, 'type': 'fuel_lean'}
        }
        
        for param, threshold_info in thresholds.items():
            if param in data and data[param] is not None:
                value = data[param]
                
                if threshold_info['type'] == 'knock' and value > threshold_info['max']:
                    critical_events.append({
                        'event_type': 'KNOCK_DETECTED',
                        'severity': 'CRITICAL',
                        'description': f'Knock retard detected: {value:.2f}°',
                        'parameter': param,
                        'value': value,
                        'threshold': threshold_info['max']
                    })
                    
                elif threshold_info['type'] == 'overheat' and value > threshold_info['max']:
                    critical_events.append({
                        'event_type': 'OVERHEATING',
                        'severity': 'CRITICAL',
                        'description': f'High coolant temperature: {value:.1f}°C',
                        'parameter': param,
                        'value': value,
                        'threshold': threshold_info['max']
                    })
                    
                elif threshold_info['type'] == 'overboost' and value > threshold_info['max']:
                    critical_events.append({
                        'event_type': 'OVERBOOST',
                        'severity': 'WARNING',
                        'description': f'High boost pressure: {value:.1f} PSI',
                        'parameter': param,
                        'value': value,
                        'threshold': threshold_info['max']
                    })
                    
                elif threshold_info['type'] == 'fuel_lean' and abs(value) > threshold_info['max']:
                    critical_events.append({
                        'event_type': 'FUEL_TRIM_CRITICAL',
                        'severity': 'WARNING',
                        'description': f'Fuel trim out of range: {value:.1f}%',
                        'parameter': param,
                        'value': value,
                        'threshold': threshold_info['max']
                    })
                    
        return critical_events
        
    def log_data_to_database(self, session_id: str, data: Dict, data_type: str = 'normal'):
        """Log data to SQLite database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Prepare data for insertion
            db_data = {
                'timestamp': data.get('timestamp'),
                'session_id': session_id,
                'rpm': data.get('rpm'),
                'speed': data.get('speed'),
                'coolant_temp': data.get('coolant_temp'),
                'intake_temp': data.get('intake_temp'),
                'boost_pressure': data.get('boost_pressure'),
                'fuel_pressure': data.get('fuel_pressure'),
                'knock_retard': data.get('knock_retard'),
                'fuel_trim_long': data.get('fuel_trim_long'),
                'fuel_trim_short': data.get('fuel_trim_short'),
                'maf_rate': data.get('maf_rate'),
                'throttle_pos': data.get('throttle_pos'),
                'timing_advance': data.get('timing_advance'),
                'gear': data.get('gear'),
                'load': data.get('load'),
                'notes': data.get('notes', '')
            }
            
            cursor.execute('''
                INSERT INTO diagnostics_data (
                    timestamp, session_id, rpm, speed, coolant_temp, intake_temp,
                    boost_pressure, fuel_pressure, knock_retard, fuel_trim_long,
                    fuel_trim_short, maf_rate, throttle_pos, timing_advance, gear, load, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                db_data['timestamp'], db_data['session_id'], db_data['rpm'],
                db_data['speed'], db_data['coolant_temp'], db_data['intake_temp'],
                db_data['boost_pressure'], db_data['fuel_pressure'], db_data['knock_retard'],
                db_data['fuel_trim_long'], db_data['fuel_trim_short'], db_data['maf_rate'],
                db_data['throttle_pos'], db_data['timing_advance'], db_data['gear'],
                db_data['load'], db_data['notes']
            ))
            
            # Check for critical events
            critical_events = self.check_critical_conditions(data)
            for event in critical_events:
                event['timestamp'] = datetime.now().isoformat()
                event['session_id'] = session_id
                event['additional_data'] = json.dumps(data)
                
                cursor.execute('''
                    INSERT INTO critical_events (
                        timestamp, session_id, event_type, severity, description,
                        parameter, value, threshold, additional_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event['timestamp'], event['session_id'], event['event_type'],
                    event['severity'], event['description'], event['parameter'],
                    event['value'], event['threshold'], event['additional_data']
                ))
                
                # Log critical event
                self.logger.warning(f"CRITICAL EVENT: {event['description']}")
                
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error logging to database: {e}")
            
    def export_session_data(self, session_id: str, output_path: str = None) -> str:
        """Export session data to CSV and JSON files"""
        if not output_path:
            output_path = f"/opt/wrxdash/data/export_{session_id}"
            
        try:
            conn = sqlite3.connect(self.database_path)
            
            # Export to CSV
            csv_path = f"{output_path}.csv"
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM diagnostics_data WHERE session_id = ?
                ORDER BY timestamp
            ''', (session_id,))
            
            with open(csv_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([description[0] for description in cursor.description])
                writer.writerows(cursor.fetchall())
                
            # Export critical events to JSON
            json_path = f"{output_path}_events.json"
            cursor.execute('''
                SELECT * FROM critical_events WHERE session_id = ?
                ORDER BY timestamp
            ''', (session_id,))
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    'timestamp': row[1],
                    'event_type': row[2],
                    'severity': row[3],
                    'description': row[4],
                    'parameter': row[5],
                    'value': row[6],
                    'threshold': row[7]
                })
                
            with open(json_path, 'w') as jsonfile:
                json.dump(events, jsonfile, indent=2)
                
            conn.close()
            
            self.logger.info(f"Session data exported to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error exporting session data: {e}")
            raise
            
    def start_logging(self, session_id: str, obd_device: str = "/dev/ttyUSB0"):
        """Start the main logging process"""
        try:
            # Connect to OBD2
            obd_conn = obd.OBD(obd_device)
            if not obd_conn.is_connected():
                raise Exception("Failed to connect to OBD2 device")
                
            self.running = True
            self.logger.info(f"Starting logging for session {session_id}")
            
            while self.running:
                current_time = time.time()
                
                # Collect fast data every 0.5s
                if current_time - self.last_collection['fast'] >= self.intervals['fast']:
                    fast_data = self.collect_fast_data(obd_conn, session_id)
                    if fast_data:
                        self.log_data_to_database(session_id, fast_data, 'fast')
                    self.last_collection['fast'] = current_time
                    
                # Collect normal data every 2s
                if current_time - self.last_collection['normal'] >= self.intervals['normal']:
                    normal_data = self.collect_normal_data(obd_conn, session_id)
                    if normal_data:
                        self.log_data_to_database(session_id, normal_data, 'normal')
                    self.last_collection['normal'] = current_time
                    
                # Collect slow data every 10s
                if current_time - self.last_collection['slow'] >= self.intervals['slow']:
                    slow_data = self.collect_slow_data(obd_conn, session_id)
                    if slow_data:
                        self.log_data_to_database(session_id, slow_data, 'slow')
                    self.last_collection['slow'] = current_time
                    
                time.sleep(0.1)  # Check every 100ms
                
        except KeyboardInterrupt:
            self.logger.info("Logging stopped by user")
        except Exception as e:
            self.logger.error(f"Logging error: {e}")
        finally:
            self.running = False
            if 'obd_conn' in locals():
                obd_conn.close()
            self.end_session(session_id)
            
    def stop_logging(self):
        """Stop the logging process"""
        self.running = False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='WRXDash Diagnostics Logger')
    parser.add_argument('--device', default='/dev/ttyUSB0', help='OBD2 device path')
    parser.add_argument('--session-id', help='Session ID (auto-generated if not provided)')
    parser.add_argument('--export', action='store_true', help='Export session data after logging')
    
    args = parser.parse_args()
    
    logger = DiagnosticsLogger()
    
    if not args.session_id:
        args.session_id = logger.start_session()
        
    try:
        logger.start_logging(args.session_id, args.device)
    except KeyboardInterrupt:
        print("\nStopping logger...")
        logger.stop_logging()
        
        if args.export:
            export_path = logger.export_session_data(args.session_id)
            print(f"Session data exported to {export_path}")
