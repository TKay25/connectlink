# ConnectLink - System Architecture & Integration Guide

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT INTERFACE (Frontend)                 │
│  HTML5 / CSS3 / JavaScript / Bootstrap 5.3                         │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      FLASK API LAYER (Backend)                       │
│  Routes / Controllers / Business Logic (Python)                     │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────┐
│                 MODULE SERVICES (Domain Logic)                       │
│ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │ Projects    │ │ Hardware/POS │ │ Financial    │ │ Communication│ │
│ │ Manager     │ │ Manager      │ │ Manager      │ │ Manager      │ │
│ └─────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────┐
│              DATABASE ACCESS LAYER (ORM / Queries)                   │
│  PostgreSQL Driver / Connection Pool / Query Builder                │
└──────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL DATABASE                               │
│ Tables: Projects | Inventory | Transactions | Users | Payments      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Module Interaction Diagram

```
                         ┌─────────────────────┐
                         │  Admin Dashboard    │
                         │  - Statistics       │
                         │  - User Management  │
                         │  - Reports          │
                         └─────────────────────┘
                                    ↑
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                 ↓
        ┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
        │ Projects Module  │ │ Hardware/POS │ │ Financial Mgmt  │
        │                  │ │ Module       │ │ Module          │
        │ - Projects       │ │              │ │                 │
        │ - Quotations     │ │ - Inventory  │ │ - Payments      │
        │ - Contracts      │ │ - Sales      │ │ - Deposits      │
        │ - Work Plans     │ │ - AI Class   │ │ - Installments  │
        │ - Schedules      │ │ - Analytics  │ │ - Reminders     │
        └──────────────────┘ └──────────────┘ └─────────────────┘
                    ↓                 ↓                 ↓
                    │              Share              │
                    └─────────────────┬─────────────────┘
                                      ↓
                    ┌──────────────────────────────────┐
                    │ Communication Module              │
                    │ - WhatsApp Integration            │
                    │ - PDF Generation                  │
                    │ - Email Notifications             │
                    │ - AI Chat Support                 │
                    └──────────────────────────────────┘
```

---

## Module-by-Module Architecture

### 1️⃣ PROJECTS MODULE

**Responsibility**: End-to-end project lifecycle management

**Key Components**:
```python
# database_models.py
class Project:
    id: int
    client_id: int
    project_name: str
    description: str
    location: str
    start_date: datetime
    end_date: datetime
    status: str  # pending, in_progress, completed
    total_budget: float
    expenditure: float
    created_at: datetime

# projects_manager.py
class ProjectManager:
    def create_project(client_id, details) → Project
    def update_project(project_id, updates) → Project
    def get_project_timeline() → List[Milestone]
    def archive_project(project_id) → bool
```

**Interactions**:
- ✅ Calls **Quotation System** to generate cost estimates
- ✅ Generates **Contracts** from approved quotations
- ✅ Tracks **Payment Plans** via Financial Module
- ✅ Creates **Work Plans** for execution
- ✅ Sends **Documents** via Communication Module

**Database Tables**:
```
connectlinkdatabase
├── Projects (ID, ClientID, Name, Status, Budget, etc.)
├── Quotations (ID, ProjectID, Items, Total)
├── Contracts (ID, ProjectID, TermsContent)
└── WorkPlans (ID, ProjectID, Activities, Timeline)
```

---

### 2️⃣ HARDWARE & POS MODULE

**Responsibility**: Inventory management and point-of-sale operations

**Architecture**:
```python
# inventory_models.py
class Product:
    id: int
    name: str  # AI-classified
    category: str  # Main category
    sub_category: str  # Sub category
    cost_price: float
    retail_price: float
    stock_level: int
    unit_type: str
    funding_source: str  # profit/capital
    created_at: datetime

class StockAddition:
    id: int
    product_id: int
    quantity_added: int
    date_added: datetime
    notes: str

# AI_classifier.py
class ProductClassifier:
    def classify_product(name: str) → (category: str, confidence: float)
    def get_suggestions(name: str) → List[Suggestions]
    def create_new_category(name: str) → bool
    def learn_from_correction(name: str, correct_category: str) → None

# pos_manager.py
class POSManager:
    def create_transaction(items: List) → Transaction
    def process_payment(transaction_id, amount, method) → Receipt
    def generate_receipt(transaction_id) → PDF
    def record_sale(product_id, quantity) → bool
```

