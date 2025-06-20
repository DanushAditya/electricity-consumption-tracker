// Global variables
let realTimeChart;
let chartData = {
    labels: [],  // Shared labels for time
    datasets: [
        {
            label: 'Air Conditioner Consumption (kWh)',
            data: [],
            backgroundColor: 'rgba(0, 123, 255, 0.5)',
            borderColor: 'rgba(0, 123, 255, 1)',
            borderWidth: 1,
            fill: false
        },
        {
            label: 'Washing Machine Consumption (kWh)',
            data: [],
            backgroundColor: 'rgba(0, 255, 123, 0.5)',
            borderColor: 'rgba(0, 255, 123, 1)',
            borderWidth: 1,
            fill: false
        },
        {
            label: 'Refrigerator Consumption (kWh)',
            data: [],
            backgroundColor: 'rgba(255, 123, 0, 0.5)',
            borderColor: 'rgba(255, 123, 0, 1)',
            borderWidth: 1,
            fill: false
        }
    ]
};

function initializeChart() {
    const ctx = document.getElementById('realTimeChart').getContext('2d');
    realTimeChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        tooltipFormat: 'll HH:mm',
                        displayFormats: {
                            minute: 'HH:mm'
                        }
                    }
                },
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function fetchRealTimeData(appliance, datasetIndex) {
    $.get(`/get_real_time_data/${appliance}`, function(data) {
        const timestamp = new Date(data.timestamp * 1000);
        const consumption = data.consumption;

        // Update the chart labels and data
        if (!chartData.labels.includes(timestamp)) {
            chartData.labels.push(timestamp);
        }
        
        chartData.datasets[datasetIndex].data.push(consumption);

        // Update the chart
        realTimeChart.update();
    });
}

function startMonitoring(appliance, datasetIndex) {
    $.post('/start_monitoring', { appliance: appliance }, function(data) {
        console.log(data.status);

        // Start fetching data every second for this appliance
        let intervalId = setInterval(function() {
            fetchRealTimeData(appliance, datasetIndex);
        }, 1000);

        // Save the interval ID so that it can be cleared when monitoring stops
        $(`#stop-${appliance}`).data('intervalId', intervalId);
    });
}

function stopMonitoring(appliance) {
    $.post('/stop_monitoring', { appliance: appliance }, function(data) {
        console.log(data.status);

        // Stop fetching data
        const intervalId = $(`#stop-${appliance}`).data('intervalId');
        clearInterval(intervalId);
    });
}

function stopAllMonitoring() {
    const appliances = ['AirConditioner', 'WashingMachine', 'Refrigerator'];
    appliances.forEach(appliance => {
        stopMonitoring(appliance);
    });
}

function getDatasetIndexForAppliance(appliance) {
    switch (appliance) {
        case 'AirConditioner':
            return 0;
        case 'WashingMachine':
            return 1;
        case 'Refrigerator':
            return 2;
        default:
            return -1;  // Handle any unknown appliances
    }
}

// Fetch and display consumption details
function fetchConsumptionDetails() {
    $.get('/display_consumption_details', function(data) {
        $('#results').html(data);
    });
}


// Fetch and display monthly bill
function fetchMonthlyBill() {
    $.get('/display_monthly_bill', function(data) {
        $('#results').html(data);
    });
}

// Fetch and display archived data
function fetchArchivedData() {
    $.get('/display_archived_data', function(data) {
        $('#results').html(data);
    });
}

// Predict next day consumption
function fetchPrediction() {
    $.get('/predict_next_day_consumption_es', function(data) {
        $('#results').html(
            `Forecast Consumption: ${data.forecast_consumption} kWh<br>` +
            `Forecast Cost: ${data.forecast_cost} INR`
        );
    });
}

// Predict next month consumption
function fetchMonthlyPrediction() {
    $.get('/predict_next_month_consumption_es', function(data) {
        $('#results').html(
            `Forecast Monthly Consumption: ${data.forecast_consumption} kWh<br>` +
            `Forecast Monthly Cost: ${data.forecast_cost} INR`
        );
    });
}

// Reset data function
function resetData() {
    $.post('/reset_data', function(data) {
        $('#results').html(data.result);

    // Reset chart data for each appliance
    const appliances = ['AirConditioner', 'WashingMachine', 'Refrigerator'];
    appliances.forEach(appliance => {
        const datasetIndex = getDatasetIndexForAppliance(appliance);
        if (datasetIndex !== -1) {
            chartData.datasets[datasetIndex].data = [];
        }
    });
    // Clear the chart labels
    chartData.labels = [];

    // Update the chart to reflect the reset
    realTimeChart.update();
    });
}

// Initialize the chart when the page loads
window.onload = initializeChart;
