"""
ConnectLink React App Integration Example
==========================================

This file demonstrates how to integrate the new modern React-like templates
with your existing Flask backend. Copy these patterns to your ConnectLink.py file.
"""

from flask import render_template, request, jsonify, session
from functools import wraps

# ==================== HELPER DECORATORS ====================

def api_response(success=True, data=None, message=""):
    """Standardize API responses for React app compatibility"""
    return jsonify({
        'success': success,
        'data': data,
        'message': message
    })

def json_error(message, status_code=400):
    """Return error response in standard format"""
    return jsonify({
        'success': False,
        'message': message
    }), status_code

# ==================== MODERN TEMPLATE ROUTES ====================

@app.route('/dashboard-modern')
def dashboard_modern():
    """New modern dashboard page"""
    if 'userid' not in session:
        return redirect('/login')
    
    return render_template('dashboard_modern.html', 
                         user=session.get('user_name'))

@app.route('/projects-modern')
def projects_modern():
    """New modern projects management page"""
    if 'userid' not in session:
        return redirect('/login')
    
    return render_template('projects_modern.html',
                         user=session.get('user_name'))

# ==================== API ENDPOINTS FOR REACT APP ====================

@app.route('/api/dashboard/stats', methods=['GET'])
def api_dashboard_stats():
    """Get dashboard statistics for KPI cards"""
    try:
        with get_db() as (cursor, connection):
            # Total projects
            cursor.execute("SELECT COUNT(*) FROM connectlinkdatabase")
            total_projects = cursor.fetchone()[0]
            
            # Active quotations
            cursor.execute("SELECT COUNT(*) FROM quotations WHERE status = 'active'")
            active_quotations = cursor.fetchone()[0]
            
            # Completed projects
            cursor.execute("SELECT COUNT(*) FROM connectlinkdatabase WHERE projectcompletionstatus = 'Completed'")
            completed = cursor.fetchone()[0]
            
            # Total contract value
            cursor.execute("SELECT COALESCE(SUM(totalcontractamount), 0) FROM connectlinkdatabase")
            total_revenue = float(cursor.fetchone()[0])
            
            return api_response(data={
                'total_projects': total_projects,
                'active_quotations': active_quotations,
                'completed_projects': completed,
                'total_revenue': total_revenue
            })
    
    except Exception as e:
        return json_error(str(e))

@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    """Get projects list with filtering"""
    try:
        limit = request.args.get('limit', 1000, type=int)
        offset = request.args.get('offset', 0, type=int)
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        
        with get_db() as (cursor, connection):
            # Base query
            query = "SELECT * FROM connectlinkdatabase WHERE 1=1"
            params = []
            
            # Add search filter
            if search:
                query += " AND (clientname ILIKE %s OR projectname ILIKE %s OR projectlocation ILIKE %s)"
                search_term = f"%{search}%"
                params.extend([search_term, search_term, search_term])
            
            # Add status filter
            if status_filter:
                query += " AND projectcompletionstatus = %s"
                params.append(status_filter)
            
            # Add ordering and limit
            query += " ORDER BY id DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, tuple(params))
            projects = cursor.fetchall()
            
            # Convert to dictionary format
            columns = [desc[0] for desc in cursor.description]
            projects_list = [
                dict(zip(columns, project)) for project in projects
            ]
            
            return api_response(data={
                'projects': projects_list,
                'total': len(projects_list)
            })
    
    except Exception as e:
        return json_error(str(e))

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def api_get_project(project_id):
    """Get single project details"""
    try:
        with get_db() as (cursor, connection):
            cursor.execute("SELECT * FROM connectlinkdatabase WHERE id = %s", (project_id,))
            result = cursor.fetchone()
            
            if not result:
                return json_error("Project not found", 404)
            
            columns = [desc[0] for desc in cursor.description]
            project = dict(zip(columns, result))
            
            return api_response(data={'project': project})
    
    except Exception as e:
        return json_error(str(e))

