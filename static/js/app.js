/**
 * Valhalla Agency OS - Application JavaScript
 */

// Global application object
const ValhallaApp = {

    // Initialize the application
    init: function() {
        this.setupEventListeners();
        this.initializeComponents();
        this.setupHTMXEvents();
        console.log('Valhalla Agency OS initialized');
    },

    // Setup global event listeners
    setupEventListeners: function() {
        // Auto-dismiss alerts after 5 seconds
        setTimeout(() => {
            const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
            alerts.forEach(alert => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);

        // Confirm delete actions
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-confirm]')) {
                const message = e.target.getAttribute('data-confirm');
                if (!confirm(message)) {
                    e.preventDefault();
                    return false;
                }
            }
        });

        // Auto-focus search inputs
        const searchInputs = document.querySelectorAll('input[name="q"]');
        if (searchInputs.length > 0) {
            searchInputs[0].focus();
        }
    },

    // Initialize UI components
    initializeComponents: function() {
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

        // Initialize date inputs with today's date as max
        const dateInputs = document.querySelectorAll('input[type="date"]');
        dateInputs.forEach(input => {
            if (!input.value && input.name === 'due_date') {
                // Set default due date to 7 days from now
                const nextWeek = new Date();
                nextWeek.setDate(nextWeek.getDate() + 7);
                input.value = nextWeek.toISOString().split('T')[0];
            }
        });
    },

    // Setup HTMX event handlers
    setupHTMXEvents: function() {
        document.addEventListener('htmx:afterRequest', (e) => {
            // Reinitialize Feather icons after HTMX requests
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
        });

        document.addEventListener('htmx:responseError', (e) => {
            console.error('HTMX Error:', e.detail);
            this.showAlert('An error occurred while processing your request.', 'danger');
        });

        document.addEventListener('htmx:sendError', (e) => {
            console.error('HTMX Send Error:', e.detail);
            this.showAlert('Network error. Please check your connection.', 'danger');
        });
    },

    // Utility function to show alerts
    showAlert: function(message, type = 'info') {
        const alertContainer = document.querySelector('.container');
        if (!alertContainer) return;

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        alertContainer.insertBefore(alertDiv, alertContainer.firstChild);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    },

    // Form utilities
    forms: {
        // Submit form with loading state
        submitWithLoading: function(form, buttonSelector = 'button[type="submit"]') {
            const button = form.querySelector(buttonSelector);
            if (!button) return;

            const originalText = button.innerHTML;
            button.innerHTML = '<i data-feather="loader" class="me-2"></i>Saving...';
            button.disabled = true;

            // Re-enable after 10 seconds as fallback
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
                if (typeof feather !== 'undefined') {
                    feather.replace();
                }
            }, 10000);
        },

        // Validate form before submission
        validate: function(form) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });

            return isValid;
        }
    },

    // Contact search functionality
    contacts: {
        search: function(query, callback) {
            if (query.length < 2) {
                callback([]);
                return;
            }

            fetch(`/contacts/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(contacts => callback(contacts))
                .catch(error => {
                    console.error('Contact search error:', error);
                    callback([]);
                });
        },

        // Add contact to selection
        addToSelection: function(contact, containerId) {
            const container = document.getElementById(containerId);
            if (!container) return;

            const contactTag = document.createElement('span');
            contactTag.className = 'badge bg-secondary me-2 mb-2';
            contactTag.innerHTML = `
                ${contact.name}
                <button type="button" class="btn-close btn-close-white ms-2" 
                        onclick="ValhallaApp.contacts.removeFromSelection(this)"></button>
                <input type="hidden" name="contacts" value="${contact.id}">
            `;

            container.appendChild(contactTag);
        },

        // Remove contact from selection
        removeFromSelection: function(button) {
            button.closest('.badge').remove();
        }
    },

    // Ticket management
    tickets: {
        // Update status with HTMX
        updateStatus: function(ticketId, newStatus) {
            const formData = new FormData();
            formData.append('status', newStatus);

            fetch(`/service/tickets/${ticketId}/status`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    ValhallaApp.showAlert('Failed to update status', 'danger');
                }
            })
            .catch(error => {
                console.error('Status update error:', error);
                ValhallaApp.showAlert('Error updating status', 'danger');
            });
        },

        // Get CSRF token from meta tag or form
        getCSRFToken: function() {
            const token = document.querySelector('meta[name="csrf-token"]');
            if (token) return token.getAttribute('content');

            const hiddenInput = document.querySelector('input[name="csrf_token"]');
            if (hiddenInput) return hiddenInput.value;

            return '';
        }
    },

    // Data tables functionality
    dataTables: {
        // Initialize sortable tables
        init: function() {
            const tables = document.querySelectorAll('.data-table');
            tables.forEach(table => {
                this.makeSortable(table);
            });
        },

        // Make table sortable
        makeSortable: function(table) {
            const headers = table.querySelectorAll('th[data-sortable]');
            headers.forEach(header => {
                header.style.cursor = 'pointer';
                header.addEventListener('click', () => {
                    this.sortTable(table, header);
                });
            });
        },

        // Sort table by column
        sortTable: function(table, header) {
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const columnIndex = Array.from(header.parentNode.children).indexOf(header);
            const currentOrder = header.dataset.order || 'asc';
            const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';

            rows.sort((a, b) => {
                const aVal = a.children[columnIndex].textContent.trim();
                const bVal = b.children[columnIndex].textContent.trim();

                if (newOrder === 'asc') {
                    return aVal.localeCompare(bVal, undefined, { numeric: true });
                } else {
                    return bVal.localeCompare(aVal, undefined, { numeric: true });
                }
            });

            // Update header indicators
            table.querySelectorAll('th').forEach(th => {
                th.removeAttribute('data-order');
                th.classList.remove('sorted-asc', 'sorted-desc');
            });

            header.dataset.order = newOrder;
            header.classList.add(`sorted-${newOrder}`);

            // Reorder rows
            rows.forEach(row => tbody.appendChild(row));
        }
    },

    // Utility functions
    utils: {
        // Format date for display
        formatDate: function(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        },

        // Format currency
        formatCurrency: function(amount) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            }).format(amount);
        },

        // Debounce function
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        // Copy text to clipboard
        copyToClipboard: function(text) {
            navigator.clipboard.writeText(text).then(() => {
                ValhallaApp.showAlert('Copied to clipboard', 'success');
            }).catch(err => {
                console.error('Copy failed:', err);
                ValhallaApp.showAlert('Failed to copy', 'danger');
            });
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    ValhallaApp.init();
});

// Export for global access
window.ValhallaApp = ValhallaApp;

// Specific form handlers
document.addEventListener('DOMContentLoaded', function() {
    // Client type change handler for service tickets
    const clientTypeSelect = document.getElementById('client_type');
    if (clientTypeSelect) {
        clientTypeSelect.addEventListener('change', function() {
            updateClientOptions();
        });
    }

    // Form submission with loading states
    const forms = document.querySelectorAll('form[data-loading]');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            ValhallaApp.forms.submitWithLoading(form);
        });
    });

    // Contact search debounced
    const contactSearchInputs = document.querySelectorAll('input[data-contact-search]');
    contactSearchInputs.forEach(input => {
        const debouncedSearch = ValhallaApp.utils.debounce((query) => {
            ValhallaApp.contacts.search(query, (contacts) => {
                displayContactResults(contacts, input);
            });
        }, 300);

        input.addEventListener('input', function() {
            debouncedSearch(this.value);
        });
    });
});

// Global functions for template usage
function updateClientOptions() {
    const clientType = document.getElementById('client_type').value;
    const clientSelect = document.getElementById('client_id');

    if (!clientType) {
        clientSelect.innerHTML = '<option value="">Select client type first</option>';
        return;
    }

    clientSelect.innerHTML = '<option value="">Loading...</option>';

    fetch(`/service/api/clients?type=${clientType}`)
        .then(response => response.json())
        .then(clients => {
            clientSelect.innerHTML = '<option value="">Select client...</option>';
            clients.forEach(client => {
                const option = document.createElement('option');
                option.value = client.id;
                option.textContent = client.name;
                clientSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error fetching clients:', error);
            clientSelect.innerHTML = '<option value="">Error loading clients</option>';
        });
}

function displayContactResults(contacts, input) {
    let resultsContainer = document.getElementById('contactResults');
    if (!resultsContainer) {
        resultsContainer = document.createElement('div');
        resultsContainer.id = 'contactResults';
        resultsContainer.className = 'contact-search-results mt-2';
        input.parentNode.appendChild(resultsContainer);
    }

    resultsContainer.innerHTML = '';

    if (contacts.length === 0) {
        resultsContainer.innerHTML = '<div class="text-muted">No contacts found</div>';
        return;
    }

    contacts.forEach(contact => {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'contact-search-result';
        resultDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${contact.name}</strong>
                    ${contact.title ? `<br><small class="text-muted">${contact.title}</small>` : ''}
                    ${contact.email ? `<br><small class="text-muted">${contact.email}</small>` : ''}
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary" 
                        onclick="ValhallaApp.contacts.addToSelection(${JSON.stringify(contact).replace(/"/g, '&quot;')}, 'selectedContacts')">
                    Add
                </button>
            </div>
        `;
        resultsContainer.appendChild(resultDiv);
    });
}

