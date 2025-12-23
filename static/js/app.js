/**
 * Product Importer - Frontend Application
 * Handles file uploads, product CRUD, webhooks, and real-time progress tracking
 */

// ==========================================
// API Client
// ==========================================
const API = {
    baseUrl: '/api',
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'An error occurred');
            }
            
            return data;
        } catch (error) {
            if (error.message === 'Failed to fetch') {
                throw new Error('Network error. Please check your connection.');
            }
            throw error;
        }
    },
    
    // Products
    async getProducts(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/products${query ? '?' + query : ''}`);
    },
    
    async createProduct(data) {
        return this.request('/products', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    async updateProduct(id, data) {
        return this.request(`/products/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    async deleteProduct(id) {
        return this.request(`/products/${id}`, { method: 'DELETE' });
    },
    
    async deleteAllProducts() {
        return this.request('/products?confirm=true', { method: 'DELETE' });
    },
    
    async getProductStats() {
        return this.request('/products/stats/summary');
    },
    
    // Imports
    async uploadCSV(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${this.baseUrl}/imports/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Upload failed');
        }
        return data;
    },
    
    async getImportStatus(jobId) {
        return this.request(`/imports/${jobId}/status`);
    },
    
    async getImports() {
        return this.request('/imports');
    },
    
    streamImportProgress(jobId, onMessage, onError) {
        const eventSource = new EventSource(`${this.baseUrl}/imports/${jobId}/stream`);
        
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onMessage(data);
                
                if (data.status === 'completed' || data.status === 'failed' || data.status === 'stream_ended') {
                    eventSource.close();
                }
            } catch (e) {
                console.error('Error parsing SSE message:', e);
            }
        };
        
        eventSource.onerror = (error) => {
            eventSource.close();
            if (onError) onError(error);
        };
        
        return eventSource;
    },
    
    // Webhooks
    async getWebhooks() {
        return this.request('/webhooks');
    },
    
    async createWebhook(data) {
        return this.request('/webhooks', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    async updateWebhook(id, data) {
        return this.request(`/webhooks/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    async deleteWebhook(id) {
        return this.request(`/webhooks/${id}`, { method: 'DELETE' });
    },
    
    async testWebhook(id) {
        return this.request(`/webhooks/${id}/test`, { method: 'POST' });
    }
};

// ==========================================
// State Management
// ==========================================
const State = {
    products: {
        items: [],
        total: 0,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        filters: {
            search: '',
            is_active: ''
        }
    },
    webhooks: [],
    imports: [],
    currentImportJob: null
};

// ==========================================
// UI Utilities
// ==========================================
const UI = {
    $(selector) {
        return document.querySelector(selector);
    },
    
    $$(selector) {
        return document.querySelectorAll(selector);
    },
    
    show(element) {
        if (typeof element === 'string') element = this.$(element);
        element?.classList.remove('hidden');
    },
    
    hide(element) {
        if (typeof element === 'string') element = this.$(element);
        element?.classList.add('hidden');
    },
    
    showModal(modalId) {
        this.$(`#${modalId}`)?.classList.add('active');
    },
    
    hideModal(modalId) {
        this.$(`#${modalId}`)?.classList.remove('active');
    },
    
    showToast(message, type = 'info') {
        const container = this.$('#toast-container');
        const icons = {
            success: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
            error: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
            warning: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
            info: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon ${type}">${icons[type]}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close">&times;</button>
        `;
        
        container.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
        
        // Manual close
        toast.querySelector('.toast-close').addEventListener('click', () => {
            toast.remove();
        });
    },
    
    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    },
    
    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },
    
    formatPrice(price) {
        if (price === null || price === undefined) return '-';
        return '$' + parseFloat(price).toFixed(2);
    },
    
    truncate(str, length = 50) {
        if (!str) return '';
        return str.length > length ? str.substring(0, length) + '...' : str;
    }
};

// ==========================================
// Tab Navigation
// ==========================================
function initTabs() {
    UI.$$('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = item.dataset.tab;
            
            // Update nav items
            UI.$$('.nav-item').forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            // Update tab content
            UI.$$('.tab-content').forEach(tab => tab.classList.remove('active'));
            UI.$(`#tab-${tabId}`).classList.add('active');
            
            // Load tab-specific data
            if (tabId === 'products') loadProducts();
            if (tabId === 'webhooks') loadWebhooks();
            if (tabId === 'import') loadImportHistory();
        });
    });
}

