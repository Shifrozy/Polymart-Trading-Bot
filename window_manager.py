"""
15-minute window management and eligibility checking
"""

from datetime import datetime, timedelta
import logging


logger = logging.getLogger(__name__)


class WindowManager:
    """Manages 15-minute trading windows and entry eligibility"""
    
    def __init__(self, window_duration_minutes: int = 15):
        self.window_duration = timedelta(minutes=window_duration_minutes)
        self.window_duration_minutes = window_duration_minutes
    
    def get_current_window(self, current_time: datetime = None):
        """Get the current 15-minute window start and end times"""
        if current_time is None:
            current_time = datetime.utcnow()
        
        # Round down to nearest 15-minute mark
        minutes = (current_time.minute // self.window_duration_minutes) * self.window_duration_minutes
        window_start = current_time.replace(minute=minutes, second=0, microsecond=0)
        window_end = window_start + self.window_duration
        
        return window_start, window_end
    
    def get_time_remaining(self, current_time: datetime = None):
        """Get seconds remaining until window expiry"""
        if current_time is None:
            current_time = datetime.utcnow()
        
        _, window_end = self.get_current_window(current_time)
        remaining = (window_end - current_time).total_seconds()
        return max(0, remaining)
    
    def is_entry_eligible(self, current_time: datetime, max_remaining: int, min_remaining: int):
        """
        Check if current time is within entry window
        
        Args:
            current_time: Current timestamp
            max_remaining: Maximum seconds remaining for entry (e.g., 300 for 5:00)
            min_remaining: Minimum seconds remaining for entry (e.g., 90 for 1:30)
        
        Returns:
            bool: True if within entry window
        """
        remaining = self.get_time_remaining(current_time)
        eligible = min_remaining <= remaining <= max_remaining
        
        if not eligible:
            logger.debug(f"Entry not eligible: {remaining:.0f}s remaining (need {min_remaining}-{max_remaining}s)")
        
        return eligible
    
    def get_window_id(self, current_time: datetime = None):
        """Get unique identifier for current window"""
        window_start, _ = self.get_current_window(current_time)
        return window_start.strftime("%Y%m%d_%H%M")


# Test the WindowManager
if __name__ == "__main__":
    wm = WindowManager(15)
    
    print("Testing WindowManager:")
    print("=" * 50)
    
    now = datetime.utcnow()
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    window_start, window_end = wm.get_current_window(now)
    print(f"Window start: {window_start.strftime('%H:%M:%S')}")
    print(f"Window end:   {window_end.strftime('%H:%M:%S')}")
    
    remaining = wm.get_time_remaining(now)
    print(f"Time remaining: {remaining:.0f} seconds")
    
    window_id = wm.get_window_id(now)
    print(f"Window ID: {window_id}")
    
    is_eligible = wm.is_entry_eligible(now, 300, 90)
    print(f"Entry eligible: {is_eligible}")
    
    print("=" * 50)