**AI Classification Algorithm**:
```
Input: Product Name
  ↓
Step 1: Exact Match Search (Database lookup)
  • Result: 95% confidence → Return category
  ↓
Step 2: Keyword Match (Tokenize & match)
  • "3/4 copper plumbing pipe" → ["plumbing", "pipe"]
  • Result: 50-80% confidence
  ↓
Step 3: Fuzzy Match (Similarity matching)
  • Compare to existing products (fuzzywuzzy)
  • Result: 40-70% confidence
  ↓
Step 4: Fallback (Ask user)
  • Suggest top 3 matches
  • User confirms or creates new
  ↓
Output: Category + Confidence
  • ≥90%: Auto-save
  • <90%: Request confirmation
```

**Database Tables**:
```
connectlinkinventory
├── Products (ID, Name, Category, Price, Stock)
├── StockAdditions (ID, ProductID, Quantity, Date)
└── ProductCategories (ID, Name, Description)

connectlinktransactions
├── Transactions (ID, Date, Total, Items)
├── TransactionItems (TransID, ProductID, Qty, Price)
└── Receipts (ID, TransID, PDF, PrintDate)
```

---

### 3️⃣ FINANCIAL MODULE

**Responsibility**: Payment processing, tracking, and financial reporting

**Architecture**:
```python
# payment_models.py
class Payment:
    id: int
    project_id: int
    amount_due: float
    amount_received: float
    due_date: datetime
    received_date: datetime
    status: str  # pending, received, overdue, partial
    payment_method: str  # cash, card, bank_transfer

class PaymentSchedule:
    id: int
    project_id: int
    phases: List[PaymentPhase]
    total_amount: float
    deposits: float
    installments: float

# payment_manager.py
class PaymentManager:
    def create_payment_schedule(project_id, phases) → PaymentSchedule
    def record_payment(payment_id, amount, date, method) → bool
    def generate_reminder(payment_id) → ReminderMessage
    def calculate_late_fees(payment_id) → float
    def get_payment_history(project_id) → List[Payments]
    
# financial_analyzer.py
class FinancialAnalytics:
    def calculate_profit(period: str) → float
    def get_cash_flow_statement(period: str) → Statement
    def get_project_profitability(project_id) → Report
    def generate_financial_report(period: str) → PDF
```

**Payment Workflows**:

**Workflow 1: Deposit + Installments**
```
Total Project: $10,000
├─ Create Schedule
│  ├─ Deposit: $2,000 (20%) - Due now
│  ├─ Phase 1: $4,000 (40%) - Due after foundation
│  ├─ Phase 2: $3,000 (30%) - Due after walls
│  └─ Final: $1,000 (10%) - Due at completion
├─ Record Deposit: $2,000 received
│  └─ Status: Deposit Complete
│     Outstanding: $8,000
├─ Send Reminder: Phase 1 due
├─ Record Phase 1: $4,000 received
│  └─ Outstanding: $4,000
└─ Continue until final payment
```

**Database Tables**:
```
payments
├── PaymentSchedules (ID, ProjectID, TotalAmount)
├── PaymentPhases (ID, ScheduleID, Amount, DueDate, Status)
└── PaymentRecords (ID, PhaseID, AmountReceived, DateReceived)

financial_reports
├── DailyRevenue (Date, Total, Count)
├── ProjectProfitability (ProjectID, Revenue, Cost, Profit)
└── CashFlow (Date, Inflow, Outflow, Balance)
```

---

### 4️⃣ COMMUNICATION MODULE

**Responsibility**: Multi-channel communication and document delivery

