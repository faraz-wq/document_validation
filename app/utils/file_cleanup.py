"""
File cleanup service for managing temporary and old files
Automatically removes files older than retention period to prevent disk space issues
"""

import os
import shutil
import threading
import time
from datetime import datetime, timedelta
from typing import List
from app.logging_config import get_logger

logger = get_logger(__name__)


class FileCleanupService:
    """Background service for cleaning up old temporary files"""
    
    def __init__(
        self,
        cleanup_interval_minutes: int = 60,
        retention_hours: int = 24
    ):
        """
        Initialize the file cleanup service.
        
        Args:
            cleanup_interval_minutes: How often to run cleanup (default: 60 minutes)
            retention_hours: How long to keep files (default: 24 hours)
        """
        self.cleanup_interval = cleanup_interval_minutes * 60  # Convert to seconds
        self.retention_delta = timedelta(hours=retention_hours)
        
        # Directories to clean up
        self.data_dirs = [
            "data/documents_v1",
            "temp_ocr_batches",
            "records/gemini_raw",
            "records/ocr_raw",
            "extracted_results"
        ]
        
        self.is_running = False
        self.cleanup_thread = None
        
        logger.info(f"FileCleanupService initialized: interval={cleanup_interval_minutes}min, "
                   f"retention={retention_hours}h")
    
    def start_cleanup_service(self):
        """Start the automatic cleanup service in a background thread"""
        if not self.is_running:
            self.is_running = True
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.cleanup_thread.start()
            logger.info("File cleanup service started")
    
    def stop_cleanup_service(self):
        """Stop the cleanup service"""
        self.is_running = False
        if self.cleanup_thread:
            logger.info("File cleanup service stopped")
    
    def _cleanup_loop(self):
        """Main cleanup loop that runs in background"""
        while self.is_running:
            try:
                self.cleanup_old_files()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error during file cleanup: {e}", exc_info=True)
                # Continue running even if cleanup fails
                time.sleep(60)  # Wait a minute before retrying
    
    def cleanup_old_files(self) -> dict:
        """
        Remove files older than retention period.
        
        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_time = datetime.now() - self.retention_delta
        stats = {
            'files_deleted': 0,
            'bytes_freed': 0,
            'errors': 0,
            'directories_checked': 0
        }
        
        logger.info(f"Starting file cleanup (cutoff: {cutoff_time})")
        
        for dir_path in self.data_dirs:
            if not os.path.exists(dir_path):
                logger.debug(f"Directory does not exist, skipping: {dir_path}")
                continue
            
            stats['directories_checked'] += 1
            
            try:
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            # Get file modification time
                            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                            
                            if file_mtime < cutoff_time:
                                # Get file size before deletion
                                file_size = os.path.getsize(file_path)
                                
                                # Delete the file
                                os.remove(file_path)
                                
                                stats['files_deleted'] += 1
                                stats['bytes_freed'] += file_size
                                
                                logger.debug(f"Deleted old file: {file_path} "
                                           f"(age: {datetime.now() - file_mtime}, "
                                           f"size: {file_size / 1024:.1f}KB)")
                        
                        except OSError as e:
                            logger.error(f"Could not delete file {file_path}: {e}")
                            stats['errors'] += 1
                        except Exception as e:
                            logger.error(f"Unexpected error processing file {file_path}: {e}")
                            stats['errors'] += 1
            
            except Exception as e:
                logger.error(f"Error processing directory {dir_path}: {e}", exc_info=True)
                stats['errors'] += 1
        
        if stats['files_deleted'] > 0:
            logger.info(f"Cleanup completed: deleted {stats['files_deleted']} files, "
                       f"freed {stats['bytes_freed'] / (1024 * 1024):.2f}MB, "
                       f"errors: {stats['errors']}")
        else:
            logger.debug(f"Cleanup completed: no old files found")
        
        return stats
    
    def manual_cleanup(self) -> dict:
        """
        Manually trigger cleanup and return statistics.
        
        Returns:
            Dictionary with cleanup statistics
        """
        logger.info("Manual cleanup triggered")
        return self.cleanup_old_files()
    
    def get_directory_stats(self) -> dict:
        """
        Get statistics about monitored directories.
        
        Returns:
            Dictionary with directory statistics
        """
        stats = {}
        
        for dir_path in self.data_dirs:
            if not os.path.exists(dir_path):
                stats[dir_path] = {'exists': False}
                continue
            
            try:
                total_size = 0
                file_count = 0
                
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            total_size += os.path.getsize(file_path)
                            file_count += 1
                        except OSError:
                            pass
                
                stats[dir_path] = {
                    'exists': True,
                    'file_count': file_count,
                    'total_size_mb': total_size / (1024 * 1024),
                    'total_size_bytes': total_size
                }
            
            except Exception as e:
                logger.error(f"Error getting stats for {dir_path}: {e}")
                stats[dir_path] = {'exists': True, 'error': str(e)}
        
        return stats


# Global file cleanup service instance
file_cleanup_service = FileCleanupService(
    cleanup_interval_minutes=int(os.getenv("FILE_CLEANUP_INTERVAL_MINUTES", "60")),
    retention_hours=int(os.getenv("FILE_RETENTION_HOURS", "24"))
)
