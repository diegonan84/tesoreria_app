// ============================================================================
// fichadas.js - RECURSOS HUMANOS / CONTROL DE FICHADAS
// ============================================================================

function fiHoy() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// fecha_hora se guarda en hora local del reloj (sin zona): se muestra tal cual
function fiFormato(iso) {
    const [f, h = ""] = String(iso).split("T");
    const [a, m, d] = f.split("-");
    return `${d}/${m}/${a} ${h.slice(0, 5)}`;
}

function fiMensaje(texto) {
    document.getElementById("tabla-fichadas").innerHTML =
        `<tr><td colspan="5" style="text-align:center; color:#6b7c85; padding:20px;">${escapeHTML(texto)}</td></tr>`;
}

async function fiCargar() {
    const params = new URLSearchParams();
    const desde = document.getElementById("f-desde").value;
    const hasta = document.getElementById("f-hasta").value;
    const q = document.getElementById("f-q").value.trim();
    if (desde) params.set("desde", desde);
    if (hasta) params.set("hasta", hasta);
    if (q) params.set("q", q);

    fiMensaje("Cargando…");
    try {
        const res = await fetch(`/api/rrhh/marcaciones?${params}`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` },
        });
        if (!res.ok) {
            const j = await res.json().catch(() => ({}));
            fiMensaje(typeof j.detail === "string" ? j.detail : "No se pudieron cargar las fichadas.");
            return;
        }
        const filas = await res.json();
        if (!filas.length) { fiMensaje("No hay fichadas en el período."); return; }
        document.getElementById("tabla-fichadas").innerHTML = filas.map(m => `
            <tr>
                <td>${escapeHTML(fiFormato(m.fecha_hora))}</td>
                <td>${escapeHTML(m.identificador)}</td>
                <td>${escapeHTML(m.empleado || "Sin vincular")}</td>
                <td>${escapeHTML(m.tipo || "—")}</td>
                <td>${escapeHTML(m.origen)}</td>
            </tr>`).join("");
    } catch (e) {
        fiMensaje("No se pudo conectar con el servidor.");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("f-desde").value = fiHoy();
    document.getElementById("f-hasta").value = fiHoy();
    document.getElementById("f-buscar").addEventListener("click", fiCargar);
    document.getElementById("f-q").addEventListener("keydown", e => { if (e.key === "Enter") fiCargar(); });
    fiCargar();
});