**Architecture**:
```python
# communication_models.py
class Message:
    id: int
    recipient_id: int
    channel: str  # whatsapp, email, sms
    message_type: str  # text, document, reminder
    content: str
    status: str  # pending, sent, delivered, failed
    created_at: datetime

class PDFDocument:
    id: int
    document_type: str  # quotation, contract, invoice, receipt
    related_id: int  # project_id, transaction_id, etc
    file_path: str
    created_at: datetime

# whatsapp_service.py
class WhatsAppService:
    def send_text_message(to: str, message: str) → Message
    def send_document(to: str, document_path: str) → Message
    def send_reminder(client_id: int, payment_id: int) → Message
    def format_message_template(template_name: str, data: dict) → str
    
# pdf_generator.py
class PDFGenerator:
    def generate_quotation(quotation_id) → PDF
    def generate_contract(contract_id) → PDF
    def generate_invoice(invoice_id) → PDF
    def generate_receipt(transaction_id) → PDF
    def generate_report(report_id) → PDF
    
# ai_chat_service.py
class AIChatService:
    def process_query(query: str) → Response
    def fetch_context(query_type: str) → Data
    def generate_response(context: dict) → str
    def send_to_gemini_api(prompt: str) → str
```

**Message Flow**:
```
User Action (e.g., "Send Quotation via WhatsApp")
  ↓
Get Quotation Data (SQL Query)
  ↓
Generate PDF Document (weasyprint)
  ↓
Format WhatsApp Message
  ├─ Client Name
  ├─ Project Details
  ├─ PDF attachment
  └─ Call-to-action
  ↓
Send via WhatsApp API (Meta)
  ├─ Authenticate
  ├─ Send Payload
  └─ Get Response
  ↓
Log Message Status
  ├─ Pending
  ├─ Sent
  ├─ Delivered
  └─ Failed (with reason)
  ↓
User Notification: "✓ Message sent successfully"
```

**Database Tables**:
```
communications
├── Messages (ID, RecipientID, Channel, Status, Content)
├── PDFDocuments (ID, Type, RelatedID, FilePath)
└── MessageLog (ID, MessageID, Timestamp, Status, Response)
```

---

## Data Flow Integration

### Flow 1: Project to Payment

```
Step 1: PROJECT CREATION
├─ User creates: "House Construction - $10,000"
│  └─ Saved to: Projects table
│
Step 2: QUOTATION GENERATION
├─ AI classifies materials
├─ Calculates labor costs
├─ Total: $10,000
│  └─ Saved to: Quotations table
│
Step 3: CONTRACT GENERATION
├─ Auto-fill from quotation
├─ Add payment schedule: 20% + 40% + 30% + 10%
│  └─ Saved to: Contracts table
│
Step 4: PAYMENT SCHEDULE CREATION
├─ Deposit: $2,000 (20%)
├─ Phase 1: $4,000 (40%)
├─ Phase 2: $3,000 (30%)
├─ Final: $1,000 (10%)
│  └─ Saved to: PaymentSchedules table
│
Step 5: SEND TO CLIENT
├─ Generate PDF (Contract)
├─ Send via WhatsApp
├─ Track delivery
│  └─ Saved to: Messages, PDFDocuments tables
│
Step 6: RECORD PAYMENT
├─ Client pays $2,000 deposit
├─ Record in system
├─ Update balance
├─ Send receipt
│  └─ Saved to: PaymentRecords table
│
Step 7: TRACK & REMIND
├─ Check Phase 1 due date
├─ Send reminder: "Payment due in 3 days"
├─ Record payment when received
│  └─ Saved to: Messages, PaymentRecords tables
```

### Flow 2: Hardware Sale to Report

```
Step 1: SALES TRANSACTION
├─ Customer buys: 5 Hammers ($12 each = $60)
│  └─ Saved to: Transactions table
│
Step 2: UPDATE INVENTORY
├─ Reduce stock
├─ Old: 50 units
├─ New: 45 units
│  └─ Saved to: Products, StockAdditions tables
│
Step 3: CALCULATE PROFIT
├─ Cost per unit: $8
├─ Revenue: $60
├─ Profit: $60 - (5×$8) = $20
│  └─ Calculated & stored in transaction
│
Step 4: GENERATE RECEIPT
├─ Create PDF receipt
├─ Send to customer (Email/WhatsApp)
│  └─ Saved to: PDFDocuments, Messages tables
│
Step 5: ANALYTICS TRACKING
├─ Add to daily sales: $60
├─ Category sales (Tools): +$60
├─ Profit tracking: +$20
│  └─ Aggregated in queries
│
Step 6: MONTHLY REPORT
├─ Total revenue: $12,450
├─ Total profit: $3,560
├─ Top product: Lumber
├─ Export to Excel/PDF
│  └─ Generated on-demand
```

