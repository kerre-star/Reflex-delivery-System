from sheets_client import SheetsClient
import os
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "service-account-key.json")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

client = SheetsClient(CREDENTIALS_FILE, SHEET_ID)

# Get all deliveries
deliveries = client.get_deliveries()

print("🔧 Fixing delivery statuses...")
print("-" * 60)
fixed_count = 0

for delivery in deliveries:
    delivery_id = delivery['delivery_id']
    assigned_rider = delivery.get('assigned_rider', '').strip()
    status = delivery.get('status', 'PENDING')
    
    # If rider is assigned but status is PENDING, fix it
    if assigned_rider and status == 'PENDING':
        print(f"  Fixing {delivery_id} - assigned to {assigned_rider} but status is PENDING")
        try:
            # Find the row and update status
            cell = client.deliveries_sheet.find(delivery_id)
            if cell:
                # Update column 6 (F) which is the status column
                client.deliveries_sheet.update_cell(cell.row, 6, "ASSIGNED")
                # Update column 9 (I) which is updated_at
                from datetime import datetime
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                client.deliveries_sheet.update_cell(cell.row, 9, now)
                fixed_count += 1
                print(f"    ✅ Fixed: {delivery_id} → ASSIGNED")
        except Exception as e:
            print(f"    ❌ Error fixing {delivery_id}: {e}")

print("-" * 60)
print(f"✅ Fixed {fixed_count} deliveries")
print("\n📋 Now check your Google Sheet - all assigned deliveries should show ASSIGNED status")