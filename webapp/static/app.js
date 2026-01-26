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

    // Validate input
    if (!amount || amount <= 0) {
        alert('Please enter a valid investment amount');
        return;
    }

    // Disable button while loading
    calculateBtn.disabled = true;
    calculateBtn.textContent = 'Calculating...';

    try {
        // Call our API
        const response = await fetch(`${API_BASE}/api/portfolio?amount=${amount}`);

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

// Load and display bench stocks
async function loadBench() {
    try {
        const response = await fetch(`${API_BASE}/api/bench`);

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
