// ============================================================================
// imprimir_etiquetas.js - GENERADOR DE CÓDIGOS DE BARRAS EN LOTE
// ============================================================================

async function cargarEtiquetas() {
    const urlParams = new URLSearchParams(window.location.search);
    const numerosStr = urlParams.get('numeros');
    
    if (!numerosStr) {
        document.getElementById('contenedor-etiquetas').innerHTML = '<p style="text-align:center; padding: 20px;">No se enviaron números para imprimir.</p>';
        return;
    }

    const numerosArray = numerosStr.split(',');
    const jwtToken = localStorage.getItem('token'); 

    try {
        const response = await fetch('/patrimonio/barcode/lote', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${jwtToken}`
            },
            body: JSON.stringify({ numeros: numerosArray })
        });

        const data = await response.json();
        const contenedor = document.getElementById('contenedor-etiquetas');
        contenedor.innerHTML = '';

        if (!data.etiquetas || data.etiquetas.length === 0) {
            contenedor.innerHTML = '<p style="text-align:center; color:red; padding: 20px;">No se encontraron etiquetas para los equipos seleccionados.</p>';
            return;
        }
        
        // 1. Inyectamos la estructura usando una etiqueta <svg> para cada código
        data.etiquetas.forEach(eti => {
            // Limpiamos el ID HTML por si hay espacios o símbolos
            const idLimpio = String(eti.numero_inventario).replace(/[^a-zA-Z0-9]/g, '');
            
            contenedor.innerHTML += `
                <div class="etiqueta">
                    <div class="codigo-container">
                        <img class="logo-izq" src="/archivos/img/logo_barras.png" alt="Logo GCBA">
                        <svg id="barcode-${idLimpio}" class="barcode-der"></svg>
                    </div>
                    <div class="descripcion">${eti.descripcion}</div>
                </div>
            `;
        });

        // 2. Dibujamos la estética exacta de EAN-13 usando JsBarcode
        data.etiquetas.forEach(eti => {
            const idLimpio = String(eti.numero_inventario).replace(/[^a-zA-Z0-9]/g, '');
            
            // EAN-13 exige exactamente 12 dígitos, rellenamos con ceros a la izquierda
            const numeroPadded = String(eti.numero_inventario).padStart(12, '0');
            
            try {
                JsBarcode(`#barcode-${idLimpio}`, numeroPadded, {
                    format: "EAN13", // Genera la agrupación visual y las líneas extendidas
                    font: "Arial, sans-serif", // Tipografía sin punto en el cero
                    fontSize: 20, 
                    textMargin: 4,
                    width: 2, 
                    height: 55,
                    margin: 0,
                    displayValue: true
                });
            } catch (err) {
                // Fallback de seguridad: El EAN-13 falla si hay letras en el número. 
                // Si el número de inventario tiene letras, dibuja uno clásico.
                JsBarcode(`#barcode-${idLimpio}`, eti.numero_inventario, {
                    format: "CODE128",
                    font: "Arial, sans-serif",
                    fontSize: 20,
                    width: 2,
                    height: 55,
                    margin: 0,
                    displayValue: true
                });
            }
        });

    } catch (error) {
        console.error("Error al generar etiquetas:", error);
        alert("Hubo un error al generar los códigos de barras.");
    }
}

document.addEventListener('DOMContentLoaded', () => {
    cargarEtiquetas();
});