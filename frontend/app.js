/**
 * Vendor Payment Management System
 * Frontend Application Logic
 */

const API_BASE_URL = 'http://127.0.0.1:8000';

// DOM Elements
const vendorForm = document.getElementById('vendor-form');
const vendorIdInput = document.getElementById('vendor-id');
const vendorNameInput = document.getElementById('vendor-name');
const vendorEmailInput = document.getElementById('vendor-email');
const vendorPhoneInput = document.getElementById('vendor-phone');
const vendorTableBody = document.getElementById('vendor-table-body');
const alertContainer = document.getElementById('alert-container');

// Buttons & Typography
const btnSubmit = document.getElementById('btn-submit');
const btnUpdate = document.getElementById('btn-update');
const btnClear = document.getElementById('btn-clear');
const formTitle = document.getElementById('form-title');

// Initialize the application
document.addEventListener('DOMContentLoaded', fetchVendors);

// Event Listeners
vendorForm.addEventListener('submit', handleFormSubmit);
btnClear.addEventListener('click', resetForm);
btnUpdate.addEventListener('click', handleFormSubmit); // Update button functions as submit

/**
 * Fetch all vendors from the API (GET)
 */
async function fetchVendors() {
    try {
        const response = await fetch(`${API_BASE_URL}/vendors`);
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        const vendors = await response.json();
        renderVendorTable(vendors);
    } catch (error) {
        console.error('Error fetching vendors:', error);
        vendorTableBody.innerHTML = `<tr><td colspan="5" class="empty-state">Failed to connect to backend. Make sure the FastAPI server is running on port 8000.</td></tr>`;
    }
}

/**
 * Render vendors into the HTML table
 * @param {Array} vendors - List of vendor objects
 */
function renderVendorTable(vendors) {
    vendorTableBody.innerHTML = '';
    
    if (vendors.length === 0) {
        vendorTableBody.innerHTML = `<tr><td colspan="5" class="empty-state">No vendors found. Add a new vendor to get started!</td></tr>`;
        return;
    }
    
    vendors.forEach(vendor => {
        const tr = document.createElement('tr');
        
        // Use vendor.id if available, fallback for safety
        const id = vendor.id || vendor.vendor_id || '-';
        
        tr.innerHTML = `
            <td>#${id}</td>
            <td style="font-weight: 500;">${vendor.name}</td>
            <td>${vendor.email}</td>
            <td>${vendor.phone}</td>
            <td class="actions-cell">
                <button class="btn-icon edit" onclick="editVendor('${id}', '${vendor.name}', '${vendor.email}', '${vendor.phone}')" title="Edit Vendor">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-icon delete" onclick="deleteVendor('${id}')" title="Delete Vendor">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        vendorTableBody.appendChild(tr);
    });
}

/**
 * Handle Add/Update form submission
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    
    // Validate form
    if (!vendorForm.checkValidity()) {
        vendorForm.reportValidity();
        return;
    }
    
    const vendorData = {
        name: vendorNameInput.value.trim(),
        email: vendorEmailInput.value.trim(),
        phone: vendorPhoneInput.value.trim()
    };
    
    const vendorId = vendorIdInput.value;
    
    if (vendorId) {
        // If ID exists, it's an update
        await updateVendor(vendorId, vendorData);
    } else {
        // No ID, add new vendor
        await addVendor(vendorData);
    }
}

/**
 * Add a new vendor via API (POST)
 * @param {Object} vendorData - The new vendor details
 */
async function addVendor(vendorData) {
    try {
        const response = await fetch(`${API_BASE_URL}/vendors`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(vendorData)
        });
        
        if (!response.ok) throw new Error('Failed to add vendor');
        
        showAlert('Vendor added successfully!', 'success');
        resetForm();
        fetchVendors(); // Refresh table
    } catch (error) {
        console.error('Error adding vendor:', error);
        showAlert('Failed to add vendor.', 'error');
    }
}

/**
 * Update an existing vendor via API (PUT)
 * @param {string} id - Vendor ID
 * @param {Object} vendorData - Updated vendor details
 */
async function updateVendor(id, vendorData) {
    try {
        const response = await fetch(`${API_BASE_URL}/vendors/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(vendorData)
        });
        
        if (!response.ok) throw new Error('Failed to update vendor');
        
        showAlert('Vendor updated successfully!', 'success');
        resetForm();
        fetchVendors(); // Refresh table
    } catch (error) {
        console.error('Error updating vendor:', error);
        showAlert('Failed to update vendor.', 'error');
    }
}

/**
 * Delete a vendor via API (DELETE)
 * @param {string} id - Vendor ID
 */
window.deleteVendor = async function(id) {
    if (!confirm('Are you sure you want to delete this vendor? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/vendors/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to delete vendor');
        
        showAlert('Vendor deleted successfully!', 'success');
        fetchVendors(); // Refresh table
    } catch (error) {
        console.error('Error deleting vendor:', error);
        showAlert('Failed to delete vendor.', 'error');
    }
};

/**
 * Populate form with vendor data for editing
 */
window.editVendor = function(id, name, email, phone) {
    vendorIdInput.value = id;
    vendorNameInput.value = name;
    vendorEmailInput.value = email;
    vendorPhoneInput.value = phone;
    
    // Switch UI to "Update" mode
    formTitle.textContent = 'Edit';
    btnSubmit.classList.add('hidden');
    btnUpdate.classList.remove('hidden');
    
    // Scroll smoothly to form if on small screen
    vendorForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

/**
 * Reset form fields and UI state
 */
function resetForm() {
    vendorForm.reset();
    vendorIdInput.value = '';
    
    // Switch UI back to "Add" mode
    formTitle.textContent = 'Add New';
    btnSubmit.classList.remove('hidden');
    btnUpdate.classList.add('hidden');
}

/**
 * Show auto-dismissing alert message
 * @param {string} message - Alert text
 * @param {string} type - Alert type ('success' or 'error')
 */
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    alertDiv.innerHTML = `<i class="fas ${icon}"></i> ${message}`;
    
    // Replace any existing alert
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertDiv);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        alertDiv.style.opacity = '0';
        alertDiv.style.transition = 'opacity 0.3s ease';
        setTimeout(() => alertDiv.remove(), 300);
    }, 3000);
}