// ==========================================
// Products Management
// ==========================================
async function loadProducts() {
    const tbody = UI.$('#products-tbody');
    tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Loading products...</td></tr>';
    
    try {
        const params = {
            page: State.products.page,
            page_size: State.products.pageSize,
            ...State.products.filters
        };
        
        // Remove empty filters
        Object.keys(params).forEach(key => {
            if (params[key] === '' || params[key] === null) delete params[key];
        });
        
        const response = await API.getProducts(params);
        State.products = { ...State.products, ...response };
        
        renderProducts();
        updatePagination();
        updateProductStats();
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Error: ${error.message}</td></tr>`;
        UI.showToast(error.message, 'error');
    }
}

function renderProducts() {
    const tbody = UI.$('#products-tbody');
    
    if (State.products.items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No products found</td></tr>';
        return;
    }
    
    tbody.innerHTML = State.products.items.map(product => `
        <tr data-id="${product.id}">
            <td><strong>${product.sku}</strong></td>
            <td>${UI.truncate(product.name, 40)}</td>
            <td class="text-muted">${UI.truncate(product.description || '-', 50)}</td>
            <td>${UI.formatPrice(product.price)}</td>
            <td>${UI.formatNumber(product.quantity)}</td>
            <td>
                <span class="status-toggle">
                    <span class="status-indicator ${product.is_active ? 'active' : 'inactive'}"></span>
                    ${product.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-icon btn-small" onclick="editProduct(${product.id})" title="Edit">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                    </button>
                    <button class="btn btn-icon btn-small" onclick="deleteProduct(${product.id})" title="Delete">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function updatePagination() {
    UI.$('#page-info').textContent = `Page ${State.products.page} of ${State.products.totalPages || 1}`;
    UI.$('#prev-page').disabled = State.products.page <= 1;
    UI.$('#next-page').disabled = State.products.page >= State.products.totalPages;
}

async function updateProductStats() {
    try {
        const stats = await API.getProductStats();
        UI.$('#total-products-count').textContent = UI.formatNumber(stats.total);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function initProductFilters() {
    const searchInput = UI.$('#search-input');
    const statusFilter = UI.$('#status-filter');
    const resetBtn = UI.$('#reset-filters-btn');
    
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            State.products.filters.search = e.target.value;
            State.products.page = 1;
            loadProducts();
        }, 300);
    });
    
    statusFilter.addEventListener('change', (e) => {
        State.products.filters.is_active = e.target.value;
        State.products.page = 1;
        loadProducts();
    });
    
    resetBtn.addEventListener('click', () => {
        searchInput.value = '';
        statusFilter.value = '';
        State.products.filters = { search: '', is_active: '' };
        State.products.page = 1;
        loadProducts();
    });
    
    UI.$('#prev-page').addEventListener('click', () => {
        if (State.products.page > 1) {
            State.products.page--;
            loadProducts();
        }
    });
    
    UI.$('#next-page').addEventListener('click', () => {
        if (State.products.page < State.products.totalPages) {
            State.products.page++;
            loadProducts();
        }
    });
}

function initProductModal() {
    const modal = UI.$('#product-modal');
    const form = UI.$('#product-form');
    
    UI.$('#create-product-btn').addEventListener('click', () => {
        resetProductForm();
        UI.$('#product-modal-title').textContent = 'Add Product';
        UI.$('#product-sku').disabled = false;
        UI.showModal('product-modal');
    });
    
    modal.querySelectorAll('.modal-close, .modal-backdrop').forEach(el => {
        el.addEventListener('click', () => UI.hideModal('product-modal'));
    });
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const id = UI.$('#product-id').value;
        const data = {
            sku: UI.$('#product-sku').value,
            name: UI.$('#product-name').value,
            description: UI.$('#product-description').value || null,
            price: UI.$('#product-price').value ? parseFloat(UI.$('#product-price').value) : null,
            quantity: parseInt(UI.$('#product-quantity').value) || 0,
            is_active: UI.$('#product-active').checked
        };
        
        try {
            if (id) {
                delete data.sku; // Don't update SKU
                await API.updateProduct(id, data);
                UI.showToast('Product updated successfully', 'success');
            } else {
                await API.createProduct(data);
                UI.showToast('Product created successfully', 'success');
            }
            
            UI.hideModal('product-modal');
            loadProducts();
        } catch (error) {
            UI.showToast(error.message, 'error');
        }
    });
}

function resetProductForm() {
    UI.$('#product-id').value = '';
    UI.$('#product-sku').value = '';
    UI.$('#product-name').value = '';
    UI.$('#product-description').value = '';
    UI.$('#product-price').value = '';
    UI.$('#product-quantity').value = '0';
    UI.$('#product-active').checked = true;
}

