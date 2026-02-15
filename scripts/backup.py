#!/usr/bin/env python3
"""
Backup Script for Server Systems
Run manually or via cron for automated backups.

Usage:
    python scripts/backup.py
    
Cron (daily at 2 AM):
    0 2 * * * cd /opt/server-systems && python scripts/backup.py
"""

import shutil
import datetime
import os
import gzip
from pathlib import Path

# Configuration
BACKUP_DIR = Path(os.environ.get('BACKUP_DIR', './backups'))
DATA_DIR = Path('./data')
DATABASE_FILE = DATA_DIR / 'database.db'
KEEP_DAYS = 30  # How many days of backups to keep


def ensure_backup_dir():
    """Create backup directory if it doesn't exist."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Backup directory: {BACKUP_DIR.absolute()}")


def backup_database() -> str | None:
    """Backup the SQLite database with compression."""
    if not DATABASE_FILE.exists():
        print(f"Warning: Database not found at {DATABASE_FILE}")
        return None
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'database_{timestamp}.db.gz'
    backup_path = BACKUP_DIR / backup_name
    
    # Read and compress
    with open(DATABASE_FILE, 'rb') as f_in:
        with gzip.open(backup_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    size_mb = backup_path.stat().st_size / (1024 * 1024)
    print(f"✓ Database backup: {backup_name} ({size_mb:.2f} MB)")
    return str(backup_path)


def backup_data_directory() -> str | None:
    """Backup the entire data directory (excluding database)."""
    if not DATA_DIR.exists():
        print(f"Warning: Data directory not found at {DATA_DIR}")
        return None
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'data_{timestamp}'
    backup_path = BACKUP_DIR / backup_name
    
    # Create archive (excludes database which is backed up separately)
    shutil.make_archive(
        str(backup_path),
        'gztar',
        root_dir=DATA_DIR.parent,
        base_dir=DATA_DIR.name
    )
    
    archive_path = Path(f'{backup_path}.tar.gz')
    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"✓ Data backup: {archive_path.name} ({size_mb:.2f} MB)")
    return str(archive_path)


def cleanup_old_backups():
    """Remove backups older than KEEP_DAYS."""
    if not BACKUP_DIR.exists():
        return
    
    cutoff = datetime.datetime.now() - datetime.timedelta(days=KEEP_DAYS)
    removed = 0
    
    for filepath in BACKUP_DIR.iterdir():
        if filepath.is_file():
            mtime = datetime.datetime.fromtimestamp(filepath.stat().st_mtime)
            if mtime < cutoff:
                filepath.unlink()
                removed += 1
    
    if removed > 0:
        print(f"✓ Cleaned up {removed} old backup(s)")


def main():
    """Run full backup process."""
    print("=" * 50)
    print(f"Starting backup: {datetime.datetime.now().isoformat()}")
    print("=" * 50)
    
    ensure_backup_dir()
    
    # Run backups
    db_backup = backup_database()
    data_backup = backup_data_directory()
    
    # Cleanup old backups
    cleanup_old_backups()
    
    print("=" * 50)
    print("Backup complete!")
    
    if db_backup:
        print(f"  Database: {db_backup}")
    if data_backup:
        print(f"  Data: {data_backup}")
    
    print("=" * 50)


if __name__ == '__main__':
    main()
