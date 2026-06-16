# ConnectLink React Visual System - Quick Reference

## 🚀 Quick Start

### 1. Create New Page
```html
{% extends "base_modern.html" %}
{% block title %}My Page | ConnectLink{% endblock %}
{% block page_title %}My Page{% endblock %}
{% block page_subtitle %}Page description{% endblock %}

{% block content %}
<!-- Your content -->
{% endblock %}
```

### 2. Common Imports (Already in base_modern.html)
```html
<!-- CSS -->
<link rel="stylesheet" href="design-system.css">
<link rel="stylesheet" href="components-ui.css">

<!-- JS -->
<script src="components.js"></script>
```

---

## 🎨 Design Tokens Cheat Sheet

| Token | Value | Use |
|-------|-------|-----|
| `--primary` | #0A2B3E | Main headings, important text |
| `--accent` | #b50d0d | CTAs, highlights, status |
| `--success` | #22c55e | Success messages, positive actions |
| `--warning` | #f59e0b | Warnings, pending states |
| `--danger` | #ef4444 | Errors, destructive actions |
| `--gray-50` | #F9FAFB | Page background |
| `--gray-100` | #F3F4F6 | Hover states, light backgrounds |
| `--radius-lg` | 1rem | Buttons, inputs |
| `--radius-2xl` | 1.5rem | Cards, modals |

---

## 📦 Component Snippets

### KPI Card
```html
<div class="kpi-card">
    <div class="kpi-header">
        <div>
            <div class="kpi-title">TOTAL PROJECTS</div>
            <div class="kpi-value">42</div>
            <div class="kpi-change positive">
                <i class="fas fa-arrow-up"></i> +12%
            </div>
        </div>
        <div class="kpi-icon">
            <i class="fas fa-project-diagram"></i>
        </div>
    </div>
</div>
```

### Search Bar
```html
<div style="flex: 1;">
    <input 
        type="text" 
        class="form-input" 
        placeholder="Search..."
        id="search"
    >
</div>

<script>
    document.getElementById('search').addEventListener('input', (e) => {
        filterData(e.target.value);
    });
</script>
```

### Data Table
```html
<div class="table-wrapper">
    <table class="table-responsive">
        <thead>
            <tr>
                <th data-sortable="name">Name</th>
                <th data-sortable="amount">Amount</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody id="tableBody">
        </tbody>
    </table>
</div>

<script>
    const table = new DataTable('table.table-responsive');
    table.setData(data);
</script>
```

### Status Badge
```html
<span class="status-badge status-ongoing">Ongoing</span>
<span class="status-badge status-completed">Completed</span>
<span class="status-badge status-pending">Pending</span>
```

### Modal Dialog
```html
<div class="modal-overlay" id="confirmModal">
    <div class="modal-content" style="max-width: 400px;">
        <div class="modal-header">
            <h2 class="modal-title">Confirm</h2>
            <button class="modal-close-btn"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">Are you sure?</div>
        <div class="modal-footer">
            <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="confirm()">Confirm</button>
        </div>
    </div>
</div>

<script>
    const modal = new Modal('#confirmModal');
    modal.open();
</script>
```

### Alert/Notification
```html
<div class="alert alert-success">
    <div class="alert-icon"><i class="fas fa-check-circle"></i></div>
    <div class="alert-content">
        <div class="alert-title">Success!</div>
        <div class="alert-message">Your changes have been saved.</div>
    </div>
</div>
```

### Form with Validation
```html
<form id="myForm">
    <div class="form-group">
        <label class="form-label">Name *</label>
        <input type="text" class="form-input" name="name" required>
    </div>
    
    <div class="form-group">
        <label class="form-label">Email *</label>
        <input type="email" class="form-input" name="email" required>
    </div>
    
    <button type="submit" class="btn btn-primary">Submit</button>
</form>

<script>
    const form = new Form('#myForm');
    
    document.getElementById('myForm').addEventListener('submit', (e) => {
        e.preventDefault();
        if (form.validateAll()) {
            const data = form.getData();
            // Submit data
        }
    });
</script>
```

### Action Buttons
```html
<div class="actions-cell">
    <button class="action-btn" title="View">
        <i class="fas fa-eye"></i>
    </button>
    <button class="action-btn" title="Edit">
        <i class="fas fa-edit"></i>
    </button>
    <button class="action-btn" title="Delete">
        <i class="fas fa-trash"></i>
    </button>
</div>
```

---

## 🔧 JavaScript Utilities

