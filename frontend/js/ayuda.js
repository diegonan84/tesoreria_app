// ============================================================================
// ayuda.js - CENTRO DE AYUDA (manuales PDF)
// ============================================================================

let esAdminAyuda = false;

function decodificarTokenAyuda(token) {
    try {
        const payload = token.split('.')[1];
        return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    } catch (e) { return null; }
}

function inicializarPermisosAyuda() {
    const token = localStorage.getItem("token");
    const datos = decodificarTokenAyuda(token);
    const roles = (datos && datos.roles) || [];
    esAdminAyuda = roles.includes("Administrador");
    const btn = document.getElementById("btn-nuevo-manual");
    if (btn) btn.style.display = esAdminAyuda ? "inline-block" : "none";
}

function togglePanelManual() {
    const panel = document.getElementById("panel-subir-manual");
    if (!panel) return;
    panel.style.display = panel.style.display === "none" ? "block" : "none";
}

function formatearFechaManual(fecha) {
    if (!fecha) return "";
    const d = new Date(fecha);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function escapeHTMLManual(texto) {
    return String(texto || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

async function cargarManuales() {
    inicializarPermisosAyuda();
    const token = localStorage.getItem("token");
    if (!token) return;
    const lista = document.getElementById("lista-manuales");
    if (!lista) return;

    try {
        const res = await fetch(`${API_URL}/ayuda/manuales`, { headers: { "Authorization": `Bearer ${token}` } });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Error");

        if (!data.length) {
            lista.innerHTML = `<div class="card" style="grid-column:1/-1; text-align:center; color:#999;">Aún no hay manuales cargados.</div>`;
            return;
        }

        lista.innerHTML = data.map(m => `
            <div class="card" style="display:flex; flex-direction:column; border-top:4px solid #58a598; padding:20px;">
                <div style="background:#eef6f4; width:44px; height:44px; border-radius:8px; display:flex; align-items:center; justify-content:center; margin-bottom:12px;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3d8378" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line>
                    </svg>
                </div>
                <h3 style="margin:0 0 6px; color:#1a3644; font-size:16px;">${escapeHTMLManual(m.titulo)}</h3>
                <p style="margin:0 0 12px; color:#666; font-size:13px; flex-grow:1;">${escapeHTMLManual(m.descripcion) || "Manual de la plataforma."}</p>
                <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap;">
                    <a class="btn-action btn-approve" style="background:#1a3644; text-decoration:none;" href="${m.archivo_url}" target="_blank" download="${m.archivo_nombre}">📄 Abrir PDF</a>
                    ${esAdminAyuda ? `<button class="btn-action" style="background:#dc3545; color:white;" onclick="borrarManual(${m.id}, '${escapeHTMLManual(m.titulo)}')">Eliminar</button>` : ""}
                </div>
                <div style="font-size:11px; color:#aaa; margin-top:10px;">${m.archivo_nombre} · ${formatearFechaManual(m.fecha_subida)}</div>
            </div>
        `).join("");
    } catch (e) {
        lista.innerHTML = `<div class="card" style="grid-column:1/-1; text-align:center; color:#dc3545;">No se pudo cargar el centro de ayuda.</div>`;
    }
}

async function subirManual(event) {
    event.preventDefault();
    const file = document.getElementById("manual-archivo").files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        alert("Solo se permiten archivos PDF.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("titulo", document.getElementById("manual-titulo").value.trim());
    formData.append("descripcion", document.getElementById("manual-descripcion").value.trim());

    const btn = event.target.querySelector("button[type='submit']");
    btn.disabled = true;

    try {
        const res = await fetch(`${API_URL}/ayuda/manuales`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` },
            body: formData
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.detail || "Error al subir el manual");
            return;
        }
        document.getElementById("form-manual").reset();
        togglePanelManual();
        cargarManuales();
    } catch (e) {
        alert("Error de conexión al subir el manual.");
    } finally {
        btn.disabled = false;
    }
}

async function borrarManual(id, titulo) {
    if (!confirm(`¿Eliminar el manual "${titulo}"? También se borrará el archivo.`)) return;
    try {
        const res = await fetch(`${API_URL}/ayuda/manuales/${id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.detail || "Error al eliminar");
            return;
        }
        cargarManuales();
    } catch (e) {
        alert("Error de conexión al eliminar el manual.");
    }
}