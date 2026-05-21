// Main JavaScript for Hospital Triage System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Update clock every second
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('vi-VN', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        });
        const dateString = now.toLocaleDateString('vi-VN', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        // Update navbar clock
        const clockElement = document.getElementById('current-time');
        if (clockElement) {
            clockElement.textContent = timeString;
            clockElement.title = dateString; // Show full date on hover
        }
        
        // Update footer last-updated
        const lastUpdated = document.getElementById('last-updated');
        if (lastUpdated) {
            lastUpdated.textContent = now.toLocaleString('vi-VN');
        }
        
        // Update check-in form time field (if on check-in page)
        const checkinTimeElement = document.getElementById('checkin-time');
        if (checkinTimeElement) {
            checkinTimeElement.value = now.toLocaleString('vi-VN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
    }
    
    // Update immediately and then every second
    updateClock();
    setInterval(updateClock, 1000);

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Form validation enhancement
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Search input debounce
    const searchInputs = document.querySelectorAll('input[type="search"], input[name="search"]');
    searchInputs.forEach(function(input) {
        let timeout = null;
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                // Trigger search if needed
                if (input.value.length >= 3 || input.value.length === 0) {
                    // Auto-submit form after user stops typing
                    const form = input.closest('form');
                    if (form && input.value.length === 0) {
                        form.submit();
                    }
                }
            }, 500);
        });
    });
});

// Utility functions
function showLoading() {
    const overlay = document.createElement('div');
    overlay.className = 'spinner-overlay';
    overlay.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.querySelector('.spinner-overlay');
    if (overlay) {
        overlay.remove();
    }
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    toastContainer.appendChild(toast);
    
    setTimeout(function() {
        toast.remove();
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = 'position: fixed; top: 70px; right: 20px; z-index: 1050; max-width: 300px;';
    document.body.appendChild(container);
    return container;
}

// AJAX utility
function ajaxRequest(url, options = {}) {
    showLoading();
    return fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        ...options
    })
    .then(response => {
        hideLoading();
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .catch(error => {
        hideLoading();
        console.error('AJAX Error:', error);
        showToast('An error occurred. Please try again.', 'danger');
        throw error;
    });
}

// Confirm dialog utility
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Format date
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Format time
function formatTime(dateString) {
    return new Date(dateString).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Real-time updates for dashboard
function startRealtimeUpdates() {
    // Update every 30 seconds
    setInterval(function() {
        fetch('/api/dashboard/status')
            .then(response => response.json())
            .then(data => {
                // Update stats if elements exist
                const elements = {
                    'stat-total-patients': data.stats.total_patients,
                    'stat-active-patients': data.stats.active_patients,
                    'stat-emergency-patients': data.stats.emergency_patients,
                    'stat-available-doctors': data.stats.available_doctors,
                    'stat-busy-doctors': data.stats.busy_doctors,
                    'stat-waiting-queue': data.stats.waiting_queue
                };
                
                Object.keys(elements).forEach(function(id) {
                    const element = document.getElementById(id);
                    if (element) {
                        element.textContent = elements[id];
                    }
                });
                
                // Update last updated time
                const lastUpdated = document.getElementById('last-updated');
                if (lastUpdated) {
                    lastUpdated.textContent = new Date().toLocaleString();
                }
            })
            .catch(error => console.error('Real-time update error:', error));
    }, 30000);
}

// Initialize real-time updates if on dashboard
if (document.getElementById('stats-cards')) {
    startRealtimeUpdates();
}

// Mobile menu toggle enhancement
document.addEventListener('click', function(e) {
    const navbar = document.getElementById('navbarNav');
    const toggler = document.querySelector('.navbar-toggler');
    
    if (navbar && toggler && !navbar.contains(e.target) && !toggler.contains(e.target)) {
        const bsCollapse = bootstrap.Collapse.getInstance(navbar);
        if (bsCollapse) {
            bsCollapse.hide();
        }
    }
});

// Print functionality
function printPage() {
    window.print();
}

// Export table to CSV
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    rows.forEach(function(row) {
        const cols = row.querySelectorAll('td, th');
        const rowData = [];
        
        cols.forEach(function(col) {
            rowData.push(col.textContent.trim());
        });
        
        csv.push(rowData.join(','));
    });
    
    const csvContent = 'data:text/csv;charset=utf-8,' + csv.join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Smooth scroll to element
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Tab persistence
function saveActiveTab(tabId) {
    localStorage.setItem('activeTab', tabId);
}

function restoreActiveTab() {
    const activeTab = localStorage.getItem('activeTab');
    if (activeTab) {
        const tab = document.querySelector(`[data-bs-target="${activeTab}"]`);
        if (tab) {
            const bsTab = new bootstrap.Tab(tab);
            bsTab.show();
        }
    }
}

// Handle page visibility for pausing updates
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden, could pause expensive operations
        console.log('Page hidden - pausing updates');
    } else {
        // Page is visible again, could refresh data
        console.log('Page visible - resuming updates');
    }
});