---

## Key Integration Points

### 1. Projects → Financial
- **Connection**: ProjectID links Projects to PaymentSchedules
- **Data Passed**: Project total budget → Payment schedule amount
- **Trigger**: Contract approved → Create payment schedule

### 2. Hardware → Financial
- **Connection**: Each transaction contributes to daily revenue
- **Data Passed**: Transaction amount → Financial reports
- **Trigger**: Sale recorded → Update financial metrics

### 3. All Modules → Communication
- **Connection**: All modules can trigger messages/documents
- **Data Passed**: Project/Transaction data → Message templates
- **Trigger**: Action completed → Send notification

### 4. Projects → Hardware (Optional)
- **Connection**: Project can require hardware materials
- **Use Case**: Integrate material list with inventory
- **Example**: Project needs "50 units Lumber" → Check stock

---

## Database Schema Overview

```
connectlinkdatabase (Projects & Clients)
├── projects (id, client_id, name, status, total_budget, ...)
├── clients (id, name, contact, email, address, ...)
├── quotations (id, project_id, items, total_cost, ...)
├── contracts (id, project_id, content, signed_date, ...)
└── work_plans (id, project_id, activities, timeline, ...)

connectlinkinventory (Hardware Management)
├── products (id, name, category, cost_price, retail_price, stock_level, ...)
├── product_categories (id, name, description)
└── stock_additions (id, product_id, quantity, date_added, ...)

connectlinktransactions (Sales Records)
├── transactions (id, date, total_amount, payment_method, ...)
├── transaction_items (id, transaction_id, product_id, quantity, price, ...)
└── receipts (id, transaction_id, pdf_path, ...)

payments (Financial Tracking)
├── payment_schedules (id, project_id, total_amount, ...)
├── payment_phases (id, schedule_id, amount, due_date, status, ...)
└── payment_records (id, phase_id, amount_received, date_received, ...)

communications (Messages & Documents)
├── messages (id, recipient_id, channel, content, status, ...)
├── pdf_documents (id, type, related_id, file_path, ...)
└── message_log (id, message_id, timestamp, status, ...)

system_tables
├── users (id, username, email, role, last_login, ...)
├── audit_log (id, user_id, action, timestamp, details, ...)
└── settings (key, value)
```

---

## API Endpoint Structure

```
Projects Module
├── GET    /api/projects                    - List all projects
├── POST   /api/projects                    - Create project
├── GET    /api/projects/<id>               - Get project details
├── PUT    /api/projects/<id>               - Update project
├── DELETE /api/projects/<id>               - Delete project
├── POST   /api/projects/<id>/quotation     - Generate quotation
├── POST   /api/projects/<id>/contract      - Generate contract
├── POST   /api/projects/<id>/payment       - Create payment schedule
└── GET    /api/projects/<id>/payment       - View payment status

Hardware Module
├── GET    /api/products                    - List inventory
├── POST   /api/products                    - Add product
├── PUT    /api/products/<id>               - Update product
├── DELETE /api/products/<id>               - Delete product
├── PUT    /api/products/<id>/stock         - Adjust stock
├── POST   /api/products/bulk-import        - Bulk import
├── POST   /api/ai/classify                 - AI classification
└── GET    /api/pos/transactions            - Get sales history

Financial Module
├── POST   /api/payments                    - Record payment
├── GET    /api/payments/<id>               - Get payment details
├── GET    /api/payments/<id>/history       - Payment history
├── POST   /api/payments/<id>/reminder      - Send reminder
└── GET    /api/reports/financial           - Financial report

Communication Module
├── POST   /api/messages/whatsapp           - Send WhatsApp message
├── POST   /api/messages/email              - Send email
├── POST   /api/pdf/generate                - Generate PDF
├── POST   /api/ai/chat                     - AI query
└── GET    /api/messages/status/<id>        - Message status
```