async function editProduct(id) {
    try {
        const product = State.products.items.find(p => p.id === id);
        if (!product) return;
        
        UI.$('#product-id').value = product.id;
        UI.$('#product-sku').value = product.sku;
        UI.$('#product-sku').disabled = true;
        UI.$('#product-name').value = product.name;
        UI.$('#product-description').value = product.description || '';
        UI.$('#product-price').value = product.price || '';
        UI.$('#product-quantity').value = product.quantity || 0;
        UI.$('#product-active').checked = product.is_active;
        
        UI.$('#product-modal-title').textContent = 'Edit Product';
        UI.showModal('product-modal');
    } catch (error) {
        UI.showToast(error.message, 'error');
    }
}

async function deleteProduct(id) {
    showConfirmDialog(
        'Delete Product',
        'Are you sure you want to delete this product? This action cannot be undone.',
        async () => {
            try {
                await API.deleteProduct(id);
                UI.showToast('Product deleted successfully', 'success');
                loadProducts();
            } catch (error) {
                UI.showToast(error.message, 'error');
            }
        }
    );
}

function initBulkDelete() {
    UI.$('#bulk-delete-btn').addEventListener('click', () => {
        showConfirmDialog(
            'Delete All Products',
            'Are you sure you want to delete ALL products? This action cannot be undone!',
            async () => {
                try {
                    const result = await API.deleteAllProducts();
                    UI.showToast(result.message, 'success');
                    loadProducts();
                } catch (error) {
                    UI.showToast(error.message, 'error');
                }
            }
        );
    });
}

// ==========================================
// File Upload
// ==========================================
function initFileUpload() {
    const uploadZone = UI.$('#upload-zone');
    const fileInput = UI.$('#file-input');
    const browseBtn = UI.$('#browse-btn');
    
    // Click to browse
    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });
    
    uploadZone.addEventListener('click', () => fileInput.click());
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
    
    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        
        const file = e.dataTransfer.files[0];
        if (file && file.name.endsWith('.csv')) {
            handleFileUpload(file);
        } else {
            UI.showToast('Please upload a CSV file', 'error');
        }
    });
}

async function handleFileUpload(file) {
    UI.hide('#upload-zone');
    UI.show('#import-progress');
    
    resetProgress();
    UI.$('#progress-filename').textContent = `Uploading ${file.name}...`;
    UI.$('#progress-status').textContent = 'Uploading';
    UI.$('#progress-status').className = 'status-badge pending';
    
    try {
        const response = await API.uploadCSV(file);
        State.currentImportJob = response.job_id;
        
        UI.$('#progress-filename').textContent = `Processing ${file.name}`;
        
        // Start streaming progress
        API.streamImportProgress(
            response.job_id,
            updateProgressUI,
            (error) => {
                console.error('SSE error:', error);
                // Fallback to polling
                pollImportStatus(response.job_id);
            }
        );
    } catch (error) {
        UI.showToast(error.message, 'error');
        UI.$('#progress-status').textContent = 'Failed';
        UI.$('#progress-status').className = 'status-badge failed';
        UI.$('#progress-message').textContent = error.message;
        
        setTimeout(() => {
            UI.show('#upload-zone');
            UI.hide('#import-progress');
        }, 3000);
    }
}

function resetProgress() {
    UI.$('#progress-bar').style.width = '0%';
    UI.$('#progress-percentage').textContent = '0%';
    UI.$('#progress-processed').textContent = '0';
    UI.$('#progress-created').textContent = '0';
    UI.$('#progress-updated').textContent = '0';
    UI.$('#progress-errors').textContent = '0';
    UI.$('#progress-message').textContent = 'Preparing import...';
}

function updateProgressUI(data) {
    const statusBadge = UI.$('#progress-status');
    statusBadge.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
    statusBadge.className = `status-badge ${data.status}`;
    
    const percentage = data.progress_percentage || 0;
    UI.$('#progress-bar').style.width = `${percentage}%`;
    UI.$('#progress-percentage').textContent = `${percentage.toFixed(1)}%`;
    
    UI.$('#progress-processed').textContent = UI.formatNumber(data.processed_rows || 0);
    UI.$('#progress-created').textContent = UI.formatNumber(data.created_count || 0);
    UI.$('#progress-updated').textContent = UI.formatNumber(data.updated_count || 0);
    UI.$('#progress-errors').textContent = UI.formatNumber(data.error_count || 0);
    UI.$('#progress-message').textContent = data.message || '';
    
    if (data.status === 'completed') {
        UI.showToast('Import completed successfully!', 'success');
        loadImportHistory();
        updateProductStats();
        
        setTimeout(() => {
            UI.show('#upload-zone');
            UI.hide('#import-progress');
            UI.$('#file-input').value = '';
        }, 3000);
    } else if (data.status === 'failed') {
        UI.showToast('Import failed: ' + (data.error || 'Unknown error'), 'error');
        
        setTimeout(() => {
            UI.show('#upload-zone');
            UI.hide('#import-progress');
            UI.$('#file-input').value = '';
        }, 5000);
    }
}

