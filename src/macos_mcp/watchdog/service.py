"""
WatchDog Service for monitoring macOS Accessibility events.
Delegates to the ax module's EventObserver for the underlying AXObserver management.
"""
from macos_mcp.ax import EventObserver
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WatchDog:
    """
    Unified WatchDog Service for monitoring macOS Accessibility events.
    Wraps the ax module's EventObserver to track changes across applications.
    
    The WatchDog helps overcome laziness in the accessibility tree by:
    1. Monitoring focus changes when users interact with UI
    2. Detecting structure changes when UI elements are added/removed
    3. Tracking property changes like value updates
    
    This allows the tree traversal to be more complete as notifications
    trigger callbacks that can force fresh tree reads.
    
    Usage:
        watchdog = WatchDog()
        watchdog.set_focus_callback(on_focus_change)
        watchdog.set_structure_callback(on_structure_change)
        watchdog.start()
        
        # ... run your app ...
        
        watchdog.stop()
    """
    
    def __init__(self, debounce_interval: float = 0.05):
        """
        Args:
            debounce_interval: Minimum time between events in seconds (default 50ms).
        """
        self._observer = EventObserver(debounce_interval=debounce_interval)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
    
    @property
    def is_running(self) -> bool:
        """Check if the watchdog is currently running."""
        return self._observer.is_running
    
    def start(self):
        """Start the watchdog service."""
        self._observer.start()
        logger.info("WatchDog service started")
    
    def stop(self):
        """Stop the watchdog service."""
        self._observer.stop()
        logger.info("WatchDog service stopped")
    
    def set_focus_callback(self, callback: Optional[Callable]):
        """
        Set the callback for focus changes. Pass None to disable.
        
        Callback signature: callback(element, notification: str, pid: int)
        - element: The AXUIElement that gained focus
        - notification: The notification type (e.g., 'AXFocusedUIElementChanged')
        - pid: Process ID of the application
        """
        self._observer.on_focus_changed = callback
    
    def set_structure_callback(self, callback: Optional[Callable]):
        """
        Set the callback for structure changes. Pass None to disable.
        
        Callback signature: callback(element, notification: str, pid: int)
        - element: The AXUIElement affected by the structure change
        - notification: The notification type (e.g., 'AXCreated')
        - pid: Process ID of the application
        """
        self._observer.on_structure_changed = callback
    
    def set_property_callback(self, callback: Optional[Callable]):
        """
        Set the callback for property changes. Pass None to disable.
        
        Callback signature: callback(element, notification: str, pid: int)
        - element: The AXUIElement whose property changed
        - notification: The notification type (e.g., 'AXValueChanged')
        - pid: Process ID of the application
        """
        self._observer.on_property_changed = callback
