// ============================================================================
// notificaciones.js - GESTIÓN DE AVISOS Y CAMPANA
// ============================================================================

async function cargarCampana() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/notificaciones/me`, { headers: { "Authorization": `Bearer ${token}` } });
        if (res.ok) {
            const data = await res.json();
            const badge = document.getElementById("badge-notif");
            const lista = document.getElementById("lista-notificaciones");

            if (data.no_leidas > 0) {
                badge.style.display = "block";
                badge.innerText = data.no_leidas;
            } else badge.style.display = "none";

            lista.innerHTML = "";
            if (data.ultimas.length === 0) {
                lista.innerHTML = `<div style="padding: 15px; text-align: center; color: #666; font-size: 12px;">No hay avisos recientes.</div>`;
            } else {
                data.ultimas.forEach(n => {
                    const fechaTxt = new Date(n.fecha + "Z").toLocaleDateString('es-AR');
                    lista.innerHTML += `
                        <div style="padding: 12px; border-bottom: 1px solid #eee; text-align: left;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                                <strong style="color: #1a3644; font-size: 13px;">${escapeHTML(n.titulo)}</strong>
                                <span style="color: #999; font-size: 10px;">${escapeHTML(fechaTxt)}</span>
                            </div>
                            <div style="color: #555; font-size: 12px; line-height: 1.4;">${escapeHTML(n.mensaje)}</div>
                        </div>`;
                });
            }
        }
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
        }
    }
}

window.addEventListener("click", () => {
    const campana = document.getElementById("campana-dropdown");
    if (campana) campana.style.display = "none";
});

// ... (Aquí arriba está tu código existente de cargarCampana y toggleCampana) ...

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