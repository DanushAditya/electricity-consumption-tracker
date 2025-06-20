from flask import Flask, render_template, request, jsonify
import pandas as pd
import random
import time
from datetime import datetime
import os
import threading
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from cryptography.fernet import Fernet

app = Flask(__name__)

# Generate a key for encryption
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Initialize global variables
appliance_status = {
    'AirConditioner': False,
    'WashingMachine': False,
    'Refrigerator': False
}
consumption_data = {
    'AirConditioner': [],
    'WashingMachine': [],
    'Refrigerator': []
}
total_consumption = {
    'AirConditioner': 0,
    'WashingMachine': 0,
    'Refrigerator': 0
}
start_times = {}
end_times = {}
alerts_threshold = 15.1  # Alert when total consumption reaches 15.1 kW

# Load existing data from CSV
csv_file = 'daily_consumption.csv'
if os.path.exists(csv_file):
    daily_data = pd.read_csv(csv_file)
else:
    daily_data = pd.DataFrame(columns=['Date', 'Time', 'Appliance', 'Total Consumption (kW)', 'Cost (INR)', 'Total Time (s)'])

archived_csv_file = 'archived_daily_consumption.csv'
rate_per_kwh_inr = 10.0
data_lock = threading.Lock()

# Function to simulate real-time data
def generate_real_time_data(appliance):
    while appliance_status[appliance]:
        with data_lock:
            consumption = random.uniform(0.5, 2.0)
            consumption_data[appliance].append((time.time(), consumption))
            total_consumption[appliance] += consumption
            if total_consumption[appliance] >= alerts_threshold:
                # Trigger alert - Implementation needed here
                pass
        time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    appliance = request.form['appliance']
    if not appliance_status[appliance]:
        appliance_status[appliance] = True
        start_times[appliance] = time.time()
        threading.Thread(target=generate_real_time_data, args=(appliance,), daemon=True).start()
    return jsonify({'status': 'Monitoring started'})

@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    appliance = request.form['appliance']
    if appliance_status[appliance]:
        appliance_status[appliance] = False
        end_times[appliance] = time.time()
        store_daily_data(appliance)
    return jsonify({'status': 'Monitoring stopped'})

@app.route('/stop_all_appliances', methods=['POST'])
def stop_all_appliances():
    for appliance in appliance_status.keys():
        if appliance_status[appliance]:
            appliance_status[appliance] = False
            end_times[appliance] = time.time()
            store_daily_data(appliance)
    return jsonify({'status': 'All appliances stopped'})

@app.route('/display_consumption_details', methods=['GET'])
def display_consumption_details():
    if daily_data.empty:
        return jsonify({'result': "No data available."})

    current_date = datetime.now().strftime('%Y-%m-%d')
    current_date_row = daily_data[daily_data['Date'] == current_date]
    
    daily_summary = daily_data.groupby(['Date', 'Time', 'Appliance']).sum().reset_index()
    table_str = daily_summary.to_html()

    return table_str

@app.route('/predict_next_day_consumption_es', methods=['GET'])
def predict_next_day_consumption_es():
    if len(daily_data) < 2:
        return jsonify({'result': "Not enough data for prediction."})
    
    daily_summary = daily_data.groupby('Date').sum().reset_index()
    daily_summary['Date'] = pd.to_datetime(daily_summary['Date'])
    daily_summary.set_index('Date', inplace=True)
    daily_summary = daily_summary.asfreq('D', fill_value=0)
    
    if len(daily_summary) < 2:
        return jsonify({'result': "Not enough data for prediction."})
    
    try:
        model = ExponentialSmoothing(daily_summary['Total Consumption (kW)'], trend=None, seasonal=None)
        model_fit = model.fit()
        forecast_consumption = model_fit.forecast(steps=1).iloc[0]
        forecast_cost = forecast_consumption * rate_per_kwh_inr
    except Exception as e:
        return jsonify({'result': f"Prediction error: {str(e)}"})
    
    return jsonify({
        'forecast_consumption': forecast_consumption,
        'forecast_cost': forecast_cost
    })

