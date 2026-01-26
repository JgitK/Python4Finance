// ============================================================================
// Ichimoku Chart Module
// ============================================================================

(function() {
    'use strict';

    var currentChartData = null;

    // Get DOM elements
    var chartModal = document.getElementById('chart-modal');
    var chartTitle = document.getElementById('chart-title');
    var chartContainer = document.getElementById('ichimoku-chart');
    var closeModalBtn = document.getElementById('close-modal');
    var dateRangeSlider = document.getElementById('date-range');
    var dateRangeLabel = document.getElementById('date-range-label');

    // Debug: log if elements are found
    console.log('Chart modal found:', !!chartModal);
    console.log('Close button found:', !!closeModalBtn);

    // Close modal function
    function closeChart() {
        console.log('Closing chart');
        if (chartModal) {
            chartModal.classList.add('hidden');
        }
        currentChartData = null;
    }

    // Set up close button
    if (closeModalBtn) {
        closeModalBtn.onclick = function(e) {
            console.log('Close button clicked');
            e.preventDefault();
            closeChart();
            return false;
        };
    }

    // Close on background click
    if (chartModal) {
        chartModal.onclick = function(e) {
            if (e.target === chartModal) {
                closeChart();
            }
        };
    }

    // Close on Escape
    document.onkeydown = function(e) {
        if (e.key === 'Escape' && chartModal && !chartModal.classList.contains('hidden')) {
            closeChart();
        }
    };

    // Slider change
    if (dateRangeSlider) {
        dateRangeSlider.oninput = function() {
            var days = parseInt(this.value);
            if (dateRangeLabel) {
                dateRangeLabel.textContent = days + ' days';
            }
            if (currentChartData) {
                renderChart(currentChartData, days);
            }
        };
    }

    // Render chart with Plotly
    function renderChart(chartData, daysToShow) {
        console.log('Rendering chart for', chartData.ticker, 'with', daysToShow, 'days');

        var data = chartData.data.slice(-daysToShow);

        var dates = [], opens = [], highs = [], lows = [], closes = [];
        var tenkan = [], kijun = [], spanA = [], spanB = [];

        for (var i = 0; i < data.length; i++) {
            var d = data[i];
            dates.push(d.date);
            opens.push(d.open);
            highs.push(d.high);
            lows.push(d.low);
            closes.push(d.close);
            tenkan.push(d.tenkan_sen);
            kijun.push(d.kijun_sen);
            spanA.push(d.senkou_span_a);
            spanB.push(d.senkou_span_b);
        }

        var traces = [
            // Cloud - Span A
            {
                type: 'scatter',
                mode: 'lines',
                x: dates,
                y: spanA,
                name: 'Span A',
                line: { color: 'rgba(76,175,80,0.6)', width: 1 }
            },
            // Cloud - Span B with fill
            {
                type: 'scatter',
                mode: 'lines',
                x: dates,
                y: spanB,
                name: 'Span B',
                line: { color: 'rgba(244,67,54,0.6)', width: 1 },
                fill: 'tonexty',
                fillcolor: 'rgba(180,180,180,0.2)'
            },
            // Tenkan (blue)
            {
                type: 'scatter',
                mode: 'lines',
                x: dates,
                y: tenkan,
                name: 'Tenkan (9)',
                line: { color: '#2196F3', width: 2 }
            },
            // Kijun (red)
            {
                type: 'scatter',
                mode: 'lines',
                x: dates,
                y: kijun,
                name: 'Kijun (26)',
                line: { color: '#f44336', width: 2 }
            },
            // Candlestick
            {
                type: 'candlestick',
                x: dates,
                open: opens,
                high: highs,
                low: lows,
                close: closes,
                name: 'Price',
                increasing: { line: { color: '#26a69a' } },
                decreasing: { line: { color: '#ef5350' } }
            }
        ];

        var layout = {
            title: chartData.ticker + ' - Ichimoku Cloud',
            xaxis: { rangeslider: { visible: false } },
            yaxis: { title: 'Price ($)' },
            legend: { orientation: 'h', y: -0.15 },
            hovermode: 'x unified',
            margin: { t: 40, b: 60, l: 50, r: 30 }
        };

        Plotly.newPlot(chartContainer, traces, layout, { responsive: true });
    }

    // Open chart for a ticker
    function openChart(ticker) {
        console.log('Opening chart for', ticker);

        if (!chartModal) {
            console.error('Chart modal not found!');
            return;
        }

        // Show modal
        chartModal.classList.remove('hidden');
        chartTitle.textContent = 'Loading ' + ticker + '...';

        // Fetch data
        fetch('/api/stock/' + ticker + '/ichimoku')
            .then(function(response) {
                if (!response.ok) throw new Error('HTTP ' + response.status);
                return response.json();
            })
            .then(function(data) {
                console.log('Got data:', data.ticker, data.data.length, 'points');
                currentChartData = data;
                chartTitle.textContent = ticker + ' - Ichimoku Cloud';
                var days = dateRangeSlider ? parseInt(dateRangeSlider.value) : 120;
                renderChart(data, days);
            })
            .catch(function(error) {
                console.error('Fetch error:', error);
                chartTitle.textContent = 'Error loading ' + ticker;
                chartContainer.innerHTML = '<p style="padding:40px;text-align:center;color:red;">Failed to load chart</p>';
            });
    }

    // Make openChart available globally
    window.openChart = openChart;

    console.log('Chart.js loaded, openChart is ready');
})();
