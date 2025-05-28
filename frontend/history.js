// Constants
const API_BASE_URL = 'http://localhost:8000';
const USER_ID = 1; // Default user ID for demo

// Initialize page when loaded
document.addEventListener('DOMContentLoaded', function() {
    loadData();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Time range change handler
    document.getElementById('timeRange').addEventListener('change', function() {
        updateGraph();
    });

    // Search input handler
    document.getElementById('searchInput').addEventListener('input', function() {
        filterTable(this.value.toLowerCase());
    });

    // Table sorting
    document.querySelectorAll('.readings-table th[data-sort]').forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            sortTable(column);
        });
    });
}

// Load all data
async function loadData() {
    try {
        // Fetch readings and stats in parallel
        const [readings, stats] = await Promise.all([
            fetch(`${API_BASE_URL}/bp/readings/${USER_ID}`).then(res => res.json()),
            fetch(`${API_BASE_URL}/bp/readings/stats/${USER_ID}`).then(res => res.json())
        ]);

        // Store readings globally for filtering/sorting
        window.allReadings = readings;

        // Update UI
        updateTable(readings);
        updateStats(stats);
        initializeGraph(readings);

    } catch (error) {
        console.error('Error loading data:', error);
        alert('Error loading blood pressure data. Please try again later.');
    }
}

// Update table with readings
function updateTable(readings) {
    const tbody = document.getElementById('readingsTableBody');
    tbody.innerHTML = '';

    readings.forEach(reading => {
        const row = document.createElement('tr');
        const timestamp = new Date(reading.reading_time).toLocaleString();
        const statusClass = getStatusClass(reading.interpretation);

        row.innerHTML = `
            <td>${timestamp}</td>
            <td>${reading.systolic}</td>
            <td>${reading.diastolic}</td>
            <td>${reading.pulse || '-'}</td>
            <td class="${statusClass}">${reading.interpretation}</td>
            <td class="device-cell">${reading.device_id || 'Manual Entry'}</td>
            <td class="notes-cell">${reading.notes || '-'}</td>
        `;
        tbody.appendChild(row);
    });
}

// Update statistics display
function updateStats(stats) {
    document.getElementById('totalReadings').textContent = stats.total_readings;
    document.getElementById('avgSystolic').textContent = `${Math.round(stats.averages.systolic)} mmHg`;
    document.getElementById('avgDiastolic').textContent = `${Math.round(stats.averages.diastolic)} mmHg`;
    document.getElementById('avgPulse').textContent = stats.averages.pulse ? `${Math.round(stats.averages.pulse)} BPM` : '-';
}

// Initialize and render the graph
function initializeGraph(readings) {
    const ctx = document.getElementById('bpTrendGraph').getContext('2d');
    
    // Process data for the graph
    const dates = readings.map(r => new Date(r.reading_time));
    const systolicReadings = readings.map(r => r.systolic);
    const diastolicReadings = readings.map(r => r.diastolic);

    // Create the chart
    window.bpChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: dates,
                        datasets: [
                            {
                                label: 'Systolic',
                                data: systolicReadings,
                                borderColor: '#e74c3c',
                                backgroundColor: 'rgba(231, 76, 60, 0.1)',
                                tension: 0.4,
                                pointStyle: 'circle',
                                pointRadius: 4,
                                pointHoverRadius: 6
                            },
                            {
                                label: 'Diastolic',
                                data: diastolicReadings,
                                borderColor: '#3498db',
                                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                                tension: 0.4,
                                pointStyle: 'circle',
                                pointRadius: 4,
                                pointHoverRadius: 6
                            }
                        ]
                    },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Date'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Blood Pressure (mmHg)'
                    },
                    min: 40,
                    max: 200
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return new Date(context[0].label).toLocaleDateString();
                        }
                    }
                }
            }
        }
    });
}

// Update graph based on time range
function updateGraph() {
    const timeRange = document.getElementById('timeRange').value;
    const readings = filterReadingsByTimeRange(window.allReadings, timeRange);
    
    // Update chart data
    window.bpChart.data.labels = readings.map(r => new Date(r.reading_time));
    window.bpChart.data.datasets[0].data = readings.map(r => r.systolic);
    window.bpChart.data.datasets[1].data = readings.map(r => r.diastolic);
    window.bpChart.update();
}

// Filter readings by time range
function filterReadingsByTimeRange(readings, days) {
    if (days === 'all') return readings;
    
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - parseInt(days));
    
    return readings.filter(reading => 
        new Date(reading.reading_time) >= cutoffDate
    );
}

// Filter table based on search input
function filterTable(searchTerm) {
    const filteredReadings = window.allReadings.filter(reading => {
        const searchableText = `
            ${reading.interpretation}
            ${reading.device_id || ''}
            ${reading.notes || ''}
        `.toLowerCase();
        
        return searchableText.includes(searchTerm);
    });
    
    updateTable(filteredReadings);
}

// Sort table by column
function sortTable(column) {
    const readings = [...window.allReadings];
    const header = document.querySelector(`th[data-sort="${column}"]`);
    const isAscending = header.classList.toggle('asc');
    
    readings.sort((a, b) => {
        let valueA, valueB;
        
        switch(column) {
            case 'date':
                valueA = new Date(a.reading_time);
                valueB = new Date(b.reading_time);
                break;
            case 'systolic':
                valueA = a.systolic;
                valueB = b.systolic;
                break;
            case 'diastolic':
                valueA = a.diastolic;
                valueB = b.diastolic;
                break;
            case 'pulse':
                valueA = a.pulse || 0;
                valueB = b.pulse || 0;
                break;
            case 'status':
                valueA = a.interpretation;
                valueB = b.interpretation;
                break;
            case 'device':
                valueA = a.device_id || '';
                valueB = b.device_id || '';
                break;
            default:
                return 0;
        }
        
        if (valueA < valueB) return isAscending ? -1 : 1;
        if (valueA > valueB) return isAscending ? 1 : -1;
        return 0;
    });
    
    updateTable(readings);
}

// Get CSS class for status
function getStatusClass(status) {
    if (!status) return '';
    if (status.includes('Normal')) return 'status-normal';
    if (status.includes('Elevated')) return 'status-elevated';
    if (status.includes('Hypertension') || status.includes('Crisis')) return 'status-high';
    return '';
}