@app.route('/predict_next_month_consumption_es', methods=['GET'])
def predict_next_month_consumption_es():
    if len(daily_data) < 30:
        return jsonify({'result': "Not enough data for prediction."})
    
    daily_summary = daily_data.groupby('Date').sum().reset_index()
    daily_summary['Date'] = pd.to_datetime(daily_summary['Date'])
    daily_summary.set_index('Date', inplace=True)
    daily_summary = daily_summary.asfreq('D', fill_value=0)
    
    if len(daily_summary) < 30:
        return jsonify({'result': "Not enough data for prediction."})
    
    try:
        model = ExponentialSmoothing(daily_summary['Total Consumption (kW)'], trend='add', seasonal=None)
        model_fit = model.fit()
        forecast_consumption = model_fit.forecast(steps=30).sum()
        forecast_cost = forecast_consumption * rate_per_kwh_inr
    except Exception as e:
        return jsonify({'result': f"Prediction error: {str(e)}"})
    
    return jsonify({
        'forecast_consumption': forecast_consumption,
        'forecast_cost': forecast_cost
    })

@app.route('/display_monthly_bill', methods=['GET'])
def display_monthly_bill():
    if daily_data.empty:
        return jsonify({'result': "No data available."})

    monthly_summary = daily_data.groupby('Appliance').sum().reset_index()
    total_cost = monthly_summary['Cost (INR)'].sum()
    current_date = datetime.now().strftime('%Y-%m-%d')
    monthly_summary['Current Date'] = current_date
    average_consumption = daily_data.groupby('Appliance')['Total Consumption (kW)'].mean().reset_index()
    average_consumption.columns = ['Appliance', 'Average Consumption (kW)']
    monthly_summary = monthly_summary.merge(average_consumption, on='Appliance', how='left')
    total_row = pd.DataFrame({
        'Appliance': ['Total'],
        'Total Consumption (kW)': [monthly_summary['Total Consumption (kW)'].sum()],
        'Cost (INR)': [monthly_summary['Cost (INR)'].sum()],
        'Total Time (s)': [monthly_summary['Total Time (s)'].sum()],
        'Average Consumption (kW)': [monthly_summary['Average Consumption (kW)'].mean()],
        'Current Date': [current_date]
    })
    monthly_summary_table = pd.concat([monthly_summary[['Appliance', 'Total Consumption (kW)', 'Cost (INR)', 'Total Time (s)', 'Average Consumption (kW)', 'Current Date']], total_row], ignore_index=True)
    table_str = monthly_summary_table.to_html()
    return table_str

@app.route('/reset_data', methods=['POST'])
def reset_data():
    archive_data()
    global daily_data
    daily_data = pd.DataFrame(columns=['Date', 'Time', 'Appliance', 'Total Consumption (kW)', 'Cost (INR)', 'Total Time (s)'])
    if os.path.exists(csv_file):
        os.remove(csv_file)
    return jsonify({'result': "Data has been reset."})

@app.route('/display_archived_data', methods=['GET'])
def display_archived_data():
    if not os.path.exists(archived_csv_file):
        return jsonify({'result': "No archived data available."})
    
    archived_data = pd.read_csv(archived_csv_file)
    table_str = archived_data.to_html()
    return table_str

@app.route('/get_real_time_data/<appliance>', methods=['GET'])
def get_real_time_data(appliance):
    if appliance in consumption_data and consumption_data[appliance]:
        latest_data = consumption_data[appliance][-1]  # Get the latest data point
        timestamp, consumption = latest_data
        return jsonify({'timestamp': timestamp, 'consumption': consumption})
    return jsonify({'timestamp': time.time(), 'consumption': 0.0})  # Default data if empty

def store_daily_data(appliance):
    with data_lock:
        total_consumption_value = sum(consumption for _, consumption in consumption_data[appliance])
        duration = end_times.get(appliance, 0) - start_times.get(appliance, 0)
        cost = total_consumption_value * rate_per_kwh_inr
        date = datetime.now().strftime('%Y-%m-%d')
        time_now = datetime.now().strftime('%H:%M:%S')
        new_entry = pd.DataFrame([{
            'Date': date,
            'Time': time_now,
            'Appliance': appliance,
            'Total Consumption (kW)': total_consumption_value,
            'Cost (INR)': cost,
            'Total Time (s)': duration
        }])
        global daily_data
        daily_data = pd.concat([daily_data, new_entry], ignore_index=True)
        daily_data.to_csv(csv_file, index=False)
        consumption_data[appliance] = []

def archive_data():
    if not daily_data.empty:
        if os.path.exists(archived_csv_file):
            daily_data.to_csv(archived_csv_file, mode='a', header=False, index=False)
        else:
            daily_data.to_csv(archived_csv_file, index=False)

if __name__ == '__main__':
    app.run(debug=True)