async function pollImportStatus(jobId) {
    const poll = async () => {
        try {
            const status = await API.getImportStatus(jobId);
            updateProgressUI(status);
            
            if (status.status !== 'completed' && status.status !== 'failed') {
                setTimeout(poll, 1000);
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    };
    
    poll();
}

async function loadImportHistory() {
    try {
        const response = await API.getImports();
        State.imports = response.items;
        renderImportHistory();
    } catch (error) {
        console.error('Failed to load import history:', error);
    }
}

function renderImportHistory() {
    const container = UI.$('#import-history');
    
    if (State.imports.length === 0) {
        container.innerHTML = '<p class="empty-state">No recent imports</p>';
        return;
    }
    
    container.innerHTML = State.imports.map(job => `
        <div class="history-item">
            <div class="history-info">
                <h4>${job.filename}</h4>
                <p>${UI.formatDate(job.created_at)}</p>
            </div>
            <div class="history-stats">
                <div class="history-stat">
                    <div class="history-stat-label">Created</div>
                    <div class="history-stat-value" style="color: var(--accent-success)">${UI.formatNumber(job.created_count)}</div>
                </div>
                <div class="history-stat">
                    <div class="history-stat-label">Updated</div>
                    <div class="history-stat-value" style="color: var(--accent-info)">${UI.formatNumber(job.updated_count)}</div>
                </div>
                <div class="history-stat">
                    <div class="history-stat-label">Errors</div>
                    <div class="history-stat-value" style="color: var(--accent-danger)">${UI.formatNumber(job.error_count)}</div>
                </div>
                <span class="status-badge ${job.status}">${job.status}</span>
            </div>
        </div>
    `).join('');
}

// ==========================================
// Webhooks Management
// ==========================================
async function loadWebhooks() {
    try {
        const response = await API.getWebhooks();
        State.webhooks = response.items;
        renderWebhooks();
    } catch (error) {
        UI.showToast(error.message, 'error');
    }
}

function renderWebhooks() {
    const grid = UI.$('#webhooks-grid');
    
    if (State.webhooks.length === 0) {
        grid.innerHTML = '<p class="empty-state">No webhooks configured. Add one to get started.</p>';
        return;
    }
    
    grid.innerHTML = State.webhooks.map(webhook => `
        <div class="webhook-card" data-id="${webhook.id}">
            <div class="webhook-header">
                <div>
                    <h3>${webhook.name}</h3>
                    <p class="webhook-url">${webhook.url}</p>
                </div>
                <label class="toggle-switch">
                    <input type="checkbox" ${webhook.is_enabled ? 'checked' : ''} onchange="toggleWebhook(${webhook.id}, this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
            <span class="webhook-event">${webhook.event_type}</span>
            <div class="webhook-status">
                <div class="webhook-status-row">
                    <span class="webhook-status-label">Last triggered</span>
                    <span class="webhook-status-value">${webhook.last_triggered_at ? UI.formatDate(webhook.last_triggered_at) : 'Never'}</span>
                </div>
                <div class="webhook-status-row">
                    <span class="webhook-status-label">Last response</span>
                    <span class="webhook-status-value ${webhook.last_response_code && webhook.last_response_code < 400 ? 'success' : (webhook.last_response_code ? 'error' : '')}">${webhook.last_response_code || '-'}</span>
                </div>
                <div class="webhook-status-row">
                    <span class="webhook-status-label">Response time</span>
                    <span class="webhook-status-value">${webhook.last_response_time_ms ? webhook.last_response_time_ms + 'ms' : '-'}</span>
                </div>
            </div>
            <div class="webhook-actions">
                <button class="btn btn-secondary btn-small" onclick="testWebhook(${webhook.id})">Test</button>
                <button class="btn btn-secondary btn-small" onclick="editWebhook(${webhook.id})">Edit</button>
                <button class="btn btn-secondary btn-small" onclick="deleteWebhook(${webhook.id})">Delete</button>
            </div>
        </div>
    `).join('');
}

function initWebhookModal() {
    const modal = UI.$('#webhook-modal');
    const form = UI.$('#webhook-form');
    
    UI.$('#create-webhook-btn').addEventListener('click', () => {
        resetWebhookForm();
        UI.$('#webhook-modal-title').textContent = 'Add Webhook';
        UI.showModal('webhook-modal');
    });
    
    modal.querySelectorAll('.modal-close, .modal-backdrop').forEach(el => {
        el.addEventListener('click', () => UI.hideModal('webhook-modal'));
    });
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const id = UI.$('#webhook-id').value;
        const data = {
            name: UI.$('#webhook-name').value,
            url: UI.$('#webhook-url').value,
            event_type: UI.$('#webhook-event').value,
            secret: UI.$('#webhook-secret').value || null,
            is_enabled: UI.$('#webhook-enabled').checked
        };
        
        try {
            if (id) {
                await API.updateWebhook(id, data);
                UI.showToast('Webhook updated successfully', 'success');
            } else {
                await API.createWebhook(data);
                UI.showToast('Webhook created successfully', 'success');
            }
            
            UI.hideModal('webhook-modal');
            loadWebhooks();
        } catch (error) {
            UI.showToast(error.message, 'error');
        }
    });
}

