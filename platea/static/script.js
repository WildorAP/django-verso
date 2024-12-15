// Objeto inicial para precios (valores predeterminados)
const precios = {
    producto1: 1.05, // BUY USDT - USD
    producto2: 3.82, // BUY USDT - PEN
    producto3: 0.991, // SELL USDT - USD
    producto4: 3.78 // SELL USDT - PEN
};

// Función para obtener las tasas de cambio desde la API
async function fetchExchangeRates() {
    try {
        const response = await fetch('/api/rates/'); // URL de la API
        const data = await response.json();

        const rates = data.rates; // Tasas de cambio obtenidas de la API
        console.log('Tasas de cambio recibidas:', rates);

        // Asignar valores de la API al objeto precios
        precios.producto1 = rates.find(rate => rate.currency_from === 'USD' && rate.currency_to === 'USDT')?.rate || precios.producto1;
        precios.producto2 = rates.find(rate => rate.currency_from === 'PEN' && rate.currency_to === 'USDT')?.rate || precios.producto2;
        precios.producto3 = rates.find(rate => rate.currency_from === 'USDT' && rate.currency_to === 'USD')?.rate || precios.producto3;
        precios.producto4 = rates.find(rate => rate.currency_from === 'USDT' && rate.currency_to === 'PEN')?.rate || precios.producto4;

        console.log('Precios actualizados con las tasas de la API:', precios);

        // Actualizar las tasas de cambio en el DOM
        actualizarInformacion();

        // Actualizar los valores dinámicamente para las conversiones
        actualizarExchangeRates();
    } catch (error) {
        console.error('Error al obtener las tasas de cambio:', error);
    }
}

// Función para actualizar el DOM con los valores del objeto precios
function actualizarInformacion() {
    const precioPen = `PEN Compra: <strong>${precios.producto4.toFixed(3)}</strong> Venta: <strong>${precios.producto2.toFixed(3)}</strong>`;
    const precioUsd = `USD Compra: <strong>${precios.producto3.toFixed(3)}</strong> Venta: <strong>${precios.producto1.toFixed(3)}</strong>`;

    // Actualizar los elementos del DOM
    document.getElementById('TC-PEN').innerHTML = precioPen;
    document.getElementById('TC-USD').innerHTML = precioUsd;
}

// Actualiza las tasas de cambio para la lógica de conversión
function actualizarExchangeRates() {
    window.exchangeRates = {
        buy: {  // Comprar Stablecoin con USD o PEN
            USD: precios.producto1,
            PEN: precios.producto2
        },
        sell: { // Vender Stablecoin por USD o PEN
            USD: precios.producto3,
            PEN: precios.producto4
        }
    };
    console.log('Exchange rates actualizados:', window.exchangeRates);
}

// Función para convertir monedas
function convertCurrency() {
    // Obtener los valores ingresados por el usuario
    const amount = parseFloat(document.getElementById("amount").value);
    const toCurrency = document.getElementById("toCurrency").value;
    const transactionType = document.querySelector('input[name="transactionType"]:checked').value;

    // Validar que la cantidad sea válida
    if (isNaN(amount) || amount <= 0) {
        alert("Por favor, ingrese una cantidad válida.");
        return;
    }

    // Obtener la tasa de cambio para el tipo de transacción seleccionado (compra o venta)
    const exchangeRate = window.exchangeRates[transactionType][toCurrency];

    if (!exchangeRate) {
        alert("No se encontró una tasa de cambio para esta conversión.");
        return;
    }

    // Calcular el monto convertido
    const convertedAmount = amount * exchangeRate;

    // Mostrar el resultado en el campo de Total
    document.getElementById("convertedAmount").textContent = convertedAmount.toFixed(2);

    // Actualizar la etiqueta de la moneda en el resultado
    document.getElementById("currencyLabel").textContent = toCurrency;
}

// Llama a la función para obtener las tasas de cambio al cargar la página
window.onload = fetchExchangeRates;