---

## Security Architecture

```
┌─────────────────────────────────────────┐
│         Authentication Layer             │
│  - Login/Logout                          │
│  - Session Management                    │
│  - Password Hashing                      │
│  - 2FA (Optional)                        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Authorization Layer                 │
│  - Role-Based Access Control (RBAC)      │
│  - Permission Checking                   │
│  - Admin-only endpoints                  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│        Data Validation Layer              │
│  - Input Sanitization                    │
│  - SQL Injection Prevention                │
│  - XSS Protection                        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Audit Logging Layer              │
│  - Track all modifications               │
│  - Record user actions                   │
│  - Timestamp all events                  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Database Layer                   │
│  - PostgreSQL with encryption            │
│  - Regular backups                       │
│  - Access control                        │
└─────────────────────────────────────────┘
```

---

## Deployment Architecture

```
Development Environment
├── Flask Debug Server (port 5000)
├── PostgreSQL (local)
└── Environment: FLASK_ENV=development

Production Environment
├── Gunicorn/uWSGI (WSGI Server)
├── Nginx (Reverse Proxy)
├── PostgreSQL (remote, secure)
├── SSL/TLS (HTTPS)
└── Environment: FLASK_ENV=production

Infrastructure
├── Web Server (application runs here)
├── Database Server (PostgreSQL)
├── File Storage (PDFs, documents)
├── API Services
│  ├── WhatsApp Business API
│  ├── Google Gemini API
│  └── Email/SMS Service
└── Monitoring & Logging
```

---

## Performance Optimization

### Database Indexing
```sql
-- Projects module
CREATE INDEX idx_projects_client_id ON connectlinkdatabase(client_id);
CREATE INDEX idx_projects_status ON connectlinkdatabase(status);

-- Inventory module
CREATE INDEX idx_products_category ON connectlinkinventory(category);
CREATE INDEX idx_products_stock ON connectlinkinventory(stock_level);

-- Transactions module
CREATE INDEX idx_transactions_date ON connectlinktransactions(date);
CREATE INDEX idx_transactions_product_id ON connectlinktransactions(product_id);

-- Payments module
CREATE INDEX idx_payments_project_id ON payments(project_id);
CREATE INDEX idx_payments_status ON payments(status);
```

### Caching Strategy
```python
# Cache frequently accessed data
@app.cache.cached(timeout=300)  # 5 minutes
def get_daily_sales():
    return calculate_sales()

# Cache user-specific data
@app.cache.cached(timeout=600, key_prefix='user_')
def get_user_projects(user_id):
    return query_user_projects(user_id)
```

### API Response Optimization
```python
# Use pagination for large datasets
def get_transactions(page=1, per_page=50):
    return Transaction.query.paginate(page, per_page)

# Use lazy loading for related data
def get_project(project_id):
    project = Project.query.filter_by(id=project_id).first()
    # Load payments only when needed
    return project
```

---

## Error Handling Strategy

```python
# Global error handler
@app.errorhandler(Exception)
def handle_error(error):
    # Log error
    app.logger.error(f"Error: {error}")
    
    # Send notification (if critical)
    if error.is_critical:
        send_alert_to_admin(error)
    
    # Return user-friendly message
    return {
        'success': False,
        'message': 'An error occurred',
        'error_id': generate_error_id()
    }, 500

# Module-specific error handling
class ProjectManager:
    def create_project(self, data):
        try:
            project = Project(**data)
            db.session.add(project)
            db.session.commit()
            return project
        except Exception as e:
            db.session.rollback()
            raise ProjectCreationError(str(e))
```

---

## This architecture enables**:
✅ **Modularity** - Each module operates independently  
✅ **Scalability** - Easy to add new modules or features  
✅ **Maintainability** - Clear separation of concerns  
✅ **Reusability** - Components shared across modules  
✅ **Testability** - Each module can be tested independently  
✅ **Security** - Multiple layers of protection  
✅ **Performance** - Optimized queries and caching  
✅ **Reliability** - Error handling and logging throughout