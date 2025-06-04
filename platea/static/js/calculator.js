document.addEventListener('DOMContentLoaded', function () {
    const btnCompra = document.getElementById('btn-compra');
    const btnVenta = document.getElementById('btn-venta');
    const tipoOperacion = document.getElementById('tipo_operacion');
    const inputMonto = document.getElementById('monto');
    const selectOrigen = document.getElementById('moneda_origen');
    const selectDestino = document.getElementById('moneda_destino');
    const resultadoBox = document.getElementById('resultado_box');
    const montoOrigen = document.getElementById('monto_origen');
    const montoConvertido = document.getElementById('monto_convertido');
    const labelOrigen = document.getElementById('label_origen');
    const labelDestino = document.getElementById('label_destino');
    const tasaOrigen = document.getElementById('tasa_origen');
    const tasaValor = document.getElementById('tasa_valor');
    const tasaDestino = document.getElementById('tasa_destino');
    const resumenOperacion = document.getElementById('resumen_operacion');

    // Constantes para las monedas
    const cripto = ['USDT', 'USDC'];
    const fiat = ['USD', 'PEN'];

    // Obtener las tasas del elemento data-tasas
    const tasasElement = document.getElementById('tasas-data');
    let tasasData = {};
    if (tasasElement && tasasElement.dataset.tasas) {
        try {
            tasasData = JSON.parse(tasasElement.dataset.tasas);
        } catch (error) {
            console.error('Error al parsear las tasas:', error);
        }
    }

    // Configuración inicial
    btnCompra.classList.add('active');
    btnVenta.classList.remove('active');
    tipoOperacion.value = 'compra';
    actualizarOpcionesMonedas('compra');
    calcularConversion();
    validarMinimoMonto();

    // Event Listeners
    btnCompra.addEventListener('click', () => {
        tipoOperacion.value = 'compra';
        activarBotonSeleccionado('compra');
        actualizarOpcionesMonedas('compra');
        calcularConversion();
    });

    btnVenta.addEventListener('click', () => {
        tipoOperacion.value = 'venta';
        activarBotonSeleccionado('venta');
        actualizarOpcionesMonedas('venta');
        calcularConversion();
    });

    selectOrigen.addEventListener('change', () => {
        actualizarOpcionesDestino();
        calcularConversion();
    });
    
    selectDestino.addEventListener('change', calcularConversion);
    
    inputMonto.addEventListener('input', () => {
        calcularConversion();
        validarMinimoMonto();
    });

    function activarBotonSeleccionado(tipo) {
        if (tipo === 'compra') {
            btnCompra.classList.add('active');
            btnVenta.classList.remove('active');
        } else {
            btnVenta.classList.add('active');
            btnCompra.classList.remove('active');
        }
    }

    function actualizarOpcionesMonedas(tipo) {
        // Limpiar y actualizar opciones de moneda origen
        selectOrigen.innerHTML = '';
        const monedasOrigen = tipo === 'compra' ? fiat : cripto;
        
        const nombreMonedas = {
            'USDT': 'USDT (Tether)',
            'USDC': 'USDC (USD Coin)',
            'PEN': 'PEN (Soles)',
            'USD': 'USD (Dólares)'
        };

        monedasOrigen.forEach(moneda => {
            const option = document.createElement('option');
            option.value = moneda;
            option.textContent = nombreMonedas[moneda];
            selectOrigen.appendChild(option);
        });

        // Establecer valor por defecto según el tipo
        selectOrigen.value = tipo === 'compra' ? 'USD' : 'USDT';

        // Actualizar opciones de destino
        actualizarOpcionesDestino();
    }

    function actualizarOpcionesDestino() {
        const tipo = tipoOperacion.value;
        selectDestino.innerHTML = '';

        let opcionesDestino;
        if (tipo === 'compra') {
            opcionesDestino = cripto;
        } else {
            opcionesDestino = fiat;
        }

        const nombreMonedas = {
            'USDT': 'USDT (Tether)',
            'USDC': 'USDC (USD Coin)',
            'PEN': 'PEN (Soles)',
            'USD': 'USD (Dólares)'
        };

        opcionesDestino.forEach(moneda => {
            const option = document.createElement('option');
            option.value = moneda;
            option.textContent = nombreMonedas[moneda];
            selectDestino.appendChild(option);
        });

        // Seleccionar la primera opción por defecto
        if (opcionesDestino.length > 0) {
            selectDestino.value = opcionesDestino[0];
        }
    }

    function calcularConversion() {
        const monto = parseFloat(inputMonto.value) || 0;
        const origen = selectOrigen.value;
        const destino = selectDestino.value;
        const tipo = tipoOperacion.value;

        const key = `${origen}_${destino}`;
        const keyInverso = `${destino}_${origen}`;

        let tasa;
        let tasaMostrar;
        let resultado;

        if (tasasData[key]) {
            // Si existe la tasa directa
            // Para compra (cliente compra crypto) usamos tasa de venta
            // Para venta (cliente vende crypto) usamos tasa de compra
            tasa = tasasData[key][tipo === 'compra' ? 'venta' : 'compra'];
            tasaMostrar = tasa;
            // Si es compra dividimos, si es venta multiplicamos
            resultado = tipo === 'compra' ? monto / tasa : monto * tasa;
        } else if (tasasData[keyInverso]) {
            // Si existe la tasa inversa
            // Para compra usamos tasa de venta inversa
            // Para venta usamos tasa de compra inversa
            tasa = tasasData[keyInverso][tipo === 'compra' ? 'venta' : 'compra'];
            tasaMostrar = tasa;
            // Si es compra dividimos, si es venta multiplicamos
            resultado = tipo === 'compra' ? monto / tasa : monto * tasa;
        } else {
            tasa = 1;
            tasaMostrar = 1;
            resultado = monto;
        }

        montoOrigen.textContent = monto.toFixed(2);
        montoConvertido.textContent = resultado.toFixed(2);
        labelOrigen.textContent = origen;
        labelDestino.textContent = destino;

        // Actualizar el resumen de la operación con texto descriptivo
        let resumenTexto = '';
        if (tipo === 'compra') {
            resumenTexto = `Por ${monto.toFixed(2)} ${origen}, recibirás ${resultado.toFixed(2)} ${destino}`;
        } else {
            resumenTexto = `Por ${monto.toFixed(2)} ${origen}, recibirás ${resultado.toFixed(2)} ${destino}`;
        }
        resumenOperacion.textContent = resumenTexto;

        // Mostrar la tasa de manera diferente según el tipo de operación y monedas
        if (tipo === 'compra' && (origen === 'USD' || origen === 'PEN')) {
            tasaOrigen.textContent = origen;
            tasaValor.textContent = tasaMostrar.toFixed(3);
            tasaDestino.textContent = destino;
            // Invertir la presentación de la tasa para compra de USD/PEN a crypto
            document.getElementById('tasa_linea_detalle').innerHTML = 
                `Tasa: ${tasaMostrar.toFixed(3)} ${origen} = 1 ${destino}`;
        } else {
            tasaOrigen.textContent = origen;
            tasaValor.textContent = tasaMostrar.toFixed(3);
            tasaDestino.textContent = destino;
            document.getElementById('tasa_linea_detalle').innerHTML = 
                `Tasa: 1 ${origen} = ${tasaMostrar.toFixed(3)} ${destino}`;
        }

        validarMinimoMonto();

        // Actualizar los parámetros del botón de realizar cambio
        const loginBtn = document.getElementById('realizar-cambio-btn');
        if (loginBtn) {
            const params = new URLSearchParams({
                'monto': monto.toString(),
                'moneda_origen': origen,
                'moneda_destino': destino,
                'tipo_operacion': tipo,
                'tasa': tasaMostrar.toFixed(4)
            });

            const baseUrl = loginBtn.href.split('?')[0];
            if (loginBtn.href.includes('login')) {
                // Si es el botón de login, agregar el next parameter con los parámetros de la calculadora
                const dashboardUrl = `/usuarios/dashboard/?${params.toString()}`;
                params.set('next', dashboardUrl);
                loginBtn.href = `${baseUrl}?${params.toString()}`;
            } else {
                // Si es el botón del dashboard, agregar los parámetros directamente
                loginBtn.href = `${baseUrl}?${params.toString()}`;
            }
        }
    }

    function validarMinimoMonto() {
        const monto = parseFloat(inputMonto.value) || 0;
        const errorMonto = document.getElementById('error_monto');
        const btnRealizarCambio = document.querySelector('.btn-realizar-cambio');

        if (monto < 50) {
            errorMonto.textContent = 'El monto mínimo para operar es de 50';
            if (btnRealizarCambio) {
                btnRealizarCambio.style.pointerEvents = 'none';
                btnRealizarCambio.style.opacity = '0.5';
            }
        } else {
            errorMonto.textContent = '';
            if (btnRealizarCambio) {
                btnRealizarCambio.style.pointerEvents = 'auto';
                btnRealizarCambio.style.opacity = '1';
            }
        }
    }
}); 