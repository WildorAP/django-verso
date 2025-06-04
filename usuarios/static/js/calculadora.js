document.addEventListener('DOMContentLoaded', function() {
    // Obtener las tasas de cambio desde el elemento data-tasas o extraerlas del HTML
    const tasasElement = document.getElementById('tasas-data');
    let tasas = {};
    
    try {
        // Intentar obtener las tasas del atributo data-tasas
        if (tasasElement) {
            const tasasJSON = tasasElement.getAttribute('data-tasas');
            console.log('Tasas JSON recibidas:', tasasJSON);
            
            // Si hay un JSON válido, parsearlo
            if (tasasJSON && tasasJSON.trim() !== '') {
                try {
                    tasas = JSON.parse(tasasJSON);
                    console.log('Tasas parseadas exitosamente:', tasas);
                } catch (error) {
                    console.error('Error al parsear JSON:', error);
                    // Continuar con el método alternativo
                }
            }
        }
        
        // Si no pudimos obtener tasas del JSON, extraerlas del HTML
        if (Object.keys(tasas).length === 0) {
            console.log('Extrayendo tasas del HTML...');
            const tasasList = document.querySelectorAll('.tasas-actuales ul li');
            
            tasasList.forEach(item => {
                const texto = item.textContent.trim();
                const match = texto.match(/([A-Z]+)\s*→\s*([A-Z]+):\s*([\d.,]+)/);
                
                if (match) {
                    const origen = match[1];
                    const destino = match[2];
                    // Limpiar el valor y convertir a número
                    const valor = parseFloat(match[3].replace(',', '.'));
                    
                    // Guardar en el objeto tasas
                    const clave = `${origen}_${destino}`;
                    tasas[clave] = valor;
                    console.log(`Tasa extraída: ${clave} = ${valor}`);
                }
            });
        }
    } catch (error) {
        console.error('Error al obtener tasas:', error);
    }
    
    // Si no hay tasas, crear un objeto vacío
    if (!tasas || Object.keys(tasas).length === 0) {
        console.warn('No se pudieron obtener tasas, usando objeto vacío');
        tasas = {};
    }
    
    // Elementos del formulario
    const montoInput = document.getElementById('monto');
    const monedaOrigenSelect = document.getElementById('moneda_origen');
    const monedaDestinoSelect = document.getElementById('moneda_destino');
    
    // Elementos para mostrar el resultado
    const montoOrigenSpan = document.getElementById('monto_origen');
    const labelOrigenSpan = document.getElementById('label_origen');
    const montoConvertidoSpan = document.getElementById('monto_convertido');
    const labelDestinoSpan = document.getElementById('label_destino');
    const tasaOrigenSpan = document.getElementById('tasa_origen');
    const tasaValorSpan = document.getElementById('tasa_valor');
    const tasaDestinoSpan = document.getElementById('tasa_destino');
    
    // Función para actualizar el cálculo
    function actualizarCalculo() {
        const monto = parseFloat(montoInput.value.replace(',', '.')) || 0;
        const monedaOrigen = monedaOrigenSelect.value;
        const monedaDestino = monedaDestinoSelect.value;
        
        // Buscar la tasa de cambio correcta
        const tasaClave = `${monedaOrigen}_${monedaDestino}`;
        console.log('Buscando tasa para:', tasaClave);
        
        // Verificar si la tasa existe en el objeto
        let tasa = null;
        if (tasas[tasaClave] !== undefined) {
            tasa = parseFloat(String(tasas[tasaClave]).replace(',', '.'));
            console.log('Tasa encontrada:', tasa);
        } else {
            console.log('Tasa no encontrada directamente');
        }
        
        // Si no existe la tasa directa, intentamos calcularla
        if ((tasa === null || isNaN(tasa)) && monedaOrigen !== monedaDestino) {
            // Intentar convertir a través de USDT
            const tasaOrigenUSDT = tasas[`${monedaOrigen}_USDT`];
            const tasaUSDTDestino = tasas[`USDT_${monedaDestino}`];
            
            console.log('Intentando calcular vía USDT:', monedaOrigen, 'a USDT:', tasaOrigenUSDT, 'USDT a', monedaDestino, ':', tasaUSDTDestino);
            
            if (tasaOrigenUSDT !== undefined && tasaUSDTDestino !== undefined) {
                const tasaOrigen = parseFloat(String(tasaOrigenUSDT).replace(',', '.'));
                const tasaDestino = parseFloat(String(tasaUSDTDestino).replace(',', '.'));
                
                if (!isNaN(tasaOrigen) && !isNaN(tasaDestino)) {
                    tasa = tasaOrigen * tasaDestino;
                    console.log('Tasa calculada vía USDT:', tasa);
                }
            }
            
            // Si todavía no tenemos tasa, probar con la inversa
            if (tasa === null || isNaN(tasa)) {
                const tasaInversa = tasas[`${monedaDestino}_${monedaOrigen}`];
                console.log('Intentando inversa:', monedaDestino, 'a', monedaOrigen, ':', tasaInversa);
                
                if (tasaInversa !== undefined) {
                    const tasaInv = parseFloat(String(tasaInversa).replace(',', '.'));
                    if (!isNaN(tasaInv) && tasaInv !== 0) {
                        tasa = 1 / tasaInv;
                        console.log('Tasa calculada inversa:', tasa);
                    }
                }
            }
            
            // Si todo falla, usar 1
            if (tasa === null || isNaN(tasa)) {
                tasa = 1;
                console.log('Usando tasa predeterminada:', tasa);
            }
        } else if (monedaOrigen === monedaDestino) {
            // Si son la misma moneda, la tasa es 1
            tasa = 1;
            console.log('Misma moneda, tasa = 1');
        }
        
        // Calcular el monto convertido
        const montoConvertido = monto * tasa;
        console.log('Monto convertido:', monto, 'x', tasa, '=', montoConvertido);
        
        // Actualizar la interfaz
        montoOrigenSpan.textContent = monto.toFixed(2);
        labelOrigenSpan.textContent = monedaOrigen;
        montoConvertidoSpan.textContent = montoConvertido.toFixed(2);
        labelDestinoSpan.textContent = monedaDestino;
        tasaOrigenSpan.textContent = monedaOrigen;
        tasaValorSpan.textContent = tasa.toFixed(4);
        tasaDestinoSpan.textContent = monedaDestino;
    }
    
    // Agregar eventos para actualizar el cálculo en tiempo real
    montoInput.addEventListener('input', actualizarCalculo);
    monedaOrigenSelect.addEventListener('change', actualizarCalculo);
    monedaDestinoSelect.addEventListener('change', actualizarCalculo);
    
    // Ejecutar el cálculo inicial
    actualizarCalculo();
});