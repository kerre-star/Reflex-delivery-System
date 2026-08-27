from sheets_client import SheetsClient
import os
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "service-account-key.json")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

client = SheetsClient(CREDENTIALS_FILE, SHEET_ID)

# Get all deliveries directly from Google Sheets
deliveries = client.deliveries_sheet.get_all_records()

print("\n📋 What's ACTUALLY in Google Sheets:")
print("=" * 70)
for record in deliveries:
    if record.get("delivery_id"):
        print(f"ID: {record['delivery_id']}")
        print(f"  Status: {record.get('status', 'N/A')}")
        print(f"  Rider: {record.get('assigned_rider', 'N/A')}")
        print(f"  Updated: {record.get('updated_at', 'N/A')}")
        print("-" * 40)