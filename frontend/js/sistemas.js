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
// --- LÓGICA: NOTAS DE SALIDA (PDF + REGISTRO + HISTORIAL) ---
// ============================================================================

function togglePanelNotas() {
    const panel = document.getElementById("panel-notas");
    if (panel.style.display === "none") {
        panel.style.display = "block";
        cargarNotasSalida();
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        panel.style.display = "none";
    }
}

async function cargarNotasSalida() {
    const tabla = document.getElementById("tabla-notas");
    if (!tabla) return;
    try {
        const response = await fetch('/sistemas/notas-salida', {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (!response.ok) throw new Error("Error al cargar las notas");
        const notas = await response.json();

        if (notas.length === 0) {
            tabla.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#999; padding: 15px;">Todavía no se generaron notas de salida.</td></tr>`;
            return;
        }

        tabla.innerHTML = notas.map(n => {
            const fecha = new Date(n.fecha_creacion + "Z").toLocaleString('es-AR', {
                day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
            });
            const equipo = [n.tipo, n.marca, n.serie, n.numero_inventario ? `Inv: ${n.numero_inventario}` : '']
                .filter(Boolean).join(" · ");
            return `
                <tr>
                    <td style="font-weight: bold; color: #1a3644;">${escapeHTML(n.numero)}</td>
                    <td>${escapeHTML(fecha)}</td>
                    <td>${escapeHTML(n.nombre_apellido)}<br><small style="color:#999;">${escapeHTML(n.cuil_cuit)}</small></td>
                    <td>${escapeHTML(n.motivo)}</td>
                    <td>${escapeHTML(equipo)}</td>
                    <td>${escapeHTML(n.creador_nombre || n.creador_email || "-")}</td>
                    <td>
                        <a href="${n.archivo_url}" target="_blank" class="btn-mini notas" style="background:#fd7e14; color:white; padding:4px 10px; border-radius:4px; text-decoration:none; font-size:12px;">🖨️ Ver PDF</a>
                    </td>
                </tr>`;
        }).join("");
    } catch (error) {
        tabla.innerHTML = `<tr><td colspan="7" style="text-align:center; color:red; padding: 15px;">Error al cargar las notas: ${escapeHTML(error.message)}</td></tr>`;
    }
}

async function exportarNotasSalida() {
    try {
        const response = await fetch('/sistemas/notas-salida/exportar', {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (!response.ok) throw new Error("Error al exportar");
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Notas_de_Salida.xlsx';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert("Error al exportar: " + error.message);
    }
}

async function importarNotasSalida(input) {
    if (!input.files.length) return;
    const formData = new FormData();
    formData.append('file', input.files[0]);
    try {
        const response = await fetch('/sistemas/notas-salida/importar', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
            body: formData
        });
        if (!response.ok) throw new Error("No se pudo importar");
        const resultado = await response.json();
        let msg = `✅ Se importaron ${resultado.importados} notas de salida.`;
        if (resultado.errores && resultado.errores.length) {
            msg += `\n\n⚠️ ${resultado.errores.length} filas con errores:\n` + resultado.errores.slice(0, 10).join("\n");
        }
        alert(msg);
        cargarNotasSalida();
    } catch (error) {
        alert("Error al importar: " + error.message);
    } finally {
        input.value = "";
    }
}

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

            // Refrescamos el historial de notas registradas
            cargarNotasSalida();
            
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