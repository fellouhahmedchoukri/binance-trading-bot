document.addEventListener('DOMContentLoaded', function() {
    // Mettre à jour l'heure actuelle
    function updateCurrentTime() {
        const now = new Date();
        document.getElementById('current-time').textContent = 
            now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    setInterval(updateCurrentTime, 1000);
    updateCurrentTime();

    // Charger les données initiales
    fetchDashboardData();
    
    // Configurer le rafraîchissement automatique
    setInterval(fetchDashboardData, 30000); // Rafraîchir toutes les 30 secondes

    // Initialiser le graphique
    const ctx = document.getElementById('performance-chart').getContext('2d');
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Capital ($)',
                data: [],
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    });

    // Fonction pour récupérer les données du dashboard
    function fetchDashboardData() {
        fetch('/api/dashboard/data')
            .then(response => response.json())
            .then(data => {
                updateDashboard(data);
                updateChart(data.history, chart);
            })
            .catch(error => {
                console.error('Error fetching dashboard data:', error);
                document.getElementById('bot-status').className = 'badge bg-danger';
                document.getElementById('bot-status').textContent = 'Hors ligne';
            });
    }

    // Mettre à jour les éléments du dashboard
    function updateDashboard(data) {
        const snapshot = data.snapshot;
        
        // Mettre à jour les KPI
        document.getElementById('equity-value').textContent = `$${snapshot.equity.toFixed(2)}`;
        document.getElementById('profit-value').textContent = `$${snapshot.net_profit.toFixed(2)}`;
        document.getElementById('positions-count').textContent = snapshot.open_positions;
        document.getElementById('orders-count').textContent = snapshot.pending_orders;
        document.getElementById('btc-price').textContent = `$${snapshot.btc_price.toFixed(2)}`;
        document.getElementById('last-update').textContent = new Date(snapshot.timestamp).toLocaleTimeString('fr-FR');
        
        // Calculer les variations
        const prevEquity = data.history.length > 1 ? data.history[data.history.length - 2].equity : snapshot.equity;
        const prevProfit = data.history.length > 1 ? data.history[data.history.length - 2].net_profit : snapshot.net_profit;
        
        const equityChange = ((snapshot.equity - prevEquity) / prevEquity * 100).toFixed(2);
        const profitChange = ((snapshot.net_profit - prevProfit) / Math.abs(prevProfit) * 100).toFixed(2);
        
        document.getElementById('equity-change').textContent = `${equityChange >= 0 ? '+' : ''}${equityChange}%`;
        document.getElementById('equity-change').className = equityChange >= 0 ? 'profit-positive' : 'profit-negative';
        
        document.getElementById('profit-change').textContent = `${profitChange >= 0 ? '+' : ''}${profitChange}%`;
        document.getElementById('profit-change').className = profitChange >= 0 ? 'profit-positive' : 'profit-negative';
        
        // Mettre à jour les positions
        const positionsTable = document.getElementById('positions-table');
        positionsTable.innerHTML = '';
        
        data.positions.forEach(position => {
            const profit = (position.current_price - position.entry_price) * position.quantity;
            const profitPercent = ((position.current_price - position.entry_price) / position.entry_price * 100).toFixed(2);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${position.symbol}</td>
                <td>${position.quantity.toFixed(6)}</td>
                <td>$${position.entry_price.toFixed(2)}</td>
                <td>$${position.current_price.toFixed(2)}</td>
                <td class="${profit >= 0 ? 'profit-positive' : 'profit-negative'}">
                    ${profit >= 0 ? '+' : ''}${profit.toFixed(2)} (${profitPercent}%)
                </td>
            `;
            positionsTable.appendChild(row);
        });
        
        // Mettre à jour les ordres en attente
        const ordersTable = document.getElementById('orders-table');
        ordersTable.innerHTML = '';
        
        data.orders.forEach(order => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${order.symbol}</td>
                <td><span class="badge ${order.side === 'BUY' ? 'bg-success' : 'bg-danger'}">${order.side}</span></td>
                <td>${order.quantity.toFixed(6)}</td>
                <td>$${order.price.toFixed(2)}</td>
                <td><span class="badge bg-warning text-dark">En attente</span></td>
            `;
            ordersTable.appendChild(row);
        });
        
        // Mettre à jour les transactions récentes
        const recentTrades = document.getElementById('recent-trades');
        recentTrades.innerHTML = '';
        
        data.trades.slice(0, 5).forEach(trade => {
            const date = new Date(trade.timestamp);
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</td>
                <td>${trade.symbol}</td>
                <td><span class="badge ${trade.side === 'BUY' ? 'bg-success' : 'bg-danger'}">${trade.side}</span></td>
                <td>$${(trade.quantity * trade.price).toFixed(2)}</td>
            `;
            recentTrades.appendChild(row);
        });
    }

    // Mettre à jour le graphique de performance
    function updateChart(history, chart) {
        chart.data.labels = history.map(item => 
            new Date(item.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }));
        
        chart.data.datasets[0].data = history.map(item => item.equity);
        chart.update();
    }
});
