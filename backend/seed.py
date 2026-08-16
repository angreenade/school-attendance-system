"""
Dev convenience script: wipes and re-seeds the database with demo data.

For local development only. Cloud deployments auto-seed once on first boot
(see the startup hook in app/main.py), which never wipes real data.

Run with: python3 seed.py
"""
from app.database import Base, engine, SessionLocal
from app.seed_data import run_seed

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("Wiping existing demo data and re-seeding...")
stats = run_seed(db, wipe=True)
print("Admin login: admin / admin123")
print("Teacher login: teacher / teacher123")
print(
    f"Seeded {stats['students']} students, {stats['class_sections']} class sections, "
    f"{stats['locations']} locations, {stats['attendance_logs']} attendance logs."
)
db.close()
