/**
 * ConnectLink Component Library
 * React-like components for interactive UI
 */

class Modal {
    constructor(selector) {
        this.modal = document.querySelector(selector);
        this.overlay = this.modal?.querySelector('.modal-overlay');
        this.closeBtn = this.modal?.querySelector('.modal-close-btn');
        this.init();
    }

    init() {
        if (!this.modal) return;
        this.closeBtn?.addEventListener('click', () => this.close());
        this.overlay?.addEventListener('click', (e) => {
            if (e.target === this.overlay) this.close();
        });
    }

    open() {
        this.overlay?.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    close() {
        this.overlay?.classList.remove('active');
        document.body.style.overflow = 'auto';
    }

    toggle() {
        this.overlay?.classList.toggle('active');
    }
}

class Dropdown {
    constructor(selector) {
        this.toggle = document.querySelector(`${selector} .dropdown-toggle`);
        this.menu = document.querySelector(`${selector} .dropdown-menu`);
        this.init();
    }

    init() {
        if (!this.toggle || !this.menu) return;
        
        this.toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle_menu();
        });

        document.addEventListener('click', () => this.close());
        this.menu.addEventListener('click', (e) => e.stopPropagation());
    }

    toggle_menu() {
        this.menu.classList.toggle('active');
    }

    close() {
        this.menu.classList.remove('active');
    }
}

class Tabs {
    constructor(selector) {
        this.container = document.querySelector(selector);
        this.buttons = this.container?.querySelectorAll('[data-tab]');
        this.panels = this.container?.querySelectorAll('[data-panel]');
        this.init();
    }

    init() {
        if (!this.buttons || !this.panels) return;
        
        this.buttons.forEach((btn) => {
            btn.addEventListener('click', () => {
                const tabName = btn.getAttribute('data-tab');
                this.activate(tabName);
            });
        });
    }

    activate(tabName) {
        // Deactivate all
        this.buttons.forEach((btn) => btn.classList.remove('active'));
        this.panels.forEach((panel) => panel.classList.remove('active'));

        // Activate selected
        document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');
        document.querySelector(`[data-panel="${tabName}"]`)?.classList.add('active');
    }
}

class Toast {
    static show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-${Toast.getIcon(type)}"></i>
            </div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        const container = document.querySelector('.toast-container') || 
            (() => {
                const c = document.createElement('div');
                c.className = 'toast-container';
                document.body.appendChild(c);
                return c;
            })();

        container.appendChild(toast);
        toast.classList.add('show');

        setTimeout(() => toast.remove(), duration);
    }

    static getIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || icons.info;
    }
}

class Form {
    constructor(selector) {
        this.form = document.querySelector(selector);
        this.fields = {};
        this.init();
    }

    init() {
        if (!this.form) return;
        
        // Collect all form fields
        this.form.querySelectorAll('input, select, textarea').forEach((field) => {
            const name = field.getAttribute('name');
            if (name) {
                this.fields[name] = field;
            }
        });

        // Setup real-time validation
        Object.values(this.fields).forEach((field) => {
            field.addEventListener('blur', () => this.validateField(field));
        });

        this.form.addEventListener('submit', (e) => e.preventDefault());
    }

    getData() {
        const data = {};
        Object.entries(this.fields).forEach(([name, field]) => {
            data[name] = field.value;
        });
        return data;
    }

    setData(data) {
        Object.entries(data).forEach(([name, value]) => {
            if (this.fields[name]) {
                this.fields[name].value = value;
            }
        });
    }

    validateField(field) {
        const name = field.getAttribute('name');
        let isValid = true;

        if (field.hasAttribute('required') && !field.value.trim()) {
            isValid = false;
            this.setFieldError(field, 'This field is required');
        } else if (field.type === 'email' && field.value) {
            isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(field.value);
            if (!isValid) {
                this.setFieldError(field, 'Invalid email address');
            }
        } else {
            this.clearFieldError(field);
        }

        return isValid;
    }

