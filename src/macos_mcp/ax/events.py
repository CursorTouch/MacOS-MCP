"""
macOS Accessibility event observation system.
Provides AXObserver wrapper for monitoring accessibility notifications
(focus changes, structure changes, property changes, etc.).

Equivalent to the Windows UIA events.py module, adapted for macOS.
"""

import logging
import time
from typing import Any, Callable, Optional, Sequence, Set
from threading import Thread, Event, Lock

import objc
from ApplicationServices import (
    AXObserverCreate,
    AXObserverAddNotification,
    AXObserverRemoveNotification,
    AXObserverGetRunLoopSource,
    AXUIElementCreateApplication,
    kAXErrorSuccess,
)
from CoreFoundation import (
    CFRunLoopGetCurrent,
    CFRunLoopAddSource,
    CFRunLoopRemoveSource,
    CFRunLoopRunInMode,
    kCFRunLoopDefaultMode,
)
from Cocoa import NSWorkspace

from .enums import (
    Notification,
    FOCUS_NOTIFICATIONS,
    STRUCTURE_NOTIFICATIONS,
    PROPERTY_NOTIFICATIONS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Global Callback Registry
# =============================================================================

# Global registry for EventObserver instances (needed for callback routing)
_observer_registry: dict[int, 'EventObserver'] = {}


@objc.callbackFor(AXObserverCreate)
def _global_observer_callback(observer, element, notification, refcon):
    """
    Global callback function for AXObserver notifications.
    Routes notifications to appropriate EventObserver instances.
    """
    try:
        for event_observer in _observer_registry.values():
            if event_observer._has_observer(observer):
                event_observer._dispatch(element, str(notification), refcon)
                break
    except Exception as e:
        logger.debug(f"Error in global observer callback: {e}")


# =============================================================================
# AppObserver - Per-Application Observer
# =============================================================================

class AppObserver:
    """
    Observer for a single application's accessibility events.
    Each application requires its own AXObserver instance.

    Equivalent to the per-process observer in Windows UIA.
    """

    def __init__(self, pid: int, parent: 'EventObserver'):
        self.pid = pid
        self.parent = parent
        self.observer = None
        self.ax_app = None
        self.run_loop_source = None
        self.registered_notifications: Set[str] = set()

    def start(self, notifications: Sequence[str]) -> bool:
        """
        Create the observer and register for notifications.

        Args:
            notifications: List of notification name strings to watch.

        Returns:
            True if successfully started.
        """
        try:
            self.ax_app = AXUIElementCreateApplication(self.pid)
            if not self.ax_app:
                return False

            error, self.observer = AXObserverCreate(
                self.pid,
                _global_observer_callback,
                None
            )
            if error != kAXErrorSuccess or not self.observer:
                return False

            self.run_loop_source = AXObserverGetRunLoopSource(self.observer)
            if not self.run_loop_source:
                return False

            run_loop = CFRunLoopGetCurrent()
            CFRunLoopAddSource(run_loop, self.run_loop_source, kCFRunLoopDefaultMode)

            for notification in notifications:
                try:
                    error = AXObserverAddNotification(
                        self.observer,
                        self.ax_app,
                        notification,
                        self.pid
                    )
                    if error == kAXErrorSuccess:
                        self.registered_notifications.add(str(notification))
                except Exception:
                    pass

            return len(self.registered_notifications) > 0

        except Exception as e:
            logger.debug(f"Failed to start observer for PID {self.pid}: {e}")
            return False

    def stop(self) -> None:
        """Stop the observer and clean up resources."""
        try:
            if self.observer and self.ax_app:
                for notif_str in list(self.registered_notifications):
                    try:
                        AXObserverRemoveNotification(
                            self.observer,
                            self.ax_app,
                            notif_str
                        )
                    except Exception:
                        pass
                self.registered_notifications.clear()

            if self.run_loop_source:
                try:
                    CFRunLoopRemoveSource(
                        CFRunLoopGetCurrent(),
                        self.run_loop_source,
                        kCFRunLoopDefaultMode
                    )
                except Exception:
                    pass
                self.run_loop_source = None

            self.observer = None
            self.ax_app = None

        except Exception as e:
            logger.debug(f"Error stopping observer for PID {self.pid}: {e}")

    def matches_observer(self, observer: Any) -> bool:
        """Check if this AppObserver owns the given AXObserver."""
        return self.observer is observer


# =============================================================================
# EventObserver - Main Event Observation Service
# =============================================================================

class EventObserver:
    """
    High-level event observation service for macOS Accessibility.
    Manages multiple AppObserver instances to track changes across applications.

    Equivalent to the Windows UIA event handler system.

    Usage:
        observer = EventObserver()
        observer.on_focus_changed = my_focus_callback
        observer.on_structure_changed = my_structure_callback
        observer.start()
        # ... run your app ...
        observer.stop()

    Or as a context manager:
        with EventObserver() as observer:
            observer.on_focus_changed = my_callback
            # ... run your app ...
    """

    _instance_counter = 0

    def __init__(self, debounce_interval: float = 0.05):
        """
        Args:
            debounce_interval: Minimum time between events (seconds).
        """
        EventObserver._instance_counter += 1
        self._instance_id = EventObserver._instance_counter

        self._running = Event()
        self._thread: Optional[Thread] = None
        self._lock = Lock()

        # Callbacks
        self.on_focus_changed: Optional[Callable] = None
        self.on_structure_changed: Optional[Callable] = None
        self.on_property_changed: Optional[Callable] = None

        # Per-app observers
        self._app_observers: dict[int, AppObserver] = {}
        self._observed_pids: Set[int] = set()

        # Debouncing
        self._last_event_time: float = 0
        self._debounce_interval = debounce_interval

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    @property
    def is_running(self) -> bool:
        """Check if the observer is running."""
        return self._running.is_set()

    def start(self) -> None:
        """Start the event observation thread."""
        if self._running.is_set():
            return

        _observer_registry[self._instance_id] = self
        self._running.set()
        self._thread = Thread(
            target=self._run,
            name=f"AXEventObserver-{self._instance_id}",
            daemon=True,
        )
        self._thread.start()
        logger.debug(f"EventObserver started (instance {self._instance_id})")

    def stop(self) -> None:
        """Stop the event observation thread."""
        if not self._running.is_set():
            return

        self._running.clear()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        _observer_registry.pop(self._instance_id, None)
        logger.debug(f"EventObserver stopped (instance {self._instance_id})")

    def _has_observer(self, observer: Any) -> bool:
        """Check if this EventObserver owns the given AXObserver."""
        with self._lock:
            for app_observer in self._app_observers.values():
                if app_observer.matches_observer(observer):
                    return True
        return False

    def _dispatch(self, element: Any, notification: str, pid: int) -> None:
        """Dispatch a notification to the appropriate callback."""
        current_time = time.time()
        if current_time - self._last_event_time < self._debounce_interval:
            return
        self._last_event_time = current_time

        try:
            if notification in FOCUS_NOTIFICATIONS and self.on_focus_changed:
                self.on_focus_changed(element, notification, pid)
            elif notification in STRUCTURE_NOTIFICATIONS and self.on_structure_changed:
                self.on_structure_changed(element, notification, pid)
            elif notification in PROPERTY_NOTIFICATIONS and self.on_property_changed:
                self.on_property_changed(element, notification, pid)
        except Exception as e:
            logger.debug(f"Error in notification dispatch: {e}")

    def _get_running_app_pids(self) -> Set[int]:
        """Get PIDs of all running user-facing applications."""
        pids = set()
        try:
            apps = NSWorkspace.sharedWorkspace().runningApplications()
            for app in apps:
                if app.activationPolicy() == 0:  # Regular apps
                    pids.add(app.processIdentifier())
        except Exception:
            pass
        return pids

    def _get_notifications_to_register(self) -> list[str]:
        """Determine which notifications to register based on set callbacks."""
        notifications = []

        if self.on_focus_changed:
            notifications.extend([
                Notification.FocusedUIElementChanged,
                Notification.FocusedWindowChanged,
                Notification.MainWindowChanged,
            ])

        if self.on_structure_changed:
            notifications.extend([
                Notification.Created,
                Notification.UIElementDestroyed,
                Notification.WindowCreated,
                Notification.MenuOpened,
                Notification.MenuClosed,
                Notification.RowCountChanged,
            ])

        if self.on_property_changed:
            notifications.extend([
                Notification.ValueChanged,
                Notification.TitleChanged,
                Notification.SelectedTextChanged,
                Notification.SelectedChildrenChanged,
                Notification.SelectedChildrenMoved,
                Notification.SelectedRowsChanged,
                Notification.SelectedColumnsChanged,
                Notification.SelectedCellsChanged,
                Notification.UnitsChanged,
                Notification.Moved,
                Notification.Resized,
            ])

        return notifications

    def _update_observers(self) -> None:
        """Update observers to match currently running applications."""
        with self._lock:
            current_pids = self._get_running_app_pids()
            notifications = self._get_notifications_to_register()

            if not notifications:
                for observer in self._app_observers.values():
                    observer.stop()
                self._app_observers.clear()
                self._observed_pids.clear()
                return

            # Remove observers for terminated apps
            terminated = self._observed_pids - current_pids
            for pid in terminated:
                if pid in self._app_observers:
                    self._app_observers[pid].stop()
                    del self._app_observers[pid]
                self._observed_pids.discard(pid)

            # Add observers for new apps
            new_pids = current_pids - self._observed_pids
            for pid in new_pids:
                observer = AppObserver(pid, self)
                if observer.start(notifications):
                    self._app_observers[pid] = observer
                    self._observed_pids.add(pid)

    def _run(self) -> None:
        """Main event loop running in a dedicated thread."""
        try:
            while self._running.is_set():
                self._update_observers()
                CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, False)
        except Exception as e:
            logger.error(f"EventObserver died: {e}")
        finally:
            with self._lock:
                for observer in self._app_observers.values():
                    try:
                        observer.stop()
                    except Exception:
                        pass
                self._app_observers.clear()
                self._observed_pids.clear()
