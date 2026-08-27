from sheets_client import SheetsClient
import os
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "service-account-key.json")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

client = SheetsClient(CREDENTIALS_FILE, SHEET_ID)

# Get all deliveries
deliveries = client.get_deliveries()

print("\n📋 Current Delivery Status:")
print("=" * 60)
for d in deliveries:
    rider = d['assigned_rider'] or "Unassigned"
    print(f"{d['delivery_id']}: {d['status']} - {rider}")
print("=" * 60)

# Count by status
status_counts = {}
for d in deliveries:
    status = d['status']
    status_counts[status] = status_counts.get(status, 0) + 1

print("\n📊 Summary:")
for status, count in status_counts.items():
    print(f"  {status}: {count}")