// Error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
    // Don't show alerts for every JS error in production
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        ValhallaApp.showAlert('A JavaScript error occurred. Check console for details.', 'warning');
    }
});

// Coming soon alerts
function showComingSoon() {
    alert('This feature is coming soon!');
}

function initiateWorkflow() {
    showComingSoon();
}

function showOnboardingWorkflow() {
    showComingSoon();
}

function showOffboardingWorkflow() {
    showComingSoon();
}

// Add opportunity note functionality
function addOpportunityNote() {
    loadOpportunities();
    const modal = new bootstrap.Modal(document.getElementById('opportunityNoteModal'));
    modal.show();
}

function addClientNote() {
    alert('Client note functionality coming soon!');
}

function loadOpportunities() {
    fetch('/api/deals/active')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('opportunitySelect');
            select.innerHTML = '<option value="">Select an opportunity...</option>';

            if (Array.isArray(data) && data.length > 0) {
                data.forEach(deal => {
                    const option = document.createElement('option');
                    option.value = deal.id;
                    option.textContent = `${deal.name} - ${deal.client_name}`;
                    option.dataset.client = deal.client_name;
                    option.dataset.stage = deal.stage_name;
                    option.dataset.owner = deal.owner_name;
                    select.appendChild(option);
                });
            } else {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'No opportunities available';
                select.appendChild(option);
            }
        })
        .catch(error => {
            console.error('Error loading opportunities:', error);
            const select = document.getElementById('opportunitySelect');
            select.innerHTML = '<option value="">Error loading opportunities</option>';
        });
}

