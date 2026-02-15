#!/usr/bin/env python3
"""
Restore Script for Server Systems
Restores from backup files created by backup.py.

Usage:
    python scripts/restore.py --list
    python scripts/restore.py --database backups/database_20240101_020000.db.gz
    python scripts/restore.py --data backups/data_20240101_020000.tar.gz
"""

import argparse
import shutil
import gzip
import os
from pathlib import Path

# Configuration
BACKUP_DIR = Path(os.environ.get('BACKUP_DIR', './backups'))
DATA_DIR = Path('./data')
DATABASE_FILE = DATA_DIR / 'database.db'


def list_backups():
    """List available backup files."""
    if not BACKUP_DIR.exists():
        print(f"No backup directory found at {BACKUP_DIR}")
        return
    
    print("\nAvailable Backups:")
    print("-" * 60)
    
    backups = sorted(BACKUP_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
    
    for filepath in backups:
        if filepath.is_file():
            size_mb = filepath.stat().st_size / (1024 * 1024)
            mtime = filepath.stat().st_mtime
            from datetime import datetime
            mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  {filepath.name:<40} {size_mb:>6.2f} MB  {mtime_str}")
    
    print("-" * 60)


def restore_database(backup_file: str):
    """Restore database from gzipped backup."""
    backup_path = Path(backup_file)
    
    if not backup_path.exists():
        print(f"Error: Backup file not found: {backup_file}")
        return False
    
    # Create backup of current database
    if DATABASE_FILE.exists():
        current_backup = DATABASE_FILE.with_suffix('.db.before_restore')
        shutil.copy2(DATABASE_FILE, current_backup)
        print(f"Current database backed up to: {current_backup}")
    
    # Restore from gzipped backup
    print(f"Restoring database from: {backup_file}")
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    with gzip.open(backup_path, 'rb') as f_in:
        with open(DATABASE_FILE, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    print(f"✓ Database restored to: {DATABASE_FILE}")
    return True


def restore_data(backup_file: str):
    """Restore data directory from tar.gz backup."""
    backup_path = Path(backup_file)
    
    if not backup_path.exists():
        print(f"Error: Backup file not found: {backup_file}")
        return False
    
    # Create backup of current data
    if DATA_DIR.exists():
        current_backup = DATA_DIR.with_suffix('.before_restore')
        if current_backup.exists():
            shutil.rmtree(current_backup)
        shutil.move(str(DATA_DIR), str(current_backup))
        print(f"Current data backed up to: {current_backup}")
    
    # Restore from archive
    print(f"Restoring data from: {backup_file}")
    
    shutil.unpack_archive(backup_path, DATA_DIR.parent)
    
    print(f"✓ Data restored to: {DATA_DIR}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Restore from Server Systems backups',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/restore.py --list
  python scripts/restore.py --database backups/database_20240101_020000.db.gz
  python scripts/restore.py --data backups/data_20240101_020000.tar.gz
        """
    )
    
    parser.add_argument('--list', action='store_true', help='List available backups')
    parser.add_argument('--database', type=str, help='Restore database from backup file')
    parser.add_argument('--data', type=str, help='Restore data directory from backup file')
    
    args = parser.parse_args()
    
    if args.list:
        list_backups()
    elif args.database:
        print("\n⚠️  WARNING: This will overwrite the current database!")
        confirm = input("Type 'yes' to continue: ")
        if confirm.lower() == 'yes':
            restore_database(args.database)
        else:
            print("Restore cancelled.")
    elif args.data:
        print("\n⚠️  WARNING: This will overwrite the current data directory!")
        confirm = input("Type 'yes' to continue: ")
        if confirm.lower() == 'yes':
            restore_data(args.data)
        else:
            print("Restore cancelled.")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
