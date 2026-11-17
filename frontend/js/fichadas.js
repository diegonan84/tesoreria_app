// ============================================================================
// fichadas.js - RECURSOS HUMANOS / CONTROL DE FICHADAS
// Importación del Excel "Asistencia biométrico" y alertas por persona y día
// ============================================================================

const FI = { alerta: null };

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

async function fiCargar() {
    const params = new URLSearchParams();
    const desde = document.getElementById("f-desde").value;
    const hasta = document.getElementById("f-hasta").value;
    const q = document.getElementById("f-q").value.trim();
    if (desde) params.set("desde", desde);
    if (desde) params.set("hasta", hasta || desde);
    if (q) params.set("q", q);
    if (document.getElementById("f-solo-alertas").checked) params.set("solo_alertas", "true");
    if (FI.alerta) params.set("alerta", FI.alerta);

    fiMensaje("Cargando…");
    try {
        const res = await fetch(`/api/rrhh/fichadas?${params}`, { headers: fiHeaders() });
        if (!res.ok) { fiMensaje(await fiError(res, "No se pudieron cargar las fichadas.")); return; }
        const r = await res.json();
        if (!r.desde) {
            fiMensaje("Todavía no hay fichadas importadas. Usá el botón Importar Excel.");
            document.getElementById("fi-periodo").textContent = "";
            fiResumen([]);
            return;
        }
        // Si no se eligió período, mostramos el que devolvió el servidor (el último día cargado)
        if (!desde) {
            document.getElementById("f-desde").value = String(r.desde).slice(0, 10);
            document.getElementById("f-hasta").value = String(r.hasta).slice(0, 10);
        }
        document.getElementById("fi-periodo").textContent =
            `Período: ${fiFecha(r.desde)}${r.desde === r.hasta ? "" : " al " + fiFecha(r.hasta)} · ${r.filas.length} fila(s)`;
        fiResumen(r.resumen);
        if (!r.filas.length) { fiMensaje("No hay filas para mostrar con estos filtros."); return; }
        document.getElementById("tabla-fichadas").innerHTML = r.filas.map(f => `
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
                    : `<span class="fi-ok">${f.incidencia ? "Con incidencia" : "Sin alertas"}</span>`}</td>
            </tr>`).join("");
    } catch (e) {
        fiMensaje("No se pudo conectar con el servidor.");
    }
}

async function fiCargarArchivos() {
    const cuerpo = document.getElementById("fi-archivos");
    try {
        const res = await fetch("/api/rrhh/fichadas/archivos", { headers: fiHeaders() });
        if (!res.ok) throw new Error(await fiError(res, "No se pudieron cargar los archivos."));
        const lista = await res.json();
        cuerpo.innerHTML = lista.length ? lista.map(a => `
            <tr>
                <td>${escapeHTML(a.nombre)}</td>
                <td>${fiFecha(a.desde)}${a.desde === a.hasta ? "" : " al " + fiFecha(a.hasta)}</td>
                <td>${a.filas}${a.filas_vigentes !== a.filas ? ` <span class="fi-sub">(${a.filas_vigentes} vigentes)</span>` : ""}</td>
                <td>${escapeHTML(a.subido_por || "—")}</td>
                <td>${fiFechaHora(a.fecha_subida)}</td>
                <td><button type="button" data-borrar="${a.id}" data-nombre="${escapeHTML(a.nombre)}" title="Quitar esta importación">🗑</button></td>
            </tr>`).join("") : `<tr><td colspan="6" class="fi-aviso">Todavía no se importó ningún archivo.</td></tr>`;
    } catch (e) {
        cuerpo.innerHTML = `<tr><td colspan="6" class="fi-aviso">${escapeHTML(e.message)}</td></tr>`;
    }
}

async function fiEnviar(archivo, simular) {
    const datos = new FormData();
    datos.append("archivo", archivo);
    const res = await fetch(`/api/rrhh/fichadas/importar?simular=${simular}`, { method: "POST", headers: fiHeaders(), body: datos });
    if (!res.ok) {
        const err = new Error(await fiError(res, "No se pudo importar el archivo."));
        err.duplicado = res.status === 409;
        throw err;
    }
    return res.json();
}

