import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self):
        self.subscribers = {}
    
    def notify_status_update(self, delivery):
        """
        Notify all subscribers about a status update.
        For now, just log the update. In production, this would send webhook POSTs.
        """
        logger.info(f"📡 Status update: {delivery.get('delivery_id')} - {delivery.get('status')}")
        logger.info(f"   Customer: {delivery.get('customer_name')}")
        logger.info(f"   Updated at: {delivery.get('updated_at')}")
        
        # Here you would send webhook notifications to all subscribers
        # For now, we'll just log it
        
        return True

# Example usage
if __name__ == "__main__":
    handler = WebhookHandler()
    test_delivery = {
        'delivery_id': 'DEL-001',
        'customer_name': 'Test Customer',
        'status': 'PICKED_UP',
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    handler.notify_status_update(test_delivery)