    validateAll() {
        let isValid = true;
        Object.values(this.fields).forEach((field) => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        return isValid;
    }

    setFieldError(field, message) {
        field.classList.add('form-error');
        const errorEl = field.parentElement.querySelector('.form-error-message') ||
            (() => {
                const err = document.createElement('div');
                err.className = 'form-error-message';
                field.parentElement.appendChild(err);
                return err;
            })();
        errorEl.textContent = message;
    }

    clearFieldError(field) {
        field.classList.remove('form-error');
        field.parentElement.querySelector('.form-error-message')?.remove();
    }

    reset() {
        this.form.reset();
        Object.values(this.fields).forEach((field) => {
            this.clearFieldError(field);
        });
    }
}

class Notification {
    static show(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.innerHTML = `
            <div class="alert-icon">
                <i class="fas fa-${this.getIcon(type)}"></i>
            </div>
            <div class="alert-content">
                <div class="alert-message">${message}</div>
            </div>
        `;

        const container = document.querySelector('.notifications-container') ||
            (() => {
                const c = document.createElement('div');
                c.className = 'notifications-container';
                document.body.appendChild(c);
                return c;
            })();

        container.appendChild(notification);
        
        setTimeout(() => notification.remove(), 4000);
    }

    static getIcon(type) {
        const icons = {
            success: 'check-circle',
            danger: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || icons.info;
    }
}

class DataTable {
    constructor(selector, options = {}) {
        this.table = document.querySelector(selector);
        this.options = options;
        this.data = [];
        this.filteredData = [];
        this.init();
    }

    init() {
        if (!this.table) return;
        
        // Add search functionality
        const searchInput = document.querySelector('[data-table-search]');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.search(e.target.value);
            });
        }

        // Add sorting
        this.table.querySelectorAll('thead th[data-sortable]').forEach((th) => {
            th.style.cursor = 'pointer';
            th.addEventListener('click', () => {
                const column = th.getAttribute('data-sortable');
                this.sort(column);
            });
        });
    }

    search(query) {
        if (!query) {
            this.filteredData = [...this.data];
        } else {
            this.filteredData = this.data.filter((row) => {
                return Object.values(row).some((val) =>
                    String(val).toLowerCase().includes(query.toLowerCase())
                );
            });
        }
        this.render();
    }

    sort(column) {
        const isAscending = this.table.querySelector(`th[data-sortable="${column}"]`)?.classList.toggle('sort-asc');
        
        this.filteredData.sort((a, b) => {
            const aVal = a[column];
            const bVal = b[column];
            
            if (typeof aVal === 'number') {
                return isAscending ? aVal - bVal : bVal - aVal;
            }
            
            const comparison = String(aVal).localeCompare(String(bVal));
            return isAscending ? comparison : -comparison;
        });

        this.render();
    }

    render() {
        const tbody = this.table.querySelector('tbody');
        if (!tbody) return;

        tbody.innerHTML = this.filteredData.map((row) => {
            const cells = Object.values(row).map((val) => 
                `<td>${val}</td>`
            ).join('');
            return `<tr>${cells}</tr>`;
        }).join('');
    }

    setData(data) {
        this.data = data;
        this.filteredData = [...data];
        this.render();
    }
}

class Pagination {
    constructor(selector, itemsPerPage = 10) {
        this.container = document.querySelector(selector);
        this.itemsPerPage = itemsPerPage;
        this.currentPage = 1;
        this.totalItems = 0;
        this.data = [];
    }

    setData(data) {
        this.data = data;
        this.totalItems = data.length;
        this.currentPage = 1;
        this.render();
    }

    goToPage(page) {
        const totalPages = Math.ceil(this.totalItems / this.itemsPerPage);
        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.render();
        }
    }

    getPageData() {
        const start = (this.currentPage - 1) * this.itemsPerPage;
        return this.data.slice(start, start + this.itemsPerPage);
    }

    render() {
        const totalPages = Math.ceil(this.totalItems / this.itemsPerPage);
        const buttons = [];

        // Previous button
        if (this.currentPage > 1) {
            buttons.push(`
                <button class="btn btn-secondary btn-small" onclick="this.pagination.goToPage(${this.currentPage - 1})">
                    <i class="fas fa-chevron-left"></i>
                </button>
            `);
        }

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === this.currentPage) {
                buttons.push(`<button class="btn btn-primary btn-small active">${i}</button>`);
            } else {
                buttons.push(`
                    <button class="btn btn-secondary btn-small" onclick="this.pagination.goToPage(${i})">
                        ${i}
                    </button>
                `);
            }
        }

        // Next button
        if (this.currentPage < totalPages) {
            buttons.push(`
                <button class="btn btn-secondary btn-small" onclick="this.pagination.goToPage(${this.currentPage + 1})">
                    <i class="fas fa-chevron-right"></i>
                </button>
            `);
        }

        if (this.container) {
            this.container.innerHTML = buttons.join('');
        }
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Modal, Dropdown, Tabs, Toast, Form, Notification, DataTable, Pagination };
}
