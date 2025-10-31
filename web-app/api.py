from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import hashlib
import hmac
import json
from datetime import datetime
import sys
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ==================== FRONTEND ROUTES ====================

@app.route('/')
def serve_index():
    try:
        print("📄 Serving index.html")
        return send_from_directory('.', 'index.html')
    except Exception as e:
        print(f"❌ Error serving index.html: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/<path:path>')
def serve_static(path):
    try:
        print(f"📁 Serving static file: {path}")
        return send_from_directory('.', path)
    except Exception as e:
        print(f"❌ Error serving {path}: {e}")
        return jsonify({'error': f'File not found: {path}'}), 404

@app.route('/favicon.ico')
def favicon():
    return '', 404

# ==================== API ROUTES ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Finance Bot API'
    })

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    return jsonify({
        'message': 'API работает!',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/user-data', methods=['POST'])
def get_user_data():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Для тестирования возвращаем фиктивные данные
        return jsonify({
            'success': True,
            'user_id': 123456789,
            'credits': [
                {
                    'id': 1,
                    'debt_amount': 50000,
                    'current_debt': 45000,
                    'annual_rate': 15,
                    'months': 12,
                    'months_paid': 1,
                    'monthly_payment': 4512,
                    'total_payment': 54144,
                    'overpayment': 4144
                }
            ],
            'total_debt': 45000,
            'monthly_payments': 4512,
            'total_overpayment': 4144
        })
        
    except Exception as e:
        print(f"Error in /api/user-data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/add-credit', methods=['POST'])
def add_credit():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Фиктивный расчет для тестирования
        debt_amount = float(data.get('debt_amount', 0))
        annual_rate = float(data.get('annual_rate', 0))
        months = int(data.get('months', 0))
        
        # Простой расчет (упрощенный)
        monthly_rate = annual_rate / 100 / 12
        monthly_payment = debt_amount * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
        total_payment = monthly_payment * months
        overpayment = total_payment - debt_amount
        
        return jsonify({
            'success': True,
            'credit_id': 999,
            'monthly_payment': round(monthly_payment, 2),
            'total_payment': round(total_payment, 2),
            'overpayment': round(overpayment, 2)
        })
        
    except Exception as e:
        print(f"Error in /api/add-credit: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/make-payment', methods=['POST'])
def make_payment():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        return jsonify({
            'success': True,
            'payment_amount': data.get('amount', 0),
            'interest_amount': 500,
            'principal_amount': 1000,
            'remaining_debt': 44000
        })
        
    except Exception as e:
        print(f"Error in /api/make-payment: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"🔥 Internal Server Error: {error}")
    print(traceback.format_exc())
    return jsonify({'error': 'Internal server error'}), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    print(f"🚀 Starting Finance Bot API on {host}:{port}")
    print(f"📁 Serving from: {os.path.abspath('.')}")
    print(f"🔧 Debug mode: {debug}")
    
    # Выведем список файлов для отладки
    print("📋 Files in current directory:")
    for file in os.listdir('.'):
        print(f"   - {file}")
    
    app.run(host=host, port=port, debug=debug)
