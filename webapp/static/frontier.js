// ============================================================================
// Efficient Frontier Chart Module
// ============================================================================

(function() {
    'use strict';

    var chartContainer = document.getElementById('frontier-chart');

    // Load and render the efficient frontier on page load
    function loadEfficientFrontier() {
        if (!chartContainer) {
            console.log('Frontier chart container not found');
            return;
        }

        // Show loading state
        chartContainer.innerHTML = '<p style="padding:40px;text-align:center;color:#718096;">Loading efficient frontier...</p>';

        fetch('/api/efficient-frontier')
            .then(function(response) {
                if (!response.ok) throw new Error('HTTP ' + response.status);
                return response.json();
            })
            .then(function(data) {
                console.log('Got frontier data:', data.total_portfolios, 'portfolios');
                console.log('Strategy positions:', data.strategy_positions);
                renderFrontierChart(data);
            })
            .catch(function(error) {
                console.error('Frontier fetch error:', error);
                chartContainer.innerHTML = '<p style="padding:40px;text-align:center;color:#e53e3e;">Failed to load efficient frontier data</p>';
            });
    }

    function renderFrontierChart(data) {
        var portfolios = data.portfolios;
        var riskFreeRate = data.risk_free_rate;
        var strategyPositions = data.strategy_positions || [];

        // Extract data for plotting
        var risks = [];
        var returns = [];
        var sharpes = [];
        var hoverTexts = [];

        for (var i = 0; i < portfolios.length; i++) {
            var p = portfolios[i];
            risks.push(p.risk * 100); // Convert to percentage
            returns.push(p.return * 100);
            sharpes.push(p.sharpe);
            hoverTexts.push(
                'Return: ' + (p.return * 100).toFixed(2) + '%<br>' +
                'Risk: ' + (p.risk * 100).toFixed(2) + '%<br>' +
                'Sharpe: ' + p.sharpe.toFixed(3)
            );
        }

        // Find max Sharpe for CML line
        var optimal = data.optimal;

        // Create traces array
        var traces = [
            // All portfolios scatter plot
            {
                type: 'scatter',
                mode: 'markers',
                x: risks,
                y: returns,
                marker: {
                    color: sharpes,
                    colorscale: [
                        [0, '#ef5350'],      // Low Sharpe - red
                        [0.5, '#ffd54f'],    // Medium - yellow
                        [1, '#26a69a']       // High Sharpe - green
                    ],
                    size: 5,
                    opacity: 0.5,
                    colorbar: {
                        title: 'Sharpe',
                        thickness: 12,
                        len: 0.4,
                        y: 0.8,
                        tickfont: { size: 10 }
                    }
                },
                text: hoverTexts,
                hoverinfo: 'text',
                name: 'Simulated Portfolios'
            },
            // Capital Market Line
            {
                type: 'scatter',
                mode: 'lines',
                x: [0, optimal.risk * 100 * 2],
                y: [riskFreeRate * 100, riskFreeRate * 100 + optimal.sharpe * optimal.risk * 100 * 2],
                line: {
                    color: '#9ca3af',
                    width: 1.5,
                    dash: 'dash'
                },
                name: 'Capital Market Line',
                hoverinfo: 'skip',
                showlegend: false
            }
        ];

        // Add each strategy portfolio as a distinct marker
        for (var j = 0; j < strategyPositions.length; j++) {
            var strat = strategyPositions[j];

            traces.push({
                type: 'scatter',
                mode: 'markers+text',
                x: [strat.risk * 100],
                y: [strat.return * 100],
                marker: {
                    color: strat.color,
                    size: 14,
                    symbol: strat.symbol,
                    line: {
                        color: 'white',
                        width: 2
                    }
                },
                text: [strat.name],
                textposition: getTextPosition(strat.strategy),
                textfont: {
                    size: 10,
                    color: strat.color
                },
                hovertext: '<b>' + strat.name + '</b><br>' +
                    'Return: ' + (strat.return * 100).toFixed(2) + '%<br>' +
                    'Risk: ' + (strat.risk * 100).toFixed(2) + '%<br>' +
                    'Sharpe: ' + strat.sharpe.toFixed(3) +
                    (strat.sortino ? '<br>Sortino: ' + strat.sortino.toFixed(3) : ''),
                hoverinfo: 'text',
                name: strat.name,
                showlegend: true
            });
        }

        var layout = {
            title: '',
            xaxis: {
                title: 'Risk (Standard Deviation %)',
                zeroline: false,
                gridcolor: '#e2e8f0'
            },
            yaxis: {
                title: 'Expected Return (%)',
                zeroline: false,
                gridcolor: '#e2e8f0'
            },
            hovermode: 'closest',
            showlegend: true,
            legend: {
                x: 1.02,
                y: 0.5,
                xanchor: 'left',
                bgcolor: 'rgba(255,255,255,0.9)',
                bordercolor: '#e2e8f0',
                borderwidth: 1,
                font: { size: 11 }
            },
            margin: { t: 20, b: 50, l: 60, r: 120 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)'
        };

        var config = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot(chartContainer, traces, layout, config);
    }

    // Helper to position text labels to avoid overlap
    function getTextPosition(strategy) {
        var positions = {
            'max_sharpe': 'top right',
            'min_variance': 'bottom left',
            'max_sortino': 'top left',
            'min_cvar': 'bottom right',
            'risk_parity': 'top center',
            'equal_weight': 'bottom center'
        };
        return positions[strategy] || 'top right';
    }

    // Load on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadEfficientFrontier);
    } else {
        loadEfficientFrontier();
    }

    console.log('Frontier.js loaded');
})();
