# ConnectLink - Quick Reference Guide

## 🚀 Quick Start

### Access the System
- **URL**: `http://localhost:5000`
- **Default Port**: 5000
- **Login**: Username & Password

### Standard Database Tables
```
connectlinkdatabase      - Projects & Client Info
connectlinkinventory     - Hardware Stocks
connectlinktransactions  - Sales Records
stock_additions          - Inventory History
product_categories      - AI Categories
connectlinkusers        - User Accounts
connectlinkadmin        - Admin Settings
```

---

## 📊 BUILDING PROJECTS MODULE

### Create New Project
1. Navigate: **Projects → New Project**
2. Enter:
   - Client Name & Contact
   - Project Description
   - Location & Address
   - Expected Timeline
3. Click **Save**

### Generate Quotation
1. **Projects → Select Project → Quotation**
2. Select Activities (Auto-populate from rates)
3. Add Materials:
   - Item name → Quantity → Unit cost
   - AI auto-calculates total
4. Review Total (Subtotal + Tax)
5. **Export PDF** or **Send via WhatsApp**

### Create Contract
1. **Quotation → Generate Contract**
2. System auto-fills:
   - Parties (Client & ConnectLink)
   - Scope of Work (from quotation)
   - Payment Schedule
   - Terms & Conditions
3. Click **Send to Client** (Email/WhatsApp)

### Track Payment
1. **Project → Payment Tab**
2. View Payment Schedule:
   - Deposit Due: _________
   - Installment 1 Due: _________
   - Installment 2 Due: _________
3. Record Payment:
   - Amount Received
   - Date Received
   - Payment Method
4. **Save** → Auto-updates balance

---

## 🛠️ HARDWARE & POS MODULE

### Add New Product to Inventory

**Method 1: Single Product**
1. **Inventory → Add Product**
2. Enter:
   - **Product Name** (e.g., "2x4x8ft Lumber")
   - **Cost Price**: (e.g., $12)
   - **Retail Price**: (e.g., $15)
   - **Quantity**: (e.g., 50)
   - **Unit Type**: Piece
3. AI Auto-categorizes (98% accuracy)
4. If unsure: Confirm category from dropdown
5. Select **Funding Source**: Profit / Capital
6. Click **Save**

**Method 2: Bulk Import**
1. **Inventory → Bulk Import**
2. Upload CSV with columns:
   ```
   product_name,cost_price,retail_price,quantity,unit_type,funding_source
   "Hammer",8.50,12.00,30,"Piece","Profit"
   "Nails 2in",0.05,0.10,5000,"Box","Capital"
   ```
3. Click **Import** → Verify → Confirm

### Adjust Stock
1. **Inventory → Select Product**
2. **Adjust Stock**:
   - Current: 50 units
   - Remove: 5 units (sale)
   - New Level: 45 units
3. Add note: "Sale - Customer order #123"
4. Click **Save**

### Low Stock Alert
- Automatic when stock < 10 units
- **Action**: Click **Reorder Suggestion**
- Provides suggested quantity based on sales trend

### Process POS Sale
1. **POS → New Transaction**
2. **Search/Scan Product**:
   - Type product name
   - Select from dropdown
3. **Add to Cart**:
   - Product: Hammer
   - Price: $12.00
   - Qty: 3
   - Subtotal: $36.00
4. **Repeat** for other items
5. **Review Cart**:
   - Total: $36.00
   - Tax (10%): $3.60
   - Final: $39.60
6. **Select Payment Method**:
   - Cash
   - Card
   - Account
7. **Process Payment**
8. **Print/Email Receipt**

### AI Product Classification

**How It Works**:
```
Product Name: "3/4 inch copper plumbing pipe"
           ↓
Step 1: Exact match database
        Result: 90% confidence → "Plumbing"
           ↓
Auto-fills category: ✓ Plumbing Accessories
```

