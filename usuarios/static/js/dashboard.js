document.addEventListener('DOMContentLoaded', function() {
    // Elementos del DOM
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
    const realizarCambioBtn = document.getElementById('realizar-cambio-btn');

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

    // Configuración inicial por defecto
    tipoOperacion.value = 'venta';
    btnVenta.classList.add('active');
    btnCompra.classList.remove('active');
    actualizarOpcionesMonedas('venta');

    // Obtener parámetros de la URL al cargar
    const urlParams = new URLSearchParams(window.location.search);
    const montoParam = urlParams.get('monto');
    const monedaOrigenParam = urlParams.get('moneda_origen');
    const monedaDestinoParam = urlParams.get('moneda_destino');
    const tipoOperacionParam = urlParams.get('tipo_operacion');

    // Solo establecer valores de la URL si es la primera carga
    if (!sessionStorage.getItem('dashboardLoaded')) {
        if (tipoOperacionParam) {
            tipoOperacion.value = tipoOperacionParam;
            activarBotonSeleccionado(tipoOperacionParam);
            actualizarOpcionesMonedas(tipoOperacionParam);
        }

        if (montoParam) {
            inputMonto.value = montoParam;
        }
        
        if (monedaOrigenParam) {
            selectOrigen.value = monedaOrigenParam;
            actualizarOpcionesDestino();
        }
        
        if (monedaDestinoParam) {
            selectDestino.value = monedaDestinoParam;
        }

        // Marcar que ya se cargó el dashboard
        sessionStorage.setItem('dashboardLoaded', 'true');
    }

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
            tasa = tasasData[key][tipo === 'compra' ? 'venta' : 'compra'];
            tasaMostrar = tasa;
            resultado = tipo === 'compra' ? monto / tasa : monto * tasa;
        } else if (tasasData[keyInverso]) {
            tasa = tasasData[keyInverso][tipo === 'compra' ? 'venta' : 'compra'];
            tasaMostrar = tasa;
            resultado = tipo === 'compra' ? monto / tasa : monto * tasa;
        } else {
            tasa = 1;
            tasaMostrar = 1;
            resultado = monto;
        }

        // Actualizar los valores mostrados
        montoOrigen.textContent = monto.toFixed(2);
        montoConvertido.textContent = resultado.toFixed(2);
        labelOrigen.textContent = origen;
        labelDestino.textContent = destino;

        let resumenTexto = '';
        if (tipo === 'compra') {
            resumenTexto = `Por ${monto.toFixed(2)} ${origen}, recibirás ${resultado.toFixed(2)} ${destino}`;
        } else {
            resumenTexto = `Por ${monto.toFixed(2)} ${origen}, recibirás ${resultado.toFixed(2)} ${destino}`;
        }
        resumenOperacion.textContent = resumenTexto;

        if (tipo === 'compra' && (origen === 'USD' || origen === 'PEN')) {
            tasaOrigen.textContent = origen;
            tasaValor.textContent = tasaMostrar.toFixed(3);
            tasaDestino.textContent = destino;
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

        // Actualizar la URL del botón de realizar cambio con los valores actuales
        if (realizarCambioBtn) {
            const currentParams = new URLSearchParams();
            currentParams.append('monto', monto.toString());
            currentParams.append('moneda_origen', origen);
            currentParams.append('moneda_destino', destino);
            currentParams.append('tipo_operacion', tipo);
            currentParams.append('tasa', tasaMostrar.toString());

            const baseUrl = realizarCambioBtn.getAttribute('href').split('?')[0];
            realizarCambioBtn.href = `${baseUrl}?${currentParams.toString()}`;

            // Limpiar sessionStorage cuando se actualiza la calculadora
            sessionStorage.removeItem('dashboardLoaded');
        }
    }

    function validarMinimoMonto() {
        const monto = parseFloat(inputMonto.value) || 0;
        const errorMonto = document.getElementById('error_monto');

        if (monto < 50) {
            errorMonto.textContent = 'El monto mínimo para operar es de 50';
            if (realizarCambioBtn) {
                realizarCambioBtn.style.pointerEvents = 'none';
                realizarCambioBtn.style.opacity = '0.5';
            }
        } else {
            errorMonto.textContent = '';
            if (realizarCambioBtn) {
                realizarCambioBtn.style.pointerEvents = 'auto';
                realizarCambioBtn.style.opacity = '1';
            }
        }
    }
}); 