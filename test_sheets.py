from sheets_client import SheetsClient
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "service-account-key.json")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")  # Will read from .env

if not SHEET_ID:
    raise ValueError("Please set GOOGLE_SHEET_ID in .env file")

try:
    client = SheetsClient(CREDENTIALS_FILE, SHEET_ID)
    
    # Seed test data
    print("🌱 Seeding test data...")
    client.seed_test_data()
    
    # Get active riders
    riders = client.get_active_riders()
    print(f"\n📋 Active riders:")
    for rider in riders:
        print(f"  - {rider['name']} ({rider['phone']})")
    
    # Get all deliveries
    deliveries = client.get_deliveries()
    print(f"\n📦 Total deliveries: {len(deliveries)}")
    for delivery in deliveries[:3]:  # Show first 3
        print(f"  - {delivery['delivery_id']}: {delivery['customer_name']} - {delivery['status']}")
    
    # Test creating a delivery
    print("\n📝 Creating a test delivery...")
    new_delivery = client.create_delivery(
        customer_name="Test Customer",
        customer_phone="0799999999",
        delivery_address="Test Address, Nairobi",
        item_description="Test Item"
    )
    print(f"  ✅ Created: {new_delivery['delivery_id']}")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")