// ============================================================================
// Portfolio Optimizer - Frontend Logic
// ============================================================================
// This script calls our API and displays the results.

// API base URL (same server serving this page)
const API_BASE = '';

// DOM elements
const amountInput = document.getElementById('amount');
const calculateBtn = document.getElementById('calculate-btn');
const resultsSection = document.getElementById('results');
const benchSection = document.getElementById('bench-section');
const portfolioTypeSelect = document.getElementById('portfolio-type');
const riskToleranceGroup = document.getElementById('risk-tolerance-group');
const riskToleranceSlider = document.getElementById('risk-tolerance');
const riskToleranceValue = document.getElementById('risk-tolerance-value');

// Show/hide risk tolerance slider based on portfolio type
portfolioTypeSelect.addEventListener('change', () => {
    if (portfolioTypeSelect.value === 'custom') {
        riskToleranceGroup.classList.remove('hidden');
    } else {
        riskToleranceGroup.classList.add('hidden');
    }
});

// Update risk tolerance display
riskToleranceSlider.addEventListener('input', () => {
    riskToleranceValue.textContent = riskToleranceSlider.value + '%';
});

// Format currency
function formatCurrency(amount) {
    return '$' + amount.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Format percentage
function formatPercent(decimal) {
    return (decimal * 100).toFixed(1) + '%';
}

// Calculate and display portfolio allocation
async function calculateAllocation() {
    const amount = parseFloat(amountInput.value);
    const portfolioType = portfolioTypeSelect.value;

    // Validate input
    if (!amount || amount <= 0) {
        alert('Please enter a valid investment amount');
        return;
    }

    // Disable button while loading
    calculateBtn.disabled = true;
    calculateBtn.textContent = 'Calculating...';

    try {
        // Build API URL with parameters
        let url = `${API_BASE}/api/portfolio?amount=${amount}`;

        if (portfolioType === 'custom') {
            // Use risk tolerance for custom blend
            const riskTolerance = parseFloat(riskToleranceSlider.value) / 100;
            url += `&risk_tolerance=${riskTolerance}`;
        } else {
            url += `&portfolio_type=${portfolioType}`;
        }

        // Call our API
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error('Failed to calculate allocation');
        }

        const data = await response.json();

        // Update summary stats
        document.getElementById('total-invested').textContent = formatCurrency(data.total_invested);
        document.getElementById('cash-remaining').textContent = formatCurrency(data.cash_remaining);
        document.getElementById('efficiency').textContent = formatPercent(data.efficiency);

        // Build portfolio table
        const tbody = document.querySelector('#portfolio-table tbody');
        tbody.innerHTML = '';

        for (const stock of data.stocks) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="ticker-cell" onclick="openChart('${stock.ticker}')">${stock.ticker}</td>
                <td>${stock.sector}</td>
                <td>${stock.shares}</td>
                <td>${formatCurrency(stock.price)}</td>
                <td>${formatCurrency(stock.amount)}</td>
            `;
            tbody.appendChild(row);
        }

        // Show results
        resultsSection.classList.remove('hidden');

        // Also load bench stocks
        await loadBench();

    } catch (error) {
        console.error('Error:', error);
        alert('Error calculating allocation. Please try again.');
    } finally {
        calculateBtn.disabled = false;
        calculateBtn.textContent = 'Calculate Allocation';
    }
}

// Load and display bench stocks for current strategy
async function loadBench() {
    try {
        // Get current portfolio type for strategy-specific bench
        const portfolioType = portfolioTypeSelect.value === 'custom' ? 'max_sharpe' : portfolioTypeSelect.value;
        const response = await fetch(`${API_BASE}/api/bench?portfolio_type=${portfolioType}`);

        if (!response.ok) {
            throw new Error('Failed to load bench stocks');
        }

        const data = await response.json();

        // Build bench table
        const tbody = document.querySelector('#bench-table tbody');
        tbody.innerHTML = '';

        for (const stock of data.stocks) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="ticker-cell" onclick="openChart('${stock.ticker}')">${stock.ticker}</td>
                <td>${stock.sector}</td>
                <td>${stock.sharpe_ratio.toFixed(2)}</td>
                <td>${formatCurrency(stock.current_price)}</td>
            `;
            tbody.appendChild(row);
        }

        // Show bench section
        benchSection.classList.remove('hidden');

    } catch (error) {
        console.error('Error loading bench:', error);
    }
}

// Event listeners
calculateBtn.addEventListener('click', calculateAllocation);

// Also trigger on Enter key
amountInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        calculateAllocation();
    }
});

// Set default value
amountInput.value = '3500';
