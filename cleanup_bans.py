from app import create_app, db
from app.models import Blacklist, IPWarning, Warn

app = create_app()

with app.app_context():
    print("Clearing Blacklist...")
    Blacklist.query.delete()
    
    print("Clearing IP Warnings...")
    IPWarning.query.delete()
    
    print("Clearing User Warnings...")
    Warn.query.delete()
    
    db.session.commit()
    print("Database cleanup complete. All bans and warnings removed.")