@app.route('/api/projects', methods=['POST'])
def api_create_project():
    """Create new project"""
    try:
        data = request.json
        
        # Validate required fields
        required = ['clientname', 'projectname', 'totalcontractamount']
        if not all(field in data for field in required):
            return json_error("Missing required fields")
        
        with get_db() as (cursor, connection):
            cursor.execute("""
                INSERT INTO connectlinkdatabase (
                    clientname, clientemail, clientwanumber,
                    projectname, projectlocation, projectdescription,
                    totalcontractamount, paymentmethod,
                    depositorbullet, datedepositorbullet,
                    projectcompletionstatus
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                data.get('clientname'),
                data.get('clientemail'),
                data.get('clientwanumber'),
                data.get('projectname'),
                data.get('projectlocation'),
                data.get('projectdescription'),
                data.get('totalcontractamount'),
                data.get('paymentmethod'),
                data.get('depositorbullet'),
                data.get('datedepositorbullet'),
                'Ongoing'
            ))
            
            project_id = cursor.fetchone()[0]
            connection.commit()
            
            return api_response(data={'project_id': project_id}, 
                              message="Project created successfully")
    
    except Exception as e:
        return json_error(str(e))

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def api_update_project(project_id):
    """Update project"""
    try:
        data = request.json
        
        # Build dynamic UPDATE query
        update_fields = []
        params = []
        
        allowed_fields = [
            'clientname', 'clientemail', 'clientwanumber',
            'projectname', 'projectlocation', 'projectdescription',
            'totalcontractamount', 'paymentmethod',
            'projectcompletionstatus'
        ]
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])
        
        if not update_fields:
            return json_error("No fields to update")
        
        params.append(project_id)
        
        with get_db() as (cursor, connection):
            query = f"UPDATE connectlinkdatabase SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(query, tuple(params))
            connection.commit()
            
            return api_response(message="Project updated successfully")
    
    except Exception as e:
        return json_error(str(e))

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def api_delete_project(project_id):
    """Delete project (soft delete)"""
    try:
        with get_db() as (cursor, connection):
            cursor.execute("""
                UPDATE connectlinkdatabase 
                SET is_deleted = TRUE 
                WHERE id = %s
            """, (project_id,))
            connection.commit()
            
            return api_response(message="Project deleted successfully")
    
    except Exception as e:
        return json_error(str(e))

# ==================== QUOTATIONS API ====================

@app.route('/api/quotations', methods=['GET'])
def api_get_quotations():
    """Get quotations list"""
    try:
        with get_db() as (cursor, connection):
            cursor.execute("""
                SELECT id, name, amount, client, status, created_at 
                FROM quotations 
                ORDER BY created_at DESC 
                LIMIT 100
            """)
            
            results = cursor.fetchall()
            quotations = [
                {
                    'id': r[0],
                    'name': r[1],
                    'amount': float(r[2]),
                    'client': r[3],
                    'status': r[4],
                    'created_at': r[5].isoformat() if r[5] else None
                }
                for r in results
            ]
            
            return api_response(data={'quotations': quotations})
    
    except Exception as e:
        return json_error(str(e))

@app.route('/api/quotations', methods=['POST'])
def api_create_quotation():
    """Create quotation"""
    try:
        data = request.json
        
        with get_db() as (cursor, connection):
            cursor.execute("""
                INSERT INTO quotations (name, amount, client, status)
                VALUES (%s, %s, %s, 'pending')
                RETURNING id
            """, (
                data.get('name'),
                data.get('amount'),
                data.get('client')
            ))
            
            quotation_id = cursor.fetchone()[0]
            connection.commit()
            
            return api_response(
                data={'quotation_id': quotation_id},
                message="Quotation created successfully"
            )
    
    except Exception as e:
        return json_error(str(e))

# ==================== TRANSACTIONS API ====================

@app.route('/api/transactions', methods=['GET'])
def api_get_transactions():
    """Get transactions with pagination"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        with get_db() as (cursor, connection):
            cursor.execute("""
                SELECT id, transaction_number, total, payment_method, 
                       status, created_at
                FROM transactions
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            results = cursor.fetchall()
            transactions = [
                {
                    'id': r[0],
                    'transaction_number': r[1],
                    'total': float(r[2]),
                    'payment_method': r[3],
                    'status': r[4],
                    'created_at': r[5].isoformat() if r[5] else None
                }
                for r in results
            ]
            
            return api_response(data={'transactions': transactions})
    
    except Exception as e:
        return json_error(str(e))

@app.route('/api/transactions/summary', methods=['GET'])
def api_transaction_summary():
    """Get transaction summary for dashboard"""
    try:
        with get_db() as (cursor, connection):
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(total), 0) as total_sales,
                    COUNT(*) as transaction_count,
                    COUNT(DISTINCT DATE(created_at)) as transaction_days
                FROM transactions
                WHERE status = 'completed'
            """)
            
            result = cursor.fetchone()
            
            return api_response(data={
                'total_sales': float(result[0]),
                'transaction_count': result[1],
                'transaction_days': result[2]
            })
    
    except Exception as e:
        return json_error(str(e))

# ==================== USER PROFILE API ====================

@app.route('/api/profile', methods=['GET'])
def api_get_profile():
    """Get current user profile"""
    try:
        user_id = session.get('userid')
        if not user_id:
            return json_error("Not authenticated", 401)
        
        with get_db() as (cursor, connection):
            cursor.execute("""
                SELECT id, name, email, whatsapp, datecreated
                FROM connectlinkusers
                WHERE id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return json_error("User not found", 404)
            
            profile = {
                'id': result[0],
                'name': result[1],
                'email': result[2],
                'whatsapp': result[3],
                'created_at': result[4].isoformat() if result[4] else None
            }
            
            return api_response(data={'profile': profile})
    
    except Exception as e:
        return json_error(str(e))

@app.route('/api/profile', methods=['PUT'])
def api_update_profile():
    """Update user profile"""
    try:
        user_id = session.get('userid')
        if not user_id:
            return json_error("Not authenticated", 401)
        
        data = request.json
        
        with get_db() as (cursor, connection):
            cursor.execute("""
                UPDATE connectlinkusers
                SET name = %s, email = %s, whatsapp = %s
                WHERE id = %s
            """, (
                data.get('name'),
                data.get('email'),
                data.get('whatsapp'),
                user_id
            ))
            
            connection.commit()
            
            return api_response(message="Profile updated successfully")
    
    except Exception as e:
        return json_error(str(e))

# ==================== REFERENCE IMPLEMENTATION ====================

"""
HOW TO USE THESE ENDPOINTS IN YOUR REACT TEMPLATES:

JavaScript:
-----------

// In your dashboard_modern.html or projects_modern.html

async function loadData() {
    try {
        const res = await apiCall('/api/projects');
        const res2 = await apiCall('/api/dashboard/stats');
        
        if (res.success) {
            renderProjects(res.data.projects);
        }
        if (res2.success) {
            updateKPIs(res2.data);
        }
    } catch (error) {
        Toast.show('Failed to load data', 'error');
    }
}

async function createProject(projectData) {
    try {
        const res = await apiCall('/api/projects', {
            method: 'POST',
            body: JSON.stringify(projectData)
        });
        
        if (res.success) {
            Toast.show('Project created successfully', 'success');
            loadData(); // Refresh
        }
    } catch (error) {
        Toast.show('Failed to create project', 'error');
    }
}
"""

# ==================== NOTES ====================

"""
INTEGRATION CHECKLIST:

1. Add these routes to your ConnectLink.py file
2. Ensure database tables exist:
   - connectlinkdatabase
   - quotations
   - transactions
   - connectlinkusers
3. Test API endpoints with curl or Postman
4. Update Flask routes to return new template where appropriate
5. Modify JavaScript in templates to use your actual API endpoints
6. Test in browser DevTools Network tab
7. Verify error handling works
8. Test with different screen sizes (mobile, tablet, desktop)

EXPECTED RESPONSE FORMAT:
{
    "success": true,
    "data": {...},
    "message": "Success message"
}

ERROR RESPONSE FORMAT:
{
    "success": false,
    "message": "Error message"
}
"""
