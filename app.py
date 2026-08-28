from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from sheets_client import SheetsClient
from webhook_handler import WebhookHandler
import os
from dotenv import load_dotenv
import logging
from functools import wraps
from datetime import timedelta

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Secret key for session cookies. In production, set SECRET_KEY as an env var.
app.secret_key = os.getenv("SECRET_KEY", "dev-only-insecure-key-change-me")

# How long a "Remember me" login lasts before requiring a fresh login.
app.permanent_session_lifetime = timedelta(days=7)

VALID_ROLES = {"retailer", "dispatcher", "rider"}


def login_required(role):
    """Require the visitor to have selected/logged in as the given role
    for this browser session before viewing the page."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if session.get("role") != role:
                return redirect(url_for("login", role=role))
            return f(*args, **kwargs)
        return wrapped
    return decorator

# Initialize Sheets Client
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "service-account-key.json")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

if not SHEET_ID:
    raise ValueError("Please set GOOGLE_SHEET_ID in .env file")

# Create global instances
sheets_client = SheetsClient(CREDENTIALS_FILE, SHEET_ID)
webhook_handler = WebhookHandler()

# Store webhook subscribers (for real-time updates)
subscribers = {}


@app.route('/')
def index():
    """Home dashboard: pick which role you're logging in as."""
    return render_template('home.html')


@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    """Log in as a given role. Riders are validated against the Riders
    sheet; retailer and dispatcher are validated against the Staff sheet."""
    if role not in VALID_ROLES:
        return redirect(url_for('index'))

    if request.method == 'GET':
        return render_template('login.html', role=role)

    user_id = request.form.get('user_id', '').strip()
    remember_me = request.form.get('remember_me') == 'on'

    if not user_id:
        return render_template('login.html', role=role, error="Please enter an ID.")

    if role == 'rider':
        try:
            person = sheets_client.get_rider_by_id(user_id)
        except Exception as e:
            logger.error(f"Error validating rider login: {e}")
            return render_template('login.html', role=role, error="Couldn't verify that ID right now. Try again.")

        if not person:
            return render_template('login.html', role=role, error=f"Rider ID '{user_id}' not found or inactive.")

        identifier = person['rider_id']
        display_name = person['name']

    else:  # retailer or dispatcher
        try:
            person = sheets_client.get_staff_by_id(user_id, role)
        except Exception as e:
            logger.error(f"Error validating staff login: {e}")
            return render_template('login.html', role=role, error="Couldn't verify that ID right now. Try again.")

        if not person:
            return render_template('login.html', role=role, error=f"Staff ID '{user_id}' not found for this role, or inactive.")

        identifier = person['staff_id']
        display_name = person['name']

    session.permanent = remember_me
    session['role'] = role
    session['user_id'] = identifier
    session['user_name'] = display_name
    return redirect(url_for(role))


@app.route('/logout')
def logout():
    """Clear the session and return to the home dashboard."""
    session.clear()
    return redirect(url_for('index'))


@app.route('/retailer')
@login_required('retailer')
def retailer():
    """Load retailer page with their deliveries."""
    try:
        # Get all deliveries (in a real app, filter by retailer)
        deliveries = sheets_client.get_deliveries()
        return render_template('retailer.html', deliveries=deliveries)
    except Exception as e:
        logger.error(f"Error loading retailer page: {e}")
        return render_template('retailer.html', deliveries=[], error=str(e))


