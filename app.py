from flask import Flask, render_template, request, jsonify
from calculator import UVDoseCalculator

app = Flask(__name__)

# Put your actual NREL API key and email right here:
API_KEY = "uS4E951mkHQkRfCUkv8QzQTzld5MA4dFOhySd7d9"
EMAIL = "micahchatterjee@gmail.com"

CALCULATOR = UVDoseCalculator(api_key=API_KEY, email=EMAIL)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/calculate', methods=['POST'])
def calculate_dose():
    try:
        data = request.get_json()
        lat = float(data['latitude'])
        lon = float(data['longitude'])
        date_str = data['date']
        start_time = data['start_time']
        end_time = data['end_time']
        
        year = int(date_str.split('-')[0])
        
        df = CALCULATOR.fetch_nsrdb_data(lat, lon, year)
        results = CALCULATOR.calculate_dose(df, date_str, start_time, end_time)
        
        return jsonify({"success": True, "results": results}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)