**If Unsure (< 90% confidence)**:
- Shows suggestions: Plumbing, Electrical, Building Materials
- You select the best match
- System learns for next time

**New Categories**:
- If product doesn't match any:
  - Suggest new category
  - Type: "Outdoor Equipment"
  - Confirm → Saved for future

---

## 💰 FINANCIAL & PAYMENT MODULE

### Payment Models

**Model 1: Deposit + Installments**
```
Project: $10,000 House Construction

Payment Schedule:
├─ Deposit (20%):       $2,000 [DUE NOW]
├─ After Foundation:    $4,000 [Due: Wk 2]
├─ After Walls:         $3,000 [Due: Wk 5]
└─ Final (Completion):  $1,000 [Due: Wk 8]
```

**Model 2: 50/50**
```
├─ Deposit (50%):       $5,000 [DUE NOW]
└─ Final (50%):         $5,000 [Due: Completion]
```

### Record Payment
1. **Project → Payments**
2. Select Payment Due: "Deposit - $2,000"
3. **Record Payment**:
   - Amount Received: $2,000
   - Date: 2026-04-15
   - Payment Method: Bank Transfer
4. Click **Save & Update**
5. System auto:
   - Updates balance to $8,000
   - Marks payment as "Completed"
   - Generates receipt
   - Sends WhatsApp confirmation

### View Payment History
**Client View**:
1. Click client name
2. **Payment Tab** shows:
   ```
   Deposit:        $2,000  ✓ Paid    [2026-04-15]
   Installment 1:  $4,000  ⏳ Due    [2026-05-15]
   Installment 2:  $3,000  ⏳ Pending [2026-06-15]
   Final:          $1,000  ⏳ Pending [2026-07-15]
   ─────────────────────────────────
   Total Due:      $8,000
   Outstanding:    $8,000
   Paid:           $2,000
   ```

### Send Payment Reminder
1. **Project → Payments**
2. Select Overdue Payment
3. Click **Send Reminder**
4. Choose Channel:
   - ☐ WhatsApp
   - ☐ Email
   - ☐ Both
5. Message auto-fills:
   ```
   Hi [Client Name],
   
   Reminder: Your project payment is due
   Amount: $4,000
   Due: 2026-05-15
   
   Project: House Construction
   Status: In Progress
   
   Please reply to confirm payment receipt.
   
   Thank you!
   ConnectLink
   ```
6. Click **Send**

---

## 📱 COMMUNICATION & INTEGRATION

### Send Document via WhatsApp
1. **Project → Documents**
2. Select Document:
   - ☐ Quotation
   - ☐ Contract
   - ☐ Invoice
   - ☐ Work Plan
3. Click **Send to WhatsApp**
4. System generates PDF
5. Message appears in WhatsApp chat automatically

### Generate Reports

**Sales Report**:
1. **Analytics → Sales Report**
2. Select:
   - Date Range: 2026-04-01 to 2026-04-30
   - Category: All / Specific
3. Click **Generate**
4. View:
   ```
   Daily Revenue:      $12,450
   Items Sold:         234 units
   Top Product:        Lumber ($2,340)
   Labor Tools:        $890
   Avg Transaction:    $53.20
   ```
5. **Export**:
   - PDF (formatted report)
   - Excel (.xlsx spreadsheet)
   - Email to staff

**Project Report**:
1. **Projects → Reports**
2. View:
   - Active Projects: 12
   - Completed (Month): 3
   - Total Revenue: $89,450
   - Outstanding Payment: $12,300
3. Export → Share with team

### AI Chat Query
1. Click **Chat Helper** (bottom right)
2. Ask:
   - "What's my daily revenue?"
   - "How many projects are overdue?"
   - "Which products need reorder?"
   - "Show me payment status"
3. AI analyzes and responds with data
4. Click results to see details

---

## 👥 ADMIN & USER MANAGEMENT

