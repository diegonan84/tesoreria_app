// ============================================================================
// notificaciones.js - GESTIÓN DE AVISOS Y CAMPANA
// ============================================================================

function _auth() { return { "Authorization": `Bearer ${localStorage.getItem("token")}` }; }

function _horaFromISO(iso) {
    const d = new Date(iso);
    const h = String(d.getHours()).padStart(2, "0");
    const m = String(d.getMinutes()).padStart(2, "0");
    return `${h}:${m}`;
}

// Renderiza un recordatorio de agenda (color ámbar, distinto a avisos generales)
function renderAgendaItem(ev, tipo) {
    const d = new Date(ev.fecha_evento);
    const fechaTxt = d.toLocaleDateString("es-AR");
    const etiqueta = tipo === "pendiente" ? "⏰ Pendiente" : "Próximo";
    return `
        <div style="padding:10px 12px; border-bottom:1px solid #ede2b8; background:#fffbe6; border-left:4px solid #ffcc00; text-align:left;">
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                <strong style="color:#8a6d00; font-size:12px;">🗓️ ${escapeHTML(ev.titulo)}</strong>
                <span style="color:#b08a00; font-size:10px; font-weight:bold;">${etiqueta}</span>
            </div>
            <div style="color:#8a6d00; font-size:11px;">${fechaTxt} · ${_horaFromISO(ev.fecha_evento)}</div>
            ${ev.descripcion ? `<div style="color:#777; font-size:11px; margin-top:3px;">${escapeHTML(ev.descripcion)}</div>` : ""}
            ${tipo === "pendiente" ? `
                <button onclick="marcarVistoAgenda(${ev.id})" style="margin-top:6px; border:none; background:#ffcc00; color:#1a3644; border-radius:4px; padding:4px 10px; font-size:11px; font-weight:bold; cursor:pointer;">✔ Descartar</button>` : ""}
        </div>`;
}

async function cargarCampana() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
        const [res, resAgenda] = await Promise.all([
            fetch(`${API_URL}/notificaciones/me`, { headers: _auth() }),
            fetch(`${API_URL}/agenda/pendientes`, { headers: _auth() })
        ]);
        const data = res.ok ? await res.json() : { no_leidas: 0, ultimas: [] };
        const agenda = resAgenda.ok ? await resAgenda.json() : { cuenta: 0, pendientes: [], proximos: [] };

        const badge = document.getElementById("badge-notif");
        const lista = document.getElementById("lista-notificaciones");

        const total = (data.no_leidas || 0) + (agenda.cuenta || 0);
        if (total > 0) {
            badge.style.display = "block";
            badge.innerText = total > 99 ? "99+" : total;
        } else badge.style.display = "none";

        // --- SECCIÓN AVISOS GENERALES ---
        let html = `
            <div style="padding:8px 12px; background:#f4f6f7; font-weight:bold; color:#1a3644; font-size:11px; text-transform:uppercase; border-bottom:1px solid #e6e9ea;">🔔 Avisos Generales</div>`;
        if (data.ultimas.length === 0) {
            html += `<div style="padding:15px; text-align:center; color:#666; font-size:12px;">No hay avisos recientes.</div>`;
        } else {
            data.ultimas.forEach(n => {
                const fechaTxt = new Date(n.fecha + "Z").toLocaleDateString("es-AR");
                html += `
                    <div style="padding:12px; border-bottom:1px solid #eee; text-align:left; background:white;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <strong style="color: #1a3644; font-size: 13px;">${escapeHTML(n.titulo)}</strong>
                            <span style="color: #999; font-size: 10px;">${escapeHTML(fechaTxt)}</span>
                        </div>
                        <div style="color: #555; font-size: 12px; line-height: 1.4;">${escapeHTML(n.mensaje)}</div>
                    </div>`;
            });
        }

        // --- SECCIÓN AGENDA / RECORDATORIOS (color ámbar distinto) ---
        html += `
            <div style="padding:8px 12px; background:#fff3c4; font-weight:bold; color:#8a6d00; font-size:11px; text-transform:uppercase; border-top:2px solid #ffcc00;">📅 Agenda / Recordatorios</div>`;
        if (agenda.pendientes.length === 0 && agenda.proximos.length === 0) {
            html += `<div style="padding:15px; text-align:center; color:#999; font-size:12px;">Sin recordatorios.</div>`;
        } else {
            agenda.pendientes.forEach(ev => { html += renderAgendaItem(ev, "pendiente"); });
            agenda.proximos.forEach(ev => { html += renderAgendaItem(ev, "proximo"); });
            html += `
                <a href="/calendario" style="display:block; padding:9px 12px; background:#ffcc00; color:#1a3644; font-weight:bold; text-align:center; font-size:12px; text-decoration:none;" onclick="event.stopPropagation()">Abrir Calendario →</a>`;
        }

        lista.innerHTML = html;
    } catch (e) {}
}

// Descarta un recordatorio puntual
async function marcarVistoAgenda(id) {
    try {
        await fetch(`${API_URL}/agenda/eventos/${id}/visto`, { method: "POST", headers: _auth() });
        cargarCampana();
    } catch (e) {}
}

function toggleCampana(event) {
    if (event) event.stopPropagation();
    const dropdown = document.getElementById("campana-dropdown");
    if (dropdown) {
        const estaAbierto = dropdown.style.display === "block";
        document.querySelectorAll('.perfil-dropdown, .avisos-dropdown').forEach(d => d.style.display = 'none');
        dropdown.style.display = estaAbierto ? "none" : "block";
        
        const badge = document.getElementById("badge-notif");
        if (!estaAbierto && badge.style.display === "block") {
            badge.style.display = "none";
            fetch(`${API_URL}/notificaciones/me/leer`, { method: "PUT", headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` } });
            fetch(`${API_URL}/agenda/pendientes/visto`, { method: "PUT", headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` } });
        }
    }
}

window.addEventListener("click", () => {
    const campana = document.getElementById("campana-dropdown");
    if (campana) campana.style.display = "none";
});

// ============================================================================
// PANEL DE ADMINISTRACIÓN DE AVISOS GLOBALES
// ============================================================================

async function enviarNuevaNotificacion(event) {
    event.preventDefault();
    const titulo = document.getElementById("notif-titulo").value;
    const mensaje = document.getElementById("notif-mensaje").value;
    const token = localStorage.getItem("token");

    try {
        const res = await fetch(`${API_URL}/admin/notificaciones`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify({ titulo, mensaje })
        });
        
        if (res.ok) {
            alert("Aviso enviado a todo el equipo.");
            document.getElementById("form-notif").reset();
        } else {
            alert("Error al enviar la notificación.");
        }
    } catch (e) { 
        alert("Error de conexión"); 
    }
}