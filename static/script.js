// Reflex Delivery System - Smart Auto-Refresh

console.log('Reflex Delivery System loaded!');

// Track if user is currently filling a form
let isFormFocused = false;

// Track the last refresh time
let lastRefreshTime = Date.now();

// Function to check if form has unsaved changes
function hasFormChanges() {
    const form = document.getElementById('deliveryForm');
    if (!form) return false;
    
    const inputs = form.querySelectorAll('input, textarea, select');
    for (let input of inputs) {
        if (input.value && input.value.trim() !== '') {
            return true;
        }
    }
    return false;
}

// Function to safely refresh the page
function safeRefresh() {
    // Don't refresh if:
    // 1. User is typing in a form
    // 2. Form has unsaved changes
    // 3. A submission is in progress
    
    const form = document.getElementById('deliveryForm');
    if (form) {
        const isSubmitting = form.dataset.submitting === 'true';
        const hasChanges = hasFormChanges();
        const isFocused = document.activeElement && 
                          document.activeElement.tagName === 'INPUT' || 
                          document.activeElement?.tagName === 'TEXTAREA';
        
        if (isSubmitting || hasChanges || isFocused) {
            console.log('⏳ Skipping refresh - user is interacting with form');
            return;
        }
    }
    
    // Refresh the page
    console.log('🔄 Auto-refreshing...');
    location.reload();
}

// Auto-refresh only for specific pages
function initAutoRefresh() {
    const currentPage = window.location.pathname;
    
    // Only auto-refresh retailer and dispatcher pages
    if (currentPage.includes('retailer') || currentPage.includes('dispatcher')) {
        console.log('⏰ Auto-refresh enabled (every 15 seconds)');
        
        // Refresh every 15 seconds (more reasonable than 10)
        setInterval(safeRefresh, 15000);
    }
}

// Track form interactions
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('deliveryForm');
    if (form) {
        // Mark when user starts typing
        form.querySelectorAll('input, textarea, select').forEach(input => {
            input.addEventListener('focus', function() {
                isFormFocused = true;
            });
            
            input.addEventListener('blur', function() {
                // Wait a moment before clearing focus flag
                setTimeout(() => {
                    // Check if any input still has focus
                    const focused = document.activeElement;
                    if (focused && (focused.tagName === 'INPUT' || focused.tagName === 'TEXTAREA' || focused.tagName === 'SELECT')) {
                        return;
                    }
                    isFormFocused = false;
                }, 500);
            });
            
            input.addEventListener('input', function() {
                // User is typing
                isFormFocused = true;
            });
        });
        
        // Track form submission
        form.addEventListener('submit', function() {
            this.dataset.submitting = 'true';
            console.log('📤 Form submitting...');
        });
        
        // Reset after submission
        form.addEventListener('submit', function() {
            // After 3 seconds, reset the submitting flag
            setTimeout(() => {
                this.dataset.submitting = 'false';
            }, 3000);
        });
    }
});

// Start auto-refresh
initAutoRefresh();

console.log('✅ Reflex system ready!');