import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Nairobi is UTC+3 year-round (no daylight saving), so this is safe to hardcode
NAIROBI_TZ = timezone(timedelta(hours=3))


def nairobi_now():
    """Return the current time in Nairobi (EAT), regardless of the server's
    own timezone. Render runs in UTC by default, so datetime.now() alone
    would silently drift depending on where the code is deployed."""
    return datetime.now(NAIROBI_TZ)

class SheetsClient:
    def __init__(self, credentials_file, sheet_id):
        """
        Initialize the Google Sheets client with retry capabilities.
        
        Args:
            credentials_file: Path to service account JSON file
            sheet_id: Google Sheet ID from URL
        """
        self.sheet_id = sheet_id
        self.client = None
        self.deliveries_sheet = None
        self.riders_sheet = None
        
        # Retry configuration
        self.max_retries = 4
        self.base_delay = 1  # seconds
        
        self._authenticate(credentials_file)
        self._initialize_sheets()
    
    def _authenticate(self, credentials_file):
        """Authenticate with Google Sheets API with retry."""
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']

        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

        retries = 0
        while retries < self.max_retries:
            try:
                if creds_json:
                    # Production (Render): credentials passed as an env var
                    creds_dict = json.loads(creds_json)
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(
                        creds_dict, scope
                    )
                else:
                    # Local dev: credentials read from a file on disk
                    creds = ServiceAccountCredentials.from_json_keyfile_name(
                        credentials_file, scope
                    )
                self.client = gspread.authorize(creds)
                logger.info("✅ Successfully authenticated with Google Sheets")
                return
            except Exception as e:
                retries += 1
                wait_time = self.base_delay * (2 ** retries)
                logger.warning(f"⚠️ Auth failed (attempt {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    logger.info(f"⏳ Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to authenticate after {self.max_retries} attempts: {e}")
    
    def _initialize_sheets(self):
        """Initialize worksheet references with retry."""
        retries = 0
        while retries < self.max_retries:
            try:
                sheet = self.client.open_by_key(self.sheet_id)
                
                # Get or create Deliveries tab
                try:
                    self.deliveries_sheet = sheet.worksheet("Deliveries")
                except gspread.WorksheetNotFound:
                    self.deliveries_sheet = sheet.add_worksheet(
                        title="Deliveries", rows=1000, cols=20
                    )
                    self._setup_deliveries_headers()
                
                # Get or create Riders tab
                try:
                    self.riders_sheet = sheet.worksheet("Riders")
                except gspread.WorksheetNotFound:
                    self.riders_sheet = sheet.add_worksheet(
                        title="Riders", rows=100, cols=10
                    )
                    self._setup_riders_headers()
                
                logger.info("✅ Successfully initialized worksheets")
                return
            except Exception as e:
                retries += 1
                wait_time = self.base_delay * (2 ** retries)
                logger.warning(f"⚠️ Sheet init failed (attempt {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    logger.info(f"⏳ Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to initialize sheets after {self.max_retries} attempts: {e}")
    
    def _setup_deliveries_headers(self):
        """Set up headers for Deliveries sheet with retry."""
        headers = [
            "delivery_id", "customer_name", "customer_phone", 
            "delivery_address", "item_description", "status",
            "assigned_rider", "created_at", "updated_at", "confirmed_at"
        ]
        retries = 0
        while retries < self.max_retries:
            try:
                self.deliveries_sheet.append_row(headers)
                logger.info("✅ Set up Deliveries headers")
                return
            except Exception as e:
                retries += 1
                wait_time = self.base_delay * (2 ** retries)
                logger.warning(f"⚠️ Headers setup failed (attempt {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to set up headers: {e}")
    
    def _setup_riders_headers(self):
        """Set up headers for Riders sheet with retry."""
        headers = ["rider_id", "name", "phone", "active"]
        retries = 0
        while retries < self.max_retries:
            try:
                self.riders_sheet.append_row(headers)
                logger.info("✅ Set up Riders headers")
                return
            except Exception as e:
                retries += 1
                wait_time = self.base_delay * (2 ** retries)
                logger.warning(f"⚠️ Riders headers setup failed (attempt {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to set up riders headers: {e}")
    
    def create_delivery(self, customer_name, customer_phone, delivery_address, item_description):
        """
        Create a new delivery with retry.
        
        Returns:
            dict: The created delivery data
        """
        delivery_id = f"DEL-{nairobi_now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
        now = nairobi_now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            delivery_id,
            customer_name,
            customer_phone,
            delivery_address,
            item_description,
            "PENDING",  # Initial status
            "",  # assigned_rider
            now,  # created_at
            now,  # updated_at
            ""  # confirmed_at
        ]
        
        retries = 0
        while retries < self.max_retries:
            try:
                self.deliveries_sheet.append_row(row)
                logger.info(f"✅ Created delivery {delivery_id} for {customer_name}")
                
                # Return the created delivery
                return {
                    "delivery_id": delivery_id,
                    "customer_name": customer_name,
                    "customer_phone": customer_phone,
                    "delivery_address": delivery_address,
                    "item_description": item_description,
                    "status": "PENDING",
                    "assigned_rider": "",
                    "created_at": now,
                    "updated_at": now,
                    "confirmed_at": ""
                }
            except Exception as e:
                retries += 1
                wait_time = self.base_delay * (2 ** retries)
                logger.warning(f"⚠️ Create delivery failed (attempt {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to create delivery: {e}")
    
    def get_deliveries(self, status=None, rider=None):
        """
        Get deliveries with optional filters (with retry).
        Includes auto-correction: if rider is assigned but status is PENDING, 
        automatically correct to ASSIGNED.
        
        Args:
            status: Filter by status (PENDING, ASSIGNED, PICKED_UP, DELIVERED, CONFIRMED)
            rider: Filter by assigned rider name
        
        Returns:
            list: List of delivery dictionaries
        """
        retries = 0
        while retries < self.max_retries:
            try:
                records = self.deliveries_sheet.get_all_records()
                deliveries = []
                
                for idx, record in enumerate(records, start=2):  # start=2 because row 1 is headers
                    # Skip empty rows
                    if not record.get("delivery_id"):
                        continue
                    
                    # Get values from the record
                    actual_status = record.get("status", "PENDING")
                    assigned_rider = record.get("assigned_rider", "").strip()
                    
                    # 🔥 AUTO-CORRECT: If rider is assigned but status is PENDING, change to ASSIGNED
                    if assigned_rider and actual_status == "PENDING":
                        actual_status = "ASSIGNED"
                        # Update the sheet to fix it permanently
                        try:
                            cell = self.deliveries_sheet.find(record.get("delivery_id"))
                            if cell:
                                self.deliveries_sheet.update_cell(cell.row, 6, "ASSIGNED")  # Column F is status
                                # Also update the updated_at timestamp
                                now = nairobi_now().strftime("%Y-%m-%d %H:%M:%S")
                                self.deliveries_sheet.update_cell(cell.row, 9, now)  # Column I is updated_at
                                logger.info(f"🔧 Auto-corrected {record.get('delivery_id')} from PENDING to ASSIGNED")
                        except Exception as e:
                            logger.warning(f"Could not auto-correct status for {record.get('delivery_id')}: {e}")
                    
                    delivery = {
                        "row_index": idx,
                        "delivery_id": record.get("delivery_id", ""),
                        "customer_name": record.get("customer_name", ""),
                        "customer_phone": record.get("customer_phone", ""),
                        "delivery_address": record.get("delivery_address", ""),
                        "item_description": record.get("item_description", ""),
                        "status": actual_status,  # Use the corrected status
                        "assigned_rider": assigned_rider,
                        "created_at": record.get("created_at", ""),
                        "updated_at": record.get("updated_at", ""),
                        "confirmed_at": record.get("confirmed_at", "")
                    }
                    
                    # Apply filters
                    if status and delivery["status"] != status:
                        continue
                    if rider and delivery["assigned_rider"] != rider:
                        continue
                    
                    deliveries.append(delivery)
                
                logger.info(f"✅ Retrieved {len(deliveries)} deliveries (filter: status={status}, rider={rider})")
                return deliveries
                
            except Exception as e:
                retries += 1
                wait_time = self.base_delay * (2 ** retries)
                logger.warning(f"⚠️ Get deliveries failed (attempt {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to get deliveries: {e}")
    
    def update_delivery_status(self, delivery_id, new_status, rider_name=None):
        """
        Update a delivery's status with validation (with retry).
        
        Args:
            delivery_id: The delivery ID to update
            new_status: New status (ASSIGNED, PICKED_UP, DELIVERED, CONFIRMED)
            rider_name: Optional - the rider assigned (required for ASSIGNED)
        
        Returns:
            dict: Updated delivery data
        """
        # Validate status flow
        valid_statuses = ["PENDING", "ASSIGNED", "PICKED_UP", "DELIVERED", "CONFIRMED"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}")
        
        if new_status == "ASSIGNED" and not rider_name:
            raise ValueError("Rider name required when assigning")
        
        retries = 0
        while retries < self.max_retries:
            try:
                # Find the delivery
                cell = self.deliveries_sheet.find(delivery_id)
                if not cell:
                    raise ValueError(f"Delivery {delivery_id} not found")
                
                row = cell.row
                status_col = 6  # F column (1-indexed)
                rider_col = 7   # G column
                updated_at_col = 9  # I column
                confirmed_at_col = 10  # J column
                
                # Get current status
                current_status = self.deliveries_sheet.cell(row, status_col).value
                logger.info(f"📋 Current status for {delivery_id}: {current_status}")
                
                # Validate status transition
                status_order = ["PENDING", "ASSIGNED", "PICKED_UP", "DELIVERED", "CONFIRMED"]
                
                # If current status is None or empty, treat as PENDING
                if not current_status:
                    current_status = "PENDING"
                
                # Check if the transition is valid
                current_index = status_order.index(current_status)
                new_index = status_order.index(new_status)
                
                if new_index <= current_index:
                    raise ValueError(
                        f"Cannot go back from {current_status} to {new_status}. "
                        f"Status flow: PENDING → ASSIGNED → PICKED_UP → DELIVERED → CONFIRMED"
                    )
                
                # Update status
                now = nairobi_now().strftime("%Y-%m-%d %H:%M:%S")
                updates = [
                    (row, status_col, new_status),
                    (row, updated_at_col, now)
                ]
                
                # Update rider if assigning
                if new_status == "ASSIGNED" and rider_name:
                    updates.append((row, rider_col, rider_name))
                
                # Set confirmed_at if confirming
                if new_status == "CONFIRMED":
                    updates.append((row, confirmed_at_col, now))
                
                # Apply updates
                for row_num, col_num, value in updates:
                    self.deliveries_sheet.update_cell(row_num, col_num, value)
                
                logger.info(f"✅ Updated delivery {delivery_id} to {new_status}")
                
                # Return the updated delivery
                updated_delivery = self.get_delivery_by_id(delivery_id)
                return updated_delivery
                
            except Exception as e:
                retries += 1
                wait_time = self.base_delay * (2 ** retries)
                logger.warning(f"⚠️ Update status failed (attempt {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to update delivery status: {e}")
    
    def get_delivery_by_id(self, delivery_id):
        """Get a single delivery by ID (with retry)."""
        retries = 0
        while retries < self.max_retries:
            try:
                cell = self.deliveries_sheet.find(delivery_id)
                if not cell:
                    return None
                
                row_data = self.deliveries_sheet.row_values(cell.row)
                headers = self.deliveries_sheet.row_values(1)
                
                delivery = {}
                for idx, header in enumerate(headers):
                    if idx < len(row_data):
                        delivery[header] = row_data[idx]
                    else:
                        delivery[header] = ""
                
                delivery["row_index"] = cell.row
                
                # Auto-correct: if rider assigned but status is PENDING, correct it
                assigned_rider = delivery.get("assigned_rider", "").strip()
                if assigned_rider and delivery.get("status") == "PENDING":
                    delivery["status"] = "ASSIGNED"
                    # Update the sheet
                    try:
                        self.deliveries_sheet.update_cell(cell.row, 6, "ASSIGNED")
                        logger.info(f"🔧 Auto-corrected {delivery_id} from PENDING to ASSIGNED")
                    except Exception as e:
                        logger.warning(f"Could not auto-correct status: {e}")
                
                return delivery
                
            except Exception as e:
                retries += 1
                wait_time = self.base_delay * (2 ** retries)
                logger.warning(f"⚠️ Get delivery failed (attempt {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to get delivery: {e}")
    
    def get_active_riders(self):
        """Get all active riders (with retry)."""
        retries = 0
        while retries < self.max_retries:
            try:
                records = self.riders_sheet.get_all_records()
                riders = []
                
                for record in records:
                    if record.get("active", "").upper() == "TRUE":
                        riders.append({
                            "rider_id": record.get("rider_id", ""),
                            "name": record.get("name", ""),
                            "phone": record.get("phone", ""),
                            "active": record.get("active", "")
                        })
                
                logger.info(f"✅ Retrieved {len(riders)} active riders")
                return riders
                
            except Exception as e:
                retries += 1
                wait_time = self.base_delay * (2 ** retries)
                logger.warning(f"⚠️ Get riders failed (attempt {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to get riders: {e}")
    
    def seed_test_data(self):
        """Seed test data for the demo."""
        # Check if riders already exist
        try:
            existing = self.riders_sheet.get_all_records()
            if existing:
                logger.info("📋 Riders already exist, skipping seed")
                return
        except:
            pass
        
        # Add test riders
        test_riders = [
            ("R001", "James Mwangi", "0712345678", "TRUE"),
            ("R002", "Sarah Wanjiru", "0723456789", "TRUE"),
            ("R003", "David Ochieng", "0734567890", "TRUE"),
            ("R004", "Faith Atieno", "0745678901", "TRUE"),
            ("R005", "Brian Omondi", "0756789012", "TRUE"),
        ]
        
        for rider in test_riders:
            try:
                self.riders_sheet.append_row(rider)
                logger.info(f"✅ Added test rider: {rider[1]}")
            except Exception as e:
                logger.warning(f"⚠️ Could not add rider {rider[1]}: {e}")
        
        # Add test deliveries
        test_deliveries = [
            ("Grace Achieng", "0712345678", "Westlands, Nairobi", "Samsung TV 43 inch"),
            ("Peter Odhiambo", "0723456789", "Kileleshwa, Nairobi", "Laptop HP Elitebook"),
            ("Mary Muthoni", "0734567890", "Langata, Nairobi", "Groceries - 5kg rice, 2kg sugar"),
            ("John Kamau", "0745678901", "Karen, Nairobi", "Furniture - 3 seater sofa"),
        ]
        
        for delivery in test_deliveries:
            try:
                self.create_delivery(*delivery)
            except Exception as e:
                logger.warning(f"⚠️ Could not add test delivery: {e}")

# Example usage
if __name__ == "__main__":
    # Test the client
    # Replace these with your actual credentials
    CREDENTIALS_FILE = "service-account-key.json"
    SHEET_ID = "your-google-sheet-id"
    
    client = SheetsClient(CREDENTIALS_FILE, SHEET_ID)
    
    # Get active riders
    riders = client.get_active_riders()
    print(f"Active riders: {riders}")
    
    # Get all deliveries
    deliveries = client.get_deliveries()
    print(f"Total deliveries: {len(deliveries)}")