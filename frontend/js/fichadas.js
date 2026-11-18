// ============================================================================
// fichadas.js - RECURSOS HUMANOS / CONTROL DE FICHADAS
// Importación del Excel "Asistencia biométrico" y alertas por persona y día
// ============================================================================

// analisis: el último Excel analizado (solo en pantalla, no se guarda)
const FI = { alerta: null, analisis: null };

function fiHeaders() {
    return { "Authorization": `Bearer ${localStorage.getItem("token")}` };
}

function fiToast(msg, error = false) {
    const t = document.getElementById("fi-toast");
    t.textContent = msg;
    t.classList.toggle("error", error);
    t.classList.add("visible");
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove("visible"), error ? 6000 : 3000);
}

async function fiError(res, defecto) {
    const j = await res.json().catch(() => ({}));
    return typeof j.detail === "string" ? j.detail : defecto;
}

// "2026-11-16" → "16/11/2026"
function fiFecha(iso) {
    if (!iso) return "—";
    const [a, m, d] = String(iso).slice(0, 10).split("-");
    return `${d}/${m}/${a}`;
}

// Fecha y hora guardadas en UTC → hora local
function fiFechaHora(iso) {
    if (!iso) return "—";
    const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z");
    return d.toLocaleString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fiMinutos(hhmm) {
    if (!hhmm) return null;
    const [h, m] = hhmm.split(":").map(Number);
    return h * 60 + m;
}

// Marca en rojo la hora real que se aleja más de 1 hora de la teórica
function fiHoraReal(real, teorica) {
    if (!real) return `<span class="fi-sub">—</span>`;
    const a = fiMinutos(real), b = fiMinutos(teorica);
    const lejos = a !== null && b !== null && Math.abs(a - b) > 60;
    return lejos ? `<span class="fi-dif" title="Teórico ${escapeHTML(teorica)}">${escapeHTML(real)}</span>` : escapeHTML(real);
}

function fiMensaje(texto) {
    document.getElementById("tabla-fichadas").innerHTML = `<tr><td colspan="8" class="fi-aviso">${escapeHTML(texto)}</td></tr>`;
}

function fiResumen(resumen) {
    document.getElementById("fi-resumen").innerHTML = resumen.map(r => `
        <button type="button" class="fi-chip ${FI.alerta === r.codigo ? "activo" : ""}" data-alerta="${r.codigo}">
            <span class="fi-alerta ${r.codigo}" style="margin:0">${escapeHTML(r.nombre)}</span><b>${r.cantidad}</b>
        </button>`).join("");
}

// Muestra el último análisis aplicando los filtros de pantalla (no consulta la base)
function fiPintar() {
    const r = FI.analisis;
    if (!r) return;
    const q = document.getElementById("f-q").value.trim().toLowerCase();
    const soloAlertas = document.getElementById("f-solo-alertas").checked;
    const filas = r.filas.filter(f =>
        (!q || `${f.nombre} ${f.cuil}`.toLowerCase().includes(q)) &&
        (!soloAlertas || f.alertas.length) &&
        (!FI.alerta || f.alertas.some(a => a.codigo === FI.alerta)));
    document.getElementById("fi-periodo").textContent =
        `"${r.archivo}" · ${fiFecha(r.desde)}${r.desde === r.hasta ? "" : " al " + fiFecha(r.hasta)} · ${r.filas.length} personas`;
    fiResumen(r.resumen);
    fiListadoAlertas(filas);
    if (!filas.length) { fiMensaje("No hay filas para mostrar con estos filtros."); return; }
    document.getElementById("tabla-fichadas").innerHTML = filas.map(f => `
        <tr>
            <td>${escapeHTML(f.nombre)}<br><span class="fi-sub">${escapeHTML(f.sector || "")}</span></td>
            <td>${fiFecha(f.fecha)}</td>
            <td class="c">${f.convocado ? "Sí" : "No"}</td>
            <td class="c">${escapeHTML(f.teorico_ingreso || "—")} a ${escapeHTML(f.teorico_salida || "—")}</td>
            <td class="c">${fiHoraReal(f.real_ingreso, f.teorico_ingreso)} a ${fiHoraReal(f.real_salida, f.teorico_salida)}</td>
            <td class="c">${escapeHTML(f.horas || "—")}</td>
            <td>${f.incidencia ? `<b>${escapeHTML(f.incidencia)}</b> ${escapeHTML(f.estado_incidencia || "")}<br>` : ""}
                <span class="fi-sub">${escapeHTML(f.estado || "")}</span></td>
            <td>${f.alertas.length
                ? f.alertas.map(a => `<span class="fi-alerta ${a.codigo}">${escapeHTML(a.texto)}</span>`).join("")
                : `<span class="fi-ok">${f.no_controla ? `No se controla (${escapeHTML(f.no_controla)})` : f.incidencia ? "Con incidencia" : "Sin alertas"}</span>`}</td>
        </tr>`).join("");
}

// Una fila por alerta: Usuario | Motivo de alerta | Detalle (con el color de cada tipo)
function fiListadoAlertas(filas) {
    const items = [];
    filas.forEach(f => f.alertas
        .filter(a => !FI.alerta || a.codigo === FI.alerta)
        .forEach(a => items.push({ f, a })));
    document.getElementById("fi-cant-alertas").textContent = items.length ? `(${items.length})` : "";
    document.getElementById("fi-alertas").innerHTML = items.length ? items.map(({ f, a }) => `
        <tr class="fi-fila-alerta ${a.codigo}">
            <td><b>${escapeHTML(f.nombre)}</b><br><span class="fi-sub">${escapeHTML(f.sector || "")} · ${fiFecha(f.fecha)}</span></td>
            <td><span class="fi-alerta ${a.codigo}">${escapeHTML(a.texto)}</span></td>
            <td>${escapeHTML(a.detalle || "")}</td>
        </tr>`).join("")
        : `<tr><td colspan="3" class="fi-aviso">No hay alertas para mostrar con estos filtros.</td></tr>`;
}

// Solo consulta: el servidor lee el Excel y devuelve las alertas, sin guardar nada
async function fiAnalizar(archivo) {
    if (!archivo) return;
    const caja = document.getElementById("fi-resultado");
    const boton = document.getElementById("fi-importar");
    boton.disabled = true;
    boton.textContent = "Analizando…";
    try {
        const datos = new FormData();
        datos.append("archivo", archivo);
        const res = await fetch("/api/rrhh/fichadas/analizar", { method: "POST", headers: fiHeaders(), body: datos });
        if (!res.ok) throw new Error(await fiError(res, "No se pudo analizar el archivo."));
        FI.analisis = await res.json();
        FI.alerta = null;
        // El mismo archivo queda listo para "Sumar al banco de horas"
        if (typeof BH !== "undefined") {
            BH.archivoFichadas = archivo;
            const b = document.getElementById("bh-sumar");
            if (b) { b.disabled = false; b.title = `Sumar lo que deben según "${archivo.name}"`; }
        }
        const sinUsuario = FI.analisis.filas.filter(f => !f.en_sistema);
        const avisos = FI.analisis.avisos;
        if (sinUsuario.length || avisos.length) {
            caja.innerHTML =
                (sinUsuario.length ? `<details><summary>${sinUsuario.length} persona(s) que no están como usuarios del sistema</summary><ul>${sinUsuario.map(f => `<li>${escapeHTML(f.nombre)} (${escapeHTML(f.cuil)})</li>`).join("")}</ul></details>` : "") +
                (avisos.length ? `<details><summary>Avisos (${avisos.length})</summary><ul>${avisos.map(x => `<li>${escapeHTML(x)}</li>`).join("")}</ul></details>` : "");
            caja.style.display = "block";
        } else {
            caja.style.display = "none";
        }
        fiPintar();
        const total = FI.analisis.resumen.reduce((n, r) => n + r.cantidad, 0);
        const sinControl = FI.analisis.sin_control ? `, ${FI.analisis.sin_control} sin control por Cód Reg` : "";
        fiToast(`Analizado: ${FI.analisis.filas.length} personas, ${total} alertas${sinControl} (no se guardó nada).`);
    } catch (e) {
        fiToast(e.message || "No se pudo conectar con el servidor.", true);
    }
    boton.disabled = false;
    boton.textContent = "Analizar Excel";
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("f-q").addEventListener("input", fiPintar);
    document.getElementById("f-solo-alertas").addEventListener("change", fiPintar);
    document.getElementById("fi-resumen").addEventListener("click", e => {
        const chip = e.target.closest("[data-alerta]");
        if (!chip) return;
        FI.alerta = FI.alerta === chip.dataset.alerta ? null : chip.dataset.alerta;
        fiPintar();
    });
    document.getElementById("fi-importar").addEventListener("click", () => document.getElementById("fi-archivo").click());
    document.getElementById("fi-archivo").addEventListener("change", e => {
        fiAnalizar(e.target.files[0]);
        e.target.value = "";  // así se puede volver a elegir el mismo archivo
    });
});