@app.route('/delivery', methods=['POST'])
def create_delivery():
    """Create a new delivery from retailer form."""
    try:
        data = request.get_json() or request.form
        
        # Extract fields
        customer_name = data.get('customer_name', '').strip()
        customer_phone = data.get('customer_phone', '').strip()
        delivery_address = data.get('delivery_address', '').strip()
        item_description = data.get('item_description', '').strip()
        
        # Validate required fields
        if not all([customer_name, customer_phone, delivery_address, item_description]):
            return jsonify({
                'success': False,
                'error': 'All fields are required'
            }), 400
        
        # Create delivery
        delivery = sheets_client.create_delivery(
            customer_name=customer_name,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            item_description=item_description
        )
        
        # Notify all subscribers
        webhook_handler.notify_status_update(delivery)
        
        return jsonify({
            'success': True,
            'delivery': delivery
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating delivery: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/dispatcher')
@login_required('dispatcher')
def dispatcher():
    """Load dispatcher page with pending deliveries."""
    try:
        # Get pending deliveries
        pending = sheets_client.get_deliveries(status='PENDING')
        
        # Get all deliveries (for overview)
        all_deliveries = sheets_client.get_deliveries()
        
        # Get active riders
        riders = sheets_client.get_active_riders()
        
        return render_template('dispatcher.html', 
                             pending=pending,
                             all_deliveries=all_deliveries,
                             riders=riders)
    except Exception as e:
        logger.error(f"Error loading dispatcher page: {e}")
        return render_template('dispatcher.html', 
                             pending=[], 
                             all_deliveries=[],
                             riders=[],
                             error=str(e))


@app.route('/assign', methods=['POST'])
def assign_delivery():
    """Assign a rider to a delivery."""
    try:
        data = request.get_json() or request.form
        
        delivery_id = data.get('delivery_id', '').strip()
        rider_name = data.get('rider_name', '').strip()
        
        if not delivery_id or not rider_name:
            return jsonify({
                'success': False,
                'error': 'Delivery ID and rider name are required'
            }), 400
        
        # Update delivery status to ASSIGNED
        updated_delivery = sheets_client.update_delivery_status(
            delivery_id=delivery_id,
            new_status='ASSIGNED',
            rider_name=rider_name
        )
        
        # Notify all subscribers
        webhook_handler.notify_status_update(updated_delivery)
        
        return jsonify({
            'success': True,
            'delivery': updated_delivery
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning delivery: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/rider')
@login_required('rider')
def rider():
    """Load rider page with their deliveries."""
    try:
        rider_name = session.get('user_name', '')
        deliveries = sheets_client.get_deliveries(rider=rider_name)
        return render_template('rider.html', deliveries=deliveries, rider_name=rider_name)
    except Exception as e:
        logger.error(f"Error loading rider page: {e}")
        return render_template('rider.html', deliveries=[], error=str(e))


@app.route('/status', methods=['POST'])
def update_status():
    """Update delivery status (PICKED_UP or DELIVERED)."""
    try:
        data = request.get_json() or request.form
        
        delivery_id = data.get('delivery_id', '').strip()
        new_status = data.get('status', '').strip()
        
        if not delivery_id or not new_status:
            return jsonify({
                'success': False,
                'error': 'Delivery ID and status are required'
            }), 400
        
        # Validate status
        if new_status not in ['PICKED_UP', 'DELIVERED', 'CONFIRMED']:
            return jsonify({
                'success': False,
                'error': 'Invalid status. Must be PICKED_UP, DELIVERED, or CONFIRMED'
            }), 400
        
        # Update delivery status
        updated_delivery = sheets_client.update_delivery_status(
            delivery_id=delivery_id,
            new_status=new_status
        )
        
        # Notify all subscribers
        webhook_handler.notify_status_update(updated_delivery)
        
        return jsonify({
            'success': True,
            'delivery': updated_delivery
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/webhook/status-update', methods=['POST'])
def webhook_status_update():
    """Receive status update notifications."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Broadcast to all subscribers
        delivery = data.get('delivery', {})
        webhook_handler.notify_status_update(delivery)
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/deliveries')
def api_deliveries():
    """API endpoint to get all deliveries (for AJAX refresh)."""
    try:
        deliveries = sheets_client.get_deliveries()
        return jsonify({
            'success': True,
            'deliveries': deliveries
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/pending')
def api_pending():
    """API endpoint to get pending deliveries (for dispatcher)."""
    try:
        pending = sheets_client.get_deliveries(status='PENDING')
        return jsonify({
            'success': True,
            'deliveries': pending
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/my-deliveries')
def api_my_deliveries():
    """API endpoint to get a rider's deliveries."""
    try:
        rider_name = request.args.get('rider', '')
        if not rider_name:
            return jsonify({
                'success': False,
                'error': 'Rider name required'
            }), 400
        
        deliveries = sheets_client.get_deliveries(rider=rider_name)
        return jsonify({
            'success': True,
            'deliveries': deliveries
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)