// Paso 1: revisar el archivo (no graba). Paso 2: "Importar".
async function fiImportar(archivo) {
    if (!archivo) return;
    const caja = document.getElementById("fi-resultado");
    const boton = document.getElementById("fi-importar");
    boton.disabled = true;
    try {
        const r = await fiEnviar(archivo, true);
        const rango = fiFecha(r.desde) + (r.desde === r.hasta ? "" : " al " + fiFecha(r.hasta));
        caja.innerHTML = `<b>Revisión de "${escapeHTML(archivo.name)}"</b> (todavía no se guardó nada)<br>
            ${r.filas} filas del ${rango} · ${r.nuevas} nuevas · ${r.actualizadas} cambian · ${r.iguales} iguales a lo ya cargado.
            ${r.ya_cargado ? `<br><b>Ojo:</b> ese período ya tenía fichadas cargadas de otro archivo; las filas que cambian se reemplazan.` : ""}
            <br>Alertas: ${r.alertas.length ? r.alertas.map(a => `<span class="fi-alerta ${a.codigo}">${escapeHTML(a.nombre)}: ${a.cantidad}</span>`).join(" ") : "ninguna"}
            ${r.sin_usuario.length ? `<details><summary>${r.sin_usuario.length} persona(s) sin usuario en el sistema (se cargan igual)</summary><ul>${r.sin_usuario.map(x => `<li>${escapeHTML(x)}</li>`).join("")}</ul></details>` : ""}
            ${r.avisos.length ? `<details><summary>Avisos (${r.avisos.length})</summary><ul>${r.avisos.map(x => `<li>${escapeHTML(x)}</li>`).join("")}</ul></details>` : ""}
            <div class="fi-botones">
                ${r.nuevas || r.actualizadas ? `<button type="button" id="fi-aplicar">Importar</button>` : ""}
                <button type="button" id="fi-cancelar">${r.nuevas || r.actualizadas ? "Cancelar" : "Cerrar"}</button>
            </div>`;
        caja.style.display = "block";
        document.getElementById("fi-cancelar").onclick = () => { caja.style.display = "none"; };
        const aplicar = document.getElementById("fi-aplicar");
        if (aplicar) aplicar.onclick = async () => {
            aplicar.disabled = true;
            try {
                const f = await fiEnviar(archivo, false);
                caja.style.display = "none";
                fiToast(`Importado: ${f.nuevas} nuevas, ${f.actualizadas} actualizadas.`);
                document.getElementById("f-desde").value = String(f.desde).slice(0, 10);
                document.getElementById("f-hasta").value = String(f.hasta).slice(0, 10);
                await Promise.all([fiCargar(), fiCargarArchivos()]);
            } catch (e) {
                aplicar.disabled = false;
                fiToast(e.message, true);
            }
        };
    } catch (e) {
        if (e.duplicado) {
            caja.innerHTML = `<b class="fi-error">Archivo repetido.</b> ${escapeHTML(e.message)}
                <div class="fi-botones"><button type="button" id="fi-cancelar">Cerrar</button></div>`;
            caja.style.display = "block";
            document.getElementById("fi-cancelar").onclick = () => { caja.style.display = "none"; };
        } else {
            fiToast(e.message || "No se pudo conectar con el servidor.", true);
        }
    }
    boton.disabled = false;
}

async function fiBorrarArchivo(id, nombre) {
    if (!confirm(`¿Quitar la importación "${nombre}"? Se borran las fichadas que vienen de ese archivo.`)) return;
    try {
        const res = await fetch(`/api/rrhh/fichadas/archivos/${id}`, { method: "DELETE", headers: fiHeaders() });
        if (!res.ok) throw new Error(await fiError(res, "No se pudo quitar el archivo."));
        const r = await res.json();
        fiToast(`Se quitó el archivo (${r.filas_borradas} filas).`);
        await Promise.all([fiCargar(), fiCargarArchivos()]);
    } catch (e) {
        fiToast(e.message, true);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("f-buscar").addEventListener("click", fiCargar);
    document.getElementById("f-q").addEventListener("keydown", e => { if (e.key === "Enter") fiCargar(); });
    document.getElementById("f-solo-alertas").addEventListener("change", fiCargar);
    document.getElementById("fi-resumen").addEventListener("click", e => {
        const chip = e.target.closest("[data-alerta]");
        if (!chip) return;
        FI.alerta = FI.alerta === chip.dataset.alerta ? null : chip.dataset.alerta;
        fiCargar();
    });
    document.getElementById("fi-importar").addEventListener("click", () => document.getElementById("fi-archivo").click());
    document.getElementById("fi-archivo").addEventListener("change", e => {
        fiImportar(e.target.files[0]);
        e.target.value = "";
    });
    document.getElementById("fi-archivos").addEventListener("click", e => {
        const b = e.target.closest("button[data-borrar]");
        if (b) fiBorrarArchivo(b.dataset.borrar, b.dataset.nombre);
    });
    fiCargar();
    fiCargarArchivos();
});
