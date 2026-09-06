// ============================================================================
// sistemas.js - LÓGICA DEL MÓDULO DE SISTEMAS
// ============================================================================

const API_SISTEMAS = '/sistemas'; 

async function cargarSistemas() {
    const contenedor = document.getElementById("contenedor-sistemas");
    if (!contenedor) return;

    contenedor.innerHTML = "<p>Cargando información de sistemas...</p>";

    try {
       contenedor.innerHTML = "<p style='color: #58a598; font-weight: bold;'>Módulo inicializado correctamente.</p>";
    } catch (error) {
        console.error("Error al cargar los sistemas:", error);
        contenedor.innerHTML = "<p style='color: red;'>Error de conexión.</p>";
    }
}

function abrirNuevoSistema() {
    alert("Aquí abriremos el modal para dar de alta un sistema nuevo.");
}

// ============================================================================
// --- LÓGICA: NOTA DE SALIDA DE EQUIPOS (PDF Y AUTOCOMPLETADO) ---
// ============================================================================

function abrirModalNotaSalida() {
    document.getElementById('modal-nota-salida').style.display = 'flex';
}

function cerrarModalNotaSalida() {
    document.getElementById('modal-nota-salida').style.display = 'none';
    document.getElementById('form-nota-salida').reset();
}

const inicializarNotaSalida = () => {
    const form = document.getElementById('form-nota-salida');
    const inputInventario = document.getElementById('nota-inventario');
    if (!form) return;

    // ✨ NUEVO: Lógica de Autocompletado al salir del campo (blur)
    if (inputInventario) {
        inputInventario.addEventListener('blur', async () => {
            const numero = inputInventario.value.trim();
            if (!numero) return;

            try {
                // Consultamos el bien patrimonial usando la ruta de Patrimonio
                const response = await fetch(`/patrimonio/${numero}`, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });

                if (response.ok) {
                    const bien = await response.json();
                    // Autocompletamos los campos del modal
                    document.getElementById('nota-tipo').value = bien.tipo || bien.descripcion_bien || '';
                    document.getElementById('nota-marca').value = bien.marca || '';
                    document.getElementById('nota-serie').value = bien.serie || '';
                }
            } catch (error) {
                console.log("Inventario no encontrado o error de red:", error);
            }
        });
    }

    // Lógica para enviar el formulario y generar PDF
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const datos = {
            numero_inventario: document.getElementById('nota-inventario').value.trim() || null,
            cantidad: parseInt(document.getElementById('nota-cantidad').value) || 1,
            tipo_manual: document.getElementById('nota-tipo').value.trim() || null,
            marca_manual: document.getElementById('nota-marca').value.trim() || null,
            serie_manual: document.getElementById('nota-serie').value.trim() || null,
            nombre_apellido: document.getElementById('nota-nombre').value.trim(),
            cuil_cuit: document.getElementById('nota-cuil').value.trim(),
            motivo: document.getElementById('nota-motivo').value.trim()
        };

        const botonSubmit = form.querySelector('button[type="submit"]');

        try {
            botonSubmit.disabled = true;
            botonSubmit.textContent = 'Generando...';

            const response = await fetch('/sistemas/nota-salida/generar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(datos)
            });

            if (!response.ok) throw new Error("No se pudo generar el PDF. Verifica que el servidor esté funcionando.");

            // Descargar y abrir el PDF
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            window.open(url, '_blank');
            
            // Cerramos la ventanita
            cerrarModalNotaSalida();
            
        } catch (error) {
            alert("Error al generar la nota: " + error.message);
        } finally {
            botonSubmit.disabled = false;
            botonSubmit.textContent = '🖨️ Generar PDF';
        }
    });
};

// ============================================================================
// ARRANQUE DE LA PÁGINA (INIT)
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    if (typeof verificarAcceso === 'function') {
        verificarAcceso();
    }
    cargarSistemas();
    inicializarNotaSalida();
});