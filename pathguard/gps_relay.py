"""GPS Data Relay - Receives coordinates from smartphone USB tethering or GPS dongle."""
import logging
import json
import time
import threading
from dataclasses import dataclass
from typing import Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger(__name__)

@dataclass
class GPSFix:
    latitude: float
    longitude: float
    altitude: float = 0.0
    speed_kmh: float = 0.0
    heading: float = 0.0
    timestamp: float = 0.0
    accuracy_m: float = 0.0

class _GPSRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            fix = GPSFix(
                latitude=float(data.get('latitude', 0.0)),
                longitude=float(data.get('longitude', 0.0)),
                altitude=float(data.get('altitude', 0.0)),
                speed_kmh=float(data.get('speed_kmh', 0.0)),
                heading=float(data.get('heading', 0.0)),
                timestamp=float(data.get('timestamp', time.time())),
                accuracy_m=float(data.get('accuracy_m', 0.0))
            )
            self.server.receiver._update_fix(fix)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        except Exception as e:
            logger.error(f"Error parsing GPS data: {e}")
            self.send_response(400)
            self.end_headers()
            
    def log_message(self, format, *args):
        pass # Suppress logging

class GPSReceiver:
    """Receives GPS data via HTTP POST from smartphone relay app."""
    
    def __init__(self, port=5000):
        self.port = port
        self.latest_fix: Optional[GPSFix] = None
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable] = []
        self._running = False
    
    def on_fix(self, callback: Callable[[GPSFix], None]):
        self._callbacks.append(callback)
        
    def _update_fix(self, fix: GPSFix):
        self.latest_fix = fix
        for callback in self._callbacks:
            try:
                callback(fix)
            except Exception as e:
                logger.error(f"Error in GPS callback: {e}")
    
    def start(self):
        if self._running:
            return
        
        self._running = True
        self._server = HTTPServer(('0.0.0.0', self.port), _GPSRequestHandler)
        self._server.receiver = self
        
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info(f"GPSReceiver started on port {self.port}")
    
    def stop(self):
        if not self._running:
            return
            
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._running = False
        logger.info("GPSReceiver stopped")
    
    def get_latest(self) -> Optional[GPSFix]:
        return self.latest_fix

class SimulatedGPS:
    """Simulated GPS for demo/testing. Follows a predefined route."""
    
    def __init__(self, waypoints: list[tuple[float, float]] = None):
        # Default waypoints: a loop around a demo area
        # Use coordinates around Delhi for Indian road context
        if waypoints is None:
            self.waypoints = [
                (28.6139, 77.2090),  # India Gate
                (28.6145, 77.2095),
                (28.6150, 77.2100),
                (28.6155, 77.2105),
                (28.6160, 77.2110),
                (28.6155, 77.2115),
                (28.6150, 77.2120),
                (28.6145, 77.2115),
                (28.6139, 77.2090),  # Loop back
            ]
        else:
            self.waypoints = waypoints
        self._index = 0
        self._running = False
        self._last_time = time.time()
        self._callbacks = []

    def on_fix(self, callback: Callable[[GPSFix], None]):
        self._callbacks.append(callback)

    def get_latest(self) -> GPSFix:
        # Interpolate between waypoints, advance index
        # For simplicity, advance waypoint every 2 seconds
        current_time = time.time()
        if current_time - self._last_time > 2.0:
            self._index = (self._index + 1) % len(self.waypoints)
            self._last_time = current_time
            
        wp = self.waypoints[self._index]
        fix = GPSFix(
            latitude=wp[0], longitude=wp[1],
            speed_kmh=20.0, timestamp=current_time
        )
        for cb in self._callbacks:
            cb(fix)
        return fix
        
    def start(self):
        pass
        
    def stop(self):
        pass