### Create New User
1. **Admin → Users → Add User**
2. Fill:
   - Name: John Smith
   - Email: john@company.com
   - Phone: +1234567890
   - Role: ☐ Admin ☐ Manager ☐ Staff ☐ Viewer
3. Set Permissions:
   - ☑ Can access POS
   - ☑ Can view reports
   - ☐ Can edit projects
   - ☑ Can process payments
4. Initial Password: Auto-generated
5. Click **Save & Send Invite**

### View Activity Log
1. **Admin → Activity Log**
2. Filter by:
   - Date Range
   - User
   - Action Type
3. See:
   ```
   2026-04-15 14:23 | John Smith | Created Project "Corner Store"
   2026-04-15 13:15 | Sarah Ahmed | Sold 5 units Lumber
   2026-04-15 12:45 | Admin | Updated Product Prices
   2026-04-15 11:30 | John Smith | Recorded Payment $2,000
   ```

### System Statistics
1. **Dashboard → Overview**
2. Key Metrics:
   - Total Projects: 45
   - Active: 12
   - Completed: 33
   - Total Clients: 28
   - Active Users: 5
3. Monthly Stats:
   - Revenue: $89,450
   - Profit: $23,400
   - Transactions: 450
   - Avg Order: $198.76

---

## 🔧 QUICK TROUBLESHOOTING

### Issue: Product Not Being Classified
**Solution**:
1. Type product name clearly: "Copper Pipe 3/4 inch"
2. Check spelling
3. If still unsure, create new category
4. System learns from corrections

### Issue: Payment Not Updating
**Solution**:
1. Verify amount matches quotation
2. Check date is correct
3. Click **Refresh Page**
4. Contact Admin if persists

### Issue: WhatsApp Message Not Sent
**Solution**:
1. Check API token (Admin → Settings)
2. Verify client has WhatsApp
3. Check recipient number format
4. Try sending Email instead

### Issue: PDF Not Generating
**Solution**:
1. Check document has all required data
2. Verify images are accessible
3. Try smaller document first
4. Contact Support

### Issue: Slow Performance
**Solution**:
1. Clear browser cache (Ctrl+Shift+Delete)
2. Close other tabs
3. Restart browser
4. Contact Admin to optimize database

---

## 📋 DAILY CHECKLIST

**Morning**:
- ☐ Check payment due today
- ☐ Review new enquiries
- ☐ Check low stock alerts
- ☐ Read overnight messages

**Throughout Day**:
- ☐ Record sales transactions
- ☐ Update project progress
- ☐ Process client payments
- ☐ Send quotations

**End of Day**:
- ☐ Reconcile cash/transactions
- ☐ Update payment records
- ☐ Send due reminders
- ☐ Back up critical data

**Weekly**:
- ☐ Generate sales report
- ☐ Review profit margins
- ☐ Check inventory levels
- ☐ Analyze project timeline

**Monthly**:
- ☐ Financial close
- ☐ Staff performance review
- ☐ Update product prices
- ☐ Plan next month

---

## 🔐 Security & Backup

### Change Password
1. **Settings → Security**
2. Enter:
   - Current Password
   - New Password
   - Confirm New Password
3. Click **Update**

### Backup Database
```bash
# Backup
pg_dump connectlinkdata > backup_$(date +%Y%m%d).sql

# Restore
psql connectlinkdata < backup_20260415.sql
```

### Log Out
1. Click **User Profile** (top right)
2. Select **Logout**
3. Redirects to login page

---

## 📞 SUPPORT & HELP

**Common Needs**:
- 🔍 Help: Press **?** or click **Help**
- 🎓 Tutorial: Dashboard → Video Tutorials
- 📧 Support: support@connectlink.co.zw
- 📱 WhatsApp: +1234567890
- 💬 Chat: In-app Help Chat (bottom right)

**Version**: 2.0  
**Last Updated**: April 2026  
**Support Hours**: Monday-Friday 8AM-5PM GMT