### Show Toast
```javascript
Toast.show('Operation completed', 'success');
Toast.show('Something went wrong', 'error');
Toast.show('Please review', 'warning');
```

### API Call
```javascript
// GET
const data = await apiCall('/api/projects');

// POST
const result = await apiCall('/api/projects', {
    method: 'POST',
    body: JSON.stringify({ name: 'New Project' })
});

// Error handling (automatic toast)
try {
    await apiCall('/api/endpoint');
} catch (error) {
    // Error already shown
}
```

### Show Notification
```javascript
Notification.show('Updated successfully', 'success');
Notification.show('Error occurred', 'danger');
```

---

## 🎯 Common Layouts

### Full Width Section
```html
<div class="section-card" style="width: 100%;">
    <h3 class="section-title">Section Title</h3>
    <!-- Content -->
</div>
```

### Two Column Grid
```html
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
    <div class="section-card">Column 1</div>
    <div class="section-card">Column 2</div>
</div>
```

### Responsive Grid
```html
<div class="content-grid">
    <div class="section-card">Card 1</div>
    <div class="section-card">Card 2</div>
    <div class="section-card">Card 3</div>
</div>

<!-- 3 cols on desktop, 2 cols on tablet, 1 col on mobile -->
```

### Header with Action Button
```html
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
    <div>
        <h2 style="font-size: 1.25rem; font-weight: 700;">Page Title</h2>
        <p style="color: var(--gray-500); font-size: 0.875rem;">Subtitle</p>
    </div>
    <button class="btn btn-primary">
        <i class="fas fa-plus"></i> New Item
    </button>
</div>
```

---

## 🎬 Animations Included

| Class | Purpose |
|-------|---------|
| `fade-in-down` | Header animations |
| `fade-in-up` | Content animations |
| `slideIn` | Toast notifications |
| `floatOrb` | Background patterns |
| `spin` | Loading spinner |
| `shimmer` | Skeleton loading |

```html
<div class="fade-in-down">Header content</div>
<div class="fade-in-up">Page content</div>
```

---

## 🔌 API Response Format

Expected format from Flask:
```json
{
    "success": true,
    "data": { ... }
}
```

Error format:
```json
{
    "success": false,
    "message": "Error description"
}
```

---

## 📱 Responsive Breakpoints

- **Desktop**: 1024px+
- **Tablet**: 768px - 1024px
- **Mobile**: < 768px

All components automatically adapt!

---

## ⚡ Performance Tips

1. **Use Pagination**
```javascript
const pagination = new Pagination('#paginationDiv', 10);
pagination.setData(largeArray);
```

2. **Debounce Search**
```javascript
let debounceTimer;
searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        filterData(e.target.value);
    }, 300);
});
```

3. **Lazy Load Data**
```javascript
document.addEventListener('DOMContentLoaded', () => {
    loadInitialData();
    setTimeout(loadSecondaryData, 2000);
});
```

---

## 🐛 Debugging

### Check Browser Console
- All errors logged
- API calls visible in Network tab
- Selector errors shown

### Common Issues

| Issue | Solution |
|-------|----------|
| Modal not appearing | Check ID matches selector, ensure overlay has correct class |
| Styles not applying | Verify CSS files loaded, check console for errors |
| Button not clickable | Ensure JS loaded, check event listeners |
| API returns error | Check Flask route, verify JSON response |

---

## 📚 Files Reference

| File | Purpose |
|------|---------|
| `design-system.css` | Colors, typography, spacing, shadows |
| `components-ui.css` | Component styles (toasts, modals, buttons) |
| `components.js` | Interactive component classes |
| `base_modern.html` | Base template (extend this) |
| `dashboard_modern.html` | Dashboard example |
| `projects_modern.html` | Projects example |

---

## 🎯 Integration Steps

1. **Load base template** → Extend `base_modern.html`
2. **Add your content** → Use provided component snippets
3. **Connect API** → Use `apiCall()` helper
4. **Show feedback** → Use `Toast.show()` or `Notification.show()`
5. **Test responsive** → Check mobile/tablet views

---

## 📞 Examples Included

- ✅ Dashboard with KPI cards
- ✅ Data table with search/sort
- ✅ Modal forms
- ✅ Filter & pagination
- ✅ Toast notifications
- ✅ Form validation
- ✅ API integration

Copy these patterns to new pages!

---

**Last Updated**: June 2026
**Version**: 1.0
**Browser Support**: Chrome 90+, Firefox 88+, Safari 14+
