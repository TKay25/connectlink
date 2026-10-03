"""Throwaway mock server to preview templates/pos-system.html (offline verification).
Delete after use."""
from flask import Flask, render_template, jsonify, request, send_from_directory
import json

app = Flask(__name__, template_folder='templates', static_folder='static')

PRODUCTS = [
    {"id": 1, "name": "PVC Pipe 110mm", "category": "Plumbing", "subcategory": "Pipes",
     "sell_price": 12.5, "buy_price": 8.0, "stock": 40, "unit": "piece", "barcode": "1001"},
    {"id": 2, "name": "Circuit Breaker 20A", "category": "Electricals", "subcategory": "Breakers",
     "sell_price": 18.0, "buy_price": 11.0, "stock": 0, "unit": "piece", "barcode": "1002"},
    {"id": 3, "name": "Claw Hammer", "category": "DIY", "subcategory": "Hand Tools",
     "sell_price": 9.0, "buy_price": 5.5, "stock": 6, "unit": "piece", "barcode": "1003"},
]

SYNC_CALLS = []


@app.route('/')
@app.route('/pos-system.html')
def pos():
    return render_template('pos-system.html')


@app.route('/sw.js')
def sw():
    return send_from_directory('static/js', 'sw.js', mimetype='application/javascript')


@app.route('/pos-manifest.json')
def pos_manifest():
    return jsonify({"name": "ConnectLink POS", "short_name": "CL POS",
                    "start_url": "/pos-system.html", "display": "standalone"})


@app.route('/api/check-auth')
def check_auth():
    return jsonify({
        "authenticated": True,
        "user": {"name": "Test Admin", "full_name": "Tendai Makoni", "username": "testadmin", "role": "admin"},
        "branch": {"id": 1, "name": "Shurugwi", "read_only": False},
    })


@app.route('/api/branches')
def branches():
    return jsonify({
        "branches": [{"id": 1, "code": "SHU", "name": "Shurugwi"},
                     {"id": 2, "code": "CHE", "name": "Chegutu"}],
        "all_branches": {"id": 0, "name": "All Branches (Read-only)"},
    })


@app.route('/api/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        return jsonify({"success": True})
    return jsonify({"success": True, "products": PRODUCTS})


@app.route('/api/categories')
def categories():
    return jsonify({"categories": ["DIY", "Electricals", "Plumbing", "Machinery"]})


@app.route('/api/dashboard/stats')
def dashboard_stats():
    return jsonify({"total_products": 3, "low_stock": 1, "out_of_stock": 1,
                    "today_sales": 739.0, "items_sold": 53})


@app.route('/api/dashboard/today-by-cashier')
def today_by_cashier():
    return jsonify({"success": True, "grand_total": 739.0, "transaction_count": 4, "items_sold": 53,
                    "cashiers": [{"cashier": "Tendai Makoni", "total": 739.0,
                                  "transaction_count": 4, "items_sold": 53}]})


@app.route('/api/transactions', methods=['GET', 'POST'])
def transactions():
    if request.method == 'POST':
        return jsonify({"success": True, "transaction_id": 999,
                        "transaction_number": "TXN-LIVE-1"}), 201
    return jsonify({"transactions": [], "total": 0})


@app.route('/api/transactions/sync', methods=['POST'])
def sync():
    body = request.get_json(silent=True) or {}
    sales = body.get('sales') or []
    SYNC_CALLS.append(sales)
    with open('_preview_sync_calls.json', 'w', encoding='utf-8') as fh:
        json.dump(SYNC_CALLS, fh, indent=2)
    results = [{"client_ref": s.get("client_ref"), "status": "synced",
                "transaction_id": 1000 + i, "transaction_number": "TXN-SYNC-%d" % i}
               for i, s in enumerate(sales)]
    return jsonify({"success": True, "results": results, "synced": len(results),
                    "duplicate": 0, "failed": 0})


@app.route('/api/transactions/day-end')
def day_end():
    return jsonify({"success": True, "cashiers": [], "branches": [],
                    "grand_total": 0, "transaction_count": 0,
                    "payment_methods": {"cash": 0, "card": 0, "transfer": 0},
                    "scope": "Shurugwi", "multi_branch": False})


@app.route('/api/stock-movements')
def stock_movements():
    return jsonify({"summary": {}, "products": [], "additions": [], "reductions": [],
                    "removals": [], "voided": []})


@app.route('/api/transactions/voided')
def voided():
    return jsonify({"voided": []})


@app.route('/api/activity-log', methods=['GET', 'POST'])
def activity_log():
    if request.method == 'POST':
        return jsonify({"success": True})
    return jsonify({"activities": [], "total": 0})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5088, debug=False)