function resetWebhookForm() {
    UI.$('#webhook-id').value = '';
    UI.$('#webhook-name').value = '';
    UI.$('#webhook-url').value = '';
    UI.$('#webhook-event').value = '';
    UI.$('#webhook-secret').value = '';
    UI.$('#webhook-enabled').checked = true;
}

async function editWebhook(id) {
    const webhook = State.webhooks.find(w => w.id === id);
    if (!webhook) return;
    
    UI.$('#webhook-id').value = webhook.id;
    UI.$('#webhook-name').value = webhook.name;
    UI.$('#webhook-url').value = webhook.url;
    UI.$('#webhook-event').value = webhook.event_type;
    UI.$('#webhook-secret').value = '';
    UI.$('#webhook-enabled').checked = webhook.is_enabled;
    
    UI.$('#webhook-modal-title').textContent = 'Edit Webhook';
    UI.showModal('webhook-modal');
}

async function deleteWebhook(id) {
    showConfirmDialog(
        'Delete Webhook',
        'Are you sure you want to delete this webhook?',
        async () => {
            try {
                await API.deleteWebhook(id);
                UI.showToast('Webhook deleted successfully', 'success');
                loadWebhooks();
            } catch (error) {
                UI.showToast(error.message, 'error');
            }
        }
    );
}

async function toggleWebhook(id, enabled) {
    try {
        await API.updateWebhook(id, { is_enabled: enabled });
        UI.showToast(`Webhook ${enabled ? 'enabled' : 'disabled'}`, 'success');
    } catch (error) {
        UI.showToast(error.message, 'error');
        loadWebhooks(); // Reload to reset toggle state
    }
}

async function testWebhook(id) {
    UI.showToast('Testing webhook...', 'info');
    
    try {
        const result = await API.testWebhook(id);
        
        if (result.success) {
            UI.showToast(`Webhook test successful! Response: ${result.status_code} (${result.response_time_ms}ms)`, 'success');
        } else {
            UI.showToast(`Webhook test failed: ${result.error}`, 'error');
        }
        
        loadWebhooks(); // Reload to update status
    } catch (error) {
        UI.showToast(error.message, 'error');
    }
}

// ==========================================
// Confirm Dialog
// ==========================================
function showConfirmDialog(title, message, onConfirm) {
    UI.$('#confirm-title').textContent = title;
    UI.$('#confirm-message').textContent = message;
    UI.showModal('confirm-modal');
    
    const confirmBtn = UI.$('#confirm-btn');
    const handleConfirm = async () => {
        confirmBtn.removeEventListener('click', handleConfirm);
        UI.hideModal('confirm-modal');
        await onConfirm();
    };
    
    confirmBtn.addEventListener('click', handleConfirm);
}

function initConfirmModal() {
    const modal = UI.$('#confirm-modal');
    modal.querySelectorAll('.modal-close, .modal-backdrop').forEach(el => {
        el.addEventListener('click', () => UI.hideModal('confirm-modal'));
    });
}

// ==========================================
// Initialize Application
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initFileUpload();
    initProductFilters();
    initProductModal();
    initBulkDelete();
    initWebhookModal();
    initConfirmModal();
    
    // Load initial data
    loadImportHistory();
    updateProductStats();
});

// Make functions globally accessible for inline event handlers
window.editProduct = editProduct;
window.deleteProduct = deleteProduct;
window.editWebhook = editWebhook;
window.deleteWebhook = deleteWebhook;
window.toggleWebhook = toggleWebhook;
window.testWebhook = testWebhook;