document.addEventListener('DOMContentLoaded', function() {
    // Set up CSRF token for AJAX requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    if (csrfToken) {
        // Set up jQuery AJAX defaults if jQuery is available
        if (typeof $ !== 'undefined') {
            $.ajaxSetup({
                beforeSend: function(xhr, settings) {
                    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                        xhr.setRequestHeader("X-CSRFToken", csrfToken.getAttribute('content'));
                    }
                }
            });
        }

        // Set up fetch defaults
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            if (options.method && !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(options.method.toUpperCase())) {
                options.headers = options.headers || {};
                options.headers['X-CSRFToken'] = csrfToken.getAttribute('content');
            }
            return originalFetch(url, options);
        };
    }

    const opportunitySelect = document.getElementById('opportunitySelect');
    if (opportunitySelect) {
        opportunitySelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const detailsDiv = document.getElementById('opportunityDetails');

            if (this.value && selectedOption.dataset.client) {
                document.getElementById('selectedOpportunityClient').textContent = selectedOption.dataset.client;
                document.getElementById('selectedOpportunityStage').textContent = selectedOption.dataset.stage;
                document.getElementById('selectedOpportunityOwner').textContent = selectedOption.dataset.owner;
                detailsDiv.style.display = 'block';
            } else {
                detailsDiv.style.display = 'none';
            }
        });
    }
});

function saveOpportunityNote() {
    const dealId = document.getElementById('opportunitySelect').value;
    const note = document.getElementById('opportunityNote').value;

    if (!dealId || !note) {
        alert('Please select an opportunity and enter a note.');
        return;
    }

    fetch('/api/deals/' + dealId + '/notes', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name=csrf-token]').getAttribute('content')
        },
        body: JSON.stringify({
            body: note
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            alert('Opportunity note saved successfully!');
            document.getElementById('opportunitySelect').value = '';
            document.getElementById('opportunityNote').value = '';
            document.getElementById('opportunityDetails').style.display = 'none';
            bootstrap.Modal.getInstance(document.getElementById('opportunityNoteModal')).hide();
        } else {
            alert('Error saving note: ' + result.message);
        }
    })
    .catch(error => {
        console.error('Error saving note:', error);
        alert('Error saving note. Please try again.');
    });
}