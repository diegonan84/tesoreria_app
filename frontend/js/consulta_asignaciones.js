// ============================================================================
// consulta_asignaciones.js - ELEMENTOS POR USUARIO O DESTINO (vista unificada)
//   Solo se contabilizan/muestran los elementos con puesto HOME (teletrabajo)
// ============================================================================

const CONSULTA_API = '/patrimonio';

function getTokenHeaders() {
    return { 'Authorization': `Bearer ${localStorage.getItem('token')}` };
}

async function cargarListado(buscar) {
    const tbody = document.getElementById('tabla-unificado-body');
    const badge = document.getElementById('badge-total-unificado');
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Cargando...</td></tr>';

    try {
        let url = `${CONSULTA_API}/asignaciones/lista-completa`;
        if (buscar) url += `?buscar=${encodeURIComponent(buscar)}`;

        const res = await fetch(url, { headers: getTokenHeaders() });
        if (!res.ok) throw new Error('Error al obtener el listado');

        const data = await res.json();
        const resultados = data.resultados || [];
        renderizarListado(resultados);

        if (badge) {
            badge.style.display = 'inline-block';
            badge.innerText = `Usuarios / Lugares: ${resultados.length}`;
        }
    } catch (error) {
        console.error('Error:', error);
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #dc3545;">Error al cargar el listado.</td></tr>';
    }
}

function renderizarListado(resultados) {
    const tbody = document.getElementById('tabla-unificado-body');
    tbody.innerHTML = '';

    if (resultados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No hay usuarios ni lugares que coincidan.</td></tr>';
        return;
    }

    resultados.forEach(r => {
        const tr = document.createElement('tr');
        const esLugar = r.tipo === 'destino';
        const esPendiente = r.tipo === 'pendiente';
        const esExterno = r.tipo === 'externo';
        let badgeTipo = '';
        if (esLugar) badgeTipo = '<span style="background:#e7f3ff;color:#1a6fb5;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:bold;">Lugar</span>';
        else if (esPendiente) badgeTipo = '<span style="background:#f3f0e7;color:#9c6a1a;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:bold;">Por vincular</span>';
        else if (esExterno) badgeTipo = '<span style="background:#e8e8e8;color:#444;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:bold;">Externo</span>';
        else badgeTipo = '<span style="background:#e8f5e9;color:#2e7d32;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:bold;">Usuario</span>';
        tr.innerHTML = `
            <td>${badgeTipo}</td>
            <td>${escapeHTML(r.nombre)}</td>
            <td style="color:#666;">${escapeHTML(r.sub)}</td>
            <td style="text-align: center; font-weight: bold; color: #b45309;">${r.cantidad_home}</td>
            <td style="text-align: center;">
                <button class="btn-patrimonio" style="font-size: 12px; padding: 4px 14px;" data-ver="${r.tipo}" data-id="${r.id ?? ''}" data-texto="${escapeHTML(r.texto || '')}">Ver</button>
            </td>`;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('button[data-ver]').forEach(btn => {
        btn.addEventListener('click', () => cargarDetalle(btn));
    });
}

function cerrarModalDetalle() {
    const modal = document.getElementById('modal-detalle-asign');
    if (modal) modal.style.display = 'none';
}

async function cargarDetalle(btn) {
    const tipo = btn.dataset.ver;
    const id = btn.dataset.id;
    const texto = btn.dataset.texto;
    const titulo = document.getElementById('titulo-detalle');
    const tbody = document.getElementById('tabla-detalle-body');
    const modal = document.getElementById('modal-detalle-asign');

    if (!modal) return;
    titulo.innerText = 'Cargando...';
    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">Cargando...</td></tr>';
    modal.style.display = 'flex';

    try {
        let url = `${CONSULTA_API}/asignaciones/detalle-unificado?tipo=${tipo}`;
        if (tipo === 'pendiente' || tipo === 'externo') {
            url += `&texto=${encodeURIComponent(texto)}`;
        } else {
            url += `&id=${id}`;
        }
        const res = await fetch(url, { headers: getTokenHeaders() });
        if (!res.ok) throw new Error('Error al obtener elementos');

        const data = await res.json();
        const items = data.items || [];
        tbody.innerHTML = '';

        const etiqueta = tipo === 'destino' ? `Elementos en ${data.nombre}` : `Elementos de ${data.nombre}`;
        titulo.innerText = `${etiqueta} — en teletrabajo (HOME): ${items.length}`;

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">Sin elementos con puesto HOME.</td></tr>';
            return;
        }

        items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${escapeHTML(item.numero_inventario)}</td>
                <td>${escapeHTML(item.tipo)}</td>
                <td>${escapeHTML(item.descripcion)}</td>
                <td>${escapeHTML(item.marca)} ${escapeHTML(item.modelo)}</td>
                <td>${escapeHTML(item.serie)}</td>
                <td>${escapeHTML(item.nombre_de_equipo)}</td>
                <td>${escapeHTML(item.puesto)}</td>
                <td>${escapeHTML(item.anio)}</td>
                <td>${escapeHTML(item.estado)}</td>`;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error:', error);
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #dc3545;">Error al cargar los elementos.</td></tr>';
        titulo.innerText = 'Error al cargar detalle';
    }
}

async function reconciliar() {
    if (!confirm('¿Vincular automáticamente los datos existentes que tienen texto de Usuario/Destino pero aún no están vinculados a un usuario o lugar?')) return;

    const btn = document.getElementById('btn-reconciliar');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Vinculando...';

    try {
        const res = await fetch(`${CONSULTA_API}/asignaciones/reconciliar`, {
            method: 'POST',
            headers: getTokenHeaders()
        });
        if (!res.ok) throw new Error('Error al reconciliar');

        const data = await res.json();

        const detalles = [];
        if (data.vinculados_a_usuario > 0) detalles.push(`Usuarios: ${data.vinculados_a_usuario}`);
        if (data.vinculados_a_lugar > 0) detalles.push(`Lugares: ${data.vinculados_a_lugar}`);

        let mensaje = `Vinculados → ${detalles.join(' · ') || 'ninguno'}.`;
        const pendientes = Object.entries(data.pendientes || {});
        if (pendientes.length > 0) {
            const ejemplos = pendientes.map(([texto, n]) => `"${texto}" (${n})`).slice(0, 8).join(', ');
            mensaje += `\n\nSiguen sin vincular (revisar a mano): ${ejemplos}`;
        }
        alert(mensaje);

        cargarListado('');
        if (document.getElementById('modal-detalle-asign')) {
            document.getElementById('modal-detalle-asign').style.display = 'none';
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al vincular datos existentes.');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const btnBuscar = document.getElementById('btn-buscar-unificado');
    const btnLimpiar = document.getElementById('btn-limpiar-unificado');
    const input = document.getElementById('input-buscar-unificado');
    const btnReconciliar = document.getElementById('btn-reconciliar');

    if (btnBuscar && btnLimpiar && input) {
        btnBuscar.addEventListener('click', () => cargarListado(input.value.trim()));
        input.addEventListener('keypress', (e) => { if (e.key === 'Enter') cargarListado(input.value.trim()); });
        btnLimpiar.addEventListener('click', () => {
            input.value = '';
            cargarListado('');
        });
    }

    if (btnReconciliar) {
        btnReconciliar.addEventListener('click', reconciliar);
    }

    cargarListado('');
});

// Re-export global para console
window.cargarListado = cargarListado;