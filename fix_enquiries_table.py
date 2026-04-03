#!/usr/bin/env python3
"""Fix enquiries table styling to match other tables"""

file_path = r"c:\Users\Lenovo\Documents\GitHub\connectlink\templates\adminpage.html"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Old HTML - the complex bootstrap-heavy row generation
old_html = '''        html += `
            <tr class="${isSelected ? 'table-primary' : ''}">
                <td class="px-4 py-3">
                    <div class="d-flex align-items-center">
                        <div class="form-check me-2">
                            <input class="form-check-input enquiry-checkbox" 
                                   type="checkbox" 
                                   value="${enquiry.id}"
                                   ${isSelected ? 'checked' : ''}
                                   onchange="toggleEnquirySelection(this)">
                        </div>
                        <span class="text-muted small">${index + 1}</span>
                    </div>
                </td>
                <td class="px-4 py-3">
                    <span class="badge bg-dark rounded-pill px-3 py-1">
                        ${enquiry.id}
                    </span>
                </td>
                <td class="px-4 py-3">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-whatsapp text-success me-3"></i>
                        <div class="flex-grow-1">
                            <div class="fw-bold">${formatWhatsAppNumber(enquiry.wanumber)}</div>
                            <small class="text-muted d-block">Click to copy or message</small>
                        </div>
                        ${enquiry.wanumber ? `
                            <div class="d-flex gap-1">
                                <button class="btn btn-sm btn-outline-success" 
                                        onclick="copyWhatsAppNumber('${enquiry.wanumber}')"
                                        title="Copy Number">
                                    <i class="bi bi-copy"></i>
                                </button>
                                <a href="https://wa.me/${enquiry.wanumber}" 
                                   target="_blank" 
                                   class="btn btn-sm btn-success"
                                   title="Message on WhatsApp">
                                    <i class="bi bi-whatsapp"></i>
                                </a>
                            </div>
                        ` : ''}
                    </div>
                </td>
                <td class="px-4 py-3">
                    <div class="d-flex align-items-center">
                        <i class="bi ${typeConfig.icon} me-3" style="color: ${typeConfig.color}"></i>
                        <span class="badge rounded-pill px-3 py-1" 
                              style="background-color: ${typeConfig.color}; color: white;">
                            ${typeConfig.label}
                        </span>
                    </div>
                </td>
                <td class="px-4 py-3 text-center">
                    <div class="d-flex justify-content-center gap-1">
                        <button class="btn btn-sm btn-outline-primary" 
                                onclick="viewEnquiryDetails(${enquiry.id})"
                                title="View Details">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" 
                                onclick="deleteEnquiry(${enquiry.id})"
                                title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;'''

# New HTML - simplified to match table-theme
new_html = '''        html += `
            <tr>
                <td>
                    <input class="form-check-input enquiry-checkbox" 
                           type="checkbox" 
                           value="${enquiry.id}"
                           ${isSelected ? 'checked' : ''}
                           onchange="toggleEnquirySelection(this)">
                </td>
                <td>
                    ${enquiry.id}
                </td>
                <td>
                    ${enquiry.wanumber ? `
                        <a href="https://wa.me/${enquiry.wanumber}" target="_blank" style="text-decoration: none; color: var(--dark-blue-deep);">
                            ${formatWhatsAppNumber(enquiry.wanumber)}
                        </a>
                    ` : 'N/A'}
                </td>
                <td>
                    <span style="background-color: ${typeConfig.color}; color: white; padding: 0.3rem 0.6rem; border-radius: 0.25rem; font-size: 0.75rem;">
                        ${typeConfig.label}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" 
                            onclick="viewEnquiryDetails(${enquiry.id})"
                            style="margin-right: 0.25rem;"
                            title="View Details">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="deleteEnquiry(${enquiry.id})"
                            title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;'''

# Replace
if old_html in content:
    content = content.replace(old_html, new_html)
    print("✓ Successfully replaced table row HTML")
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ File saved successfully")
else:
    print("✗ Could not find the old HTML block to replace")
    print("The structure might have changed or the exact string doesn't match.")
