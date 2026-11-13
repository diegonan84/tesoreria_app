// ============================================================================
// home_office.js - RECURSOS HUMANOS / TABLERO DE HOME OFFICE
// ============================================================================

// guardado: lo que está en la base; usuarios[].dias: lo que se ve (con cambios sin guardar)
const HO = { usuarios: [], guardado: {} };
const HO_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"];

function hoHeaders(json = false) {
    const h = { "Authorization": `Bearer ${localStorage.getItem("token")}` };
    if (json) h["Content-Type"] = "application/json";
    return h;
}

function hoToast(msg, error = false) {
    const t = document.getElementById("ho-toast");
    t.textContent = msg;
    t.classList.toggle("error", error);
    t.classList.add("visible");
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove("visible"), 2500);
}

async function hoError(res, defecto) {
    const j = await res.json().catch(() => ({}));
    return typeof j.detail === "string" ? j.detail : defecto;
}

function hoNormalizar(txt) {
    return String(txt || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

const HO_TIPOS = { HOME: "Home", CONVOCADO: "Convocado", SIN_HORARIO: "—" };
const HO_SIGUIENTE = { HOME: "CONVOCADO", CONVOCADO: "HOME" };

function hoFiltrados() {
    const q = hoNormalizar(document.getElementById("ho-q").value.trim());
    const sector = document.getElementById("ho-sector").value;
    const area = document.getElementById("ho-area").value;
    const mostrar = document.getElementById("ho-solo").value;
    return HO.usuarios.filter(u =>
        (!q || hoNormalizar(`${u.apellido} ${u.nombre} ${u.cuil} ${u.cod_reg || ""}`).includes(q)) &&
        (!area || (u.area || "Sin área") === area) &&
        (!sector || (u.sector || "Sin sector") === sector) &&
        (!mostrar || (mostrar === "sinhome" ? !u.dias.includes("HOME") : u.dias.includes(mostrar))));
}

function hoPendientes() {
    return HO.usuarios.filter(u => u.dias.some((t, d) => t !== HO.guardado[u.usuario_id][d]));
}

function hoBarra() {
    const n = hoPendientes().length;
    document.getElementById("ho-barra").classList.toggle("con-cambios", n > 0);
    document.getElementById("ho-estado").textContent = n
        ? `Hay cambios sin guardar en ${n} persona${n > 1 ? "s" : ""}.`
        : "Sin cambios pendientes.";
    document.getElementById("ho-guardar").disabled = !n;
    document.getElementById("ho-descartar").disabled = !n;
}

function hoBoton(u, d) {
    const tipo = u.dias[d] || "CONVOCADO";
    const franja = (u.franjas || [])[d];
    if (tipo === "SIN_HORARIO") {
        return `<span class="ho-marca sin_horario" title="${HO_DIAS[d]}: sin horario en la planilla">—</span>`;
    }
    const pendiente = tipo !== HO.guardado[u.usuario_id][d] ? " pendiente" : "";
    return `<button type="button" class="ho-marca ${tipo.toLowerCase()}${pendiente}" data-usuario="${u.usuario_id}" data-dia="${d}"
                title="${HO_DIAS[d]}: clic para cambiar${pendiente ? " (sin guardar)" : ""}">${HO_TIPOS[tipo]}${franja ? `<small>${escapeHTML(franja)}</small>` : ""}</button>`;
}

function hoPintar() {
    const lista = hoFiltrados();
    const cuerpo = document.getElementById("ho-cuerpo");
    if (!lista.length) {
        cuerpo.innerHTML = `<tr><td colspan="8" class="ho-aviso">No hay personas para mostrar.</td></tr>`;
    } else {
        cuerpo.innerHTML = lista.map(u => `
            <tr class="${u.sin_control ? "ho-sin-control" : ""}">
                <td>${escapeHTML(u.apellido)}, ${escapeHTML(u.nombre)}
                    ${u.cod_reg ? `<span class="ho-sub"> · Cód Reg ${escapeHTML(u.cod_reg)}</span>` : ""}
                    ${u.observacion ? `<br><span class="ho-obs">${escapeHTML(u.observacion)}</span>` : ""}
                    ${u.sin_control ? `<br><span class="ho-sc-badge" title="No se controla Home / Convocado">⏸ ${escapeHTML(u.sin_control)}</span>` : ""}</td>
                <td class="ho-sub">${escapeHTML(u.cuil)}</td>
                <td class="ho-sub">${escapeHTML(u.area || "Sin área")}${u.subsector ? `<br>${escapeHTML(u.subsector)}` : ""}</td>
                ${HO_DIAS.map((_, d) => `<td class="dia">${hoBoton(u, d)}</td>`).join("")}
            </tr>`).join("");
    }

    // Totales del grupo filtrado por día
    const contar = tipo => HO_DIAS.map((_, d) => lista.filter(u => u.dias[d] === tipo).length);
    const fila = (titulo, valores) => `<tr><td colspan="3">${titulo}</td>${valores.map(n => `<td class="dia">${n}</td>`).join("")}</tr>`;
    document.getElementById("ho-pie").innerHTML =
        fila(`Home (de ${lista.length} personas)`, contar("HOME")) + fila("Convocados", contar("CONVOCADO"));
    hoBarra();
}

// El clic solo cambia la pantalla; se guarda con el botón "Guardar cambios"
function hoCambiar(boton) {
    const u = HO.usuarios.find(x => x.usuario_id === Number(boton.dataset.usuario));
    const d = Number(boton.dataset.dia);
    if (u.dias[d] === "SIN_HORARIO") return;
    u.dias[d] = HO_SIGUIENTE[u.dias[d] || "CONVOCADO"];
    hoPintar();
}

async function hoGuardar() {
    const cambios = hoPendientes().map(u => ({ usuario_id: u.usuario_id, dias: u.dias }));
    if (!cambios.length) return;
    const boton = document.getElementById("ho-guardar");
    boton.disabled = true;
    boton.textContent = "Guardando…";
    try {
        const res = await fetch("/api/rrhh/home-office", {
            method: "PUT", headers: hoHeaders(true), body: JSON.stringify({ cambios }),
        });
        if (!res.ok) throw new Error(await hoError(res, "No se pudo guardar."));
        cambios.forEach(c => { HO.guardado[c.usuario_id] = [...c.dias]; });
        hoToast(`Guardado: ${cambios.length} persona${cambios.length > 1 ? "s" : ""}.`);
    } catch (e) {
        hoToast(e.message || "No se pudo conectar con el servidor. Los cambios siguen sin guardar.", true);
    }
    boton.textContent = "Guardar cambios";
    hoPintar();
}

function hoDescartar() {
    if (!confirm("¿Descartar los cambios sin guardar?")) return;
    HO.usuarios.forEach(u => { u.dias = [...HO.guardado[u.usuario_id]]; });
    hoPintar();
}

async function hoCargar() {
    const aviso = msg => {
        document.getElementById("ho-cuerpo").innerHTML = `<tr><td colspan="8" class="ho-aviso">${escapeHTML(msg)}</td></tr>`;
    };
    try {
        const res = await fetch("/api/rrhh/home-office", { headers: hoHeaders() });
        if (!res.ok) { aviso(await hoError(res, "No se pudo cargar el tablero.")); return; }
        HO.usuarios = await res.json();
        HO.guardado = Object.fromEntries(HO.usuarios.map(u => [u.usuario_id, [...u.dias]]));
        const areas = [...new Set(HO.usuarios.map(u => u.area || "Sin área"))];
        const selArea = document.getElementById("ho-area");
        const areaElegida = selArea.value;
        selArea.innerHTML = `<option value="">Todas</option>` + areas.map(a => `<option>${escapeHTML(a)}</option>`).join("");
        selArea.value = areaElegida;
        const sectores = [...new Set(HO.usuarios.map(u => u.sector || "Sin sector"))].sort();
        document.getElementById("ho-sector").innerHTML = `<option value="">Todos</option>` +
            sectores.map(s => `<option>${escapeHTML(s)}</option>`).join("");
        const sel = document.getElementById("sc-usuario");
        const elegido = sel.value;
        sel.innerHTML = `<option value="">Todo el personal</option>` + HO.usuarios.map(u =>
            `<option value="${u.usuario_id}">${escapeHTML(u.apellido)}, ${escapeHTML(u.nombre)}</option>`).join("");
        sel.value = elegido;
        hoPintar();
    } catch (e) {
        aviso("No se pudo conectar con el servidor.");
    }
}

async function hoExportar(boton) {
    if (hoPendientes().length) hoToast("Ojo: el Excel sale con lo guardado; tenés cambios sin guardar.", true);
    boton.disabled = true;
    try {
        const res = await fetch("/api/rrhh/horarios/exportar", { headers: hoHeaders() });
        if (!res.ok) throw new Error(await hoError(res, "No se pudo exportar."));
        const nombre = (res.headers.get("Content-Disposition") || "").match(/filename=([^;]+)/);
        const url = URL.createObjectURL(await res.blob());
        const a = Object.assign(document.createElement("a"), { href: url, download: nombre ? nombre[1] : "Home_Office.xlsx" });
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
    } catch (e) {
        hoToast(e.message || "No se pudo conectar con el servidor.", true);
    }
    boton.disabled = false;
}

async function hoEnviarExcel(archivo, simular, vinculos = {}) {
    const datos = new FormData();
    datos.append("archivo", archivo);
    datos.append("vinculos", JSON.stringify(vinculos));
    const res = await fetch(`/api/rrhh/horarios/importar?simular=${simular}`, { method: "POST", headers: hoHeaders(), body: datos });
    if (!res.ok) throw new Error(await hoError(res, "No se pudo leer el Excel."));
    return res.json();
}

function hoTextoDia(d) {
    if (d.tipo === "SIN_HORARIO") return "—";
    return `${HO_TIPOS[d.tipo]}${d.texto ? ` ${d.texto}` : ""}`;
}

function hoTablaComparacion(diferencias) {
    if (!diferencias.length) return "";
    const celda = (antes, despues) => {
        const igual = antes.tipo === despues.tipo && (antes.texto || "") === (despues.texto || "");
        return igual
            ? `<td class="ho-igual">${escapeHTML(hoTextoDia(despues))}</td>`
            : `<td class="ho-cambio ${despues.tipo.toLowerCase()}" title="Antes: ${escapeHTML(hoTextoDia(antes))}">${escapeHTML(hoTextoDia(despues))}</td>`;
    };
    return `<details open><summary>Cambios por persona (${diferencias.length})</summary><div class="ho-comparacion"><table>
        <thead><tr><th>Persona</th>${HO_DIAS.map(d => `<th>${d.slice(0, 3)}</th>`).join("")}</tr></thead>
        <tbody>${diferencias.map(x => `<tr>
            <td>${escapeHTML(x.nombre)} <span class="ho-sub">${escapeHTML(x.hoja)}</span></td>
            ${x.despues.map((t, d) => celda(x.antes[d], t)).join("")}</tr>`).join("")}</tbody>
    </table></div></details>`;
}

function hoListaAvisos(avisos) {
    return avisos.length ? `<details><summary>Avisos (${avisos.length})</summary><ul>${avisos.map(p => `<li>${escapeHTML(p)}</li>`).join("")}</ul></details>` : "";
}

function hoNoEncontrados(lista) {
    if (!lista.length) return "";
    const opcionesTodos = HO.usuarios.map(u => `<option value="${u.usuario_id}">${escapeHTML(u.apellido)}, ${escapeHTML(u.nombre)}</option>`).join("");
    return `<details open><summary>Sin vincular (${lista.length}): elegí a quién corresponde o dejalo sin importar</summary>
        <table class="ho-sc-lista ho-ne"><tbody>${lista.map(x => `<tr>
            <td>${escapeHTML(x.nombre)} <span class="ho-sub">${escapeHTML(x.hoja)}, fila ${x.fila}</span></td>
            <td><select data-clave="${escapeHTML(x.clave)}">
                <option value="">— No importar —</option>
                ${x.candidatos.length ? `<optgroup label="Sugeridos">${x.candidatos.map(c => `<option value="${c.id}">${escapeHTML(c.nombre)}</option>`).join("")}</optgroup>` : ""}
                <optgroup label="Todos los usuarios">${opcionesTodos}</optgroup>
            </select></td></tr>`).join("")}</tbody></table></details>`;
}

function hoColores(colores) {
    if (!colores.length) return "";
    return `<details><summary>Colores de nombre encontrados (${colores.length}), para definir el Cód Reg</summary>
        <table class="ho-sc-lista"><tbody>${colores.map(c => `<tr>
            <td><span class="ho-color" style="background:#${escapeHTML(c.color)}"></span>#${escapeHTML(c.color)}</td>
            <td>${c.cantidad} persona(s)</td><td class="ho-sub">${c.ejemplos.map(escapeHTML).join("; ")}</td></tr>`).join("")}</tbody></table></details>`;
}

function hoVinculosElegidos() {
    const v = {};
    document.querySelectorAll("#ho-resultado select[data-clave]").forEach(s => { if (s.value) v[s.dataset.clave] = Number(s.value); });
    return v;
}

// Paso 1: comparar la planilla con lo guardado (no graba nada). Paso 2: "Aplicar importación".
async function hoImportar(archivo) {
    if (!archivo) return;
    if (hoPendientes().length && !confirm("Tenés cambios sin guardar en pantalla: la importación los va a reemplazar. ¿Seguir?")) return;
    const caja = document.getElementById("ho-resultado");
    const boton = document.getElementById("ho-importar");
    boton.disabled = true;
    try {
        const r = await hoEnviarExcel(archivo, true);
        caja.innerHTML = `<b>Comparación de "${escapeHTML(archivo.name)}" con lo guardado</b> (todavía no se guardó nada):<br>
            ${r.personas} personas en ${r.hojas.length} hojas · ${r.vinculados} vinculadas · ${r.actualizados} con cambios ·
            ${r.sin_cambios} iguales · ${r.no_encontrados.length} sin vincular.` +
            hoNoEncontrados(r.no_encontrados) + hoTablaComparacion(r.diferencias) + hoListaAvisos(r.avisos) + hoColores(r.colores) +
            `<div class="ho-resultado-acciones">
                <button type="button" id="ho-aplicar">Aplicar importación</button>
                <button type="button" id="ho-cancelar">Cancelar</button>
            </div>`;
        caja.style.display = "block";
        caja.scrollIntoView({ behavior: "smooth", block: "start" });
        document.getElementById("ho-cancelar").onclick = () => { caja.style.display = "none"; };
        const aplicar = document.getElementById("ho-aplicar");
        aplicar.onclick = async () => {
            aplicar.disabled = true;
            try {
                const f = await hoEnviarExcel(archivo, false, hoVinculosElegidos());
                caja.innerHTML = `<b>Importación aplicada:</b> ${f.vinculados} personas cargadas, ${f.actualizados} con cambios, ` +
                    `${f.no_encontrados.length} sin vincular (no se importaron).` +
                    hoListaAvisos(f.avisos) +
                    `<div class="ho-resultado-acciones"><button type="button" id="ho-cerrar">Cerrar</button></div>`;
                document.getElementById("ho-cerrar").onclick = () => { caja.style.display = "none"; };
                await hoCargar();
            } catch (e) {
                aplicar.disabled = false;
                hoToast(e.message || "No se pudo conectar con el servidor.", true);
            }
        };
    } catch (e) {
        hoToast(e.message || "No se pudo conectar con el servidor.", true);
    }
    boton.disabled = false;
}

// ---------------------------------------------------------------------------
// Períodos sin control
// ---------------------------------------------------------------------------
function scFecha(iso) {
    const [a, m, d] = String(iso).split("-");
    return `${d}/${m}/${a}`;
}

async function scCargar() {
    const cuerpo = document.getElementById("sc-cuerpo");
    try {
        const res = await fetch("/api/rrhh/sin-control", { headers: hoHeaders() });
        if (!res.ok) throw new Error(await hoError(res, "No se pudieron cargar los períodos."));
        const lista = await res.json();
        const vigentes = lista.filter(p => p.vigente).length;
        document.getElementById("ho-sc-cuenta").textContent = lista.length
            ? `(${vigentes} vigente${vigentes === 1 ? "" : "s"}, ${lista.length - vigentes} a futuro)` : "";
        cuerpo.innerHTML = lista.length ? lista.map(p => `
            <tr>
                <td>${escapeHTML(p.persona)}${p.vigente ? ` <span class="ho-sc-badge">vigente</span>` : ""}</td>
                <td>${scFecha(p.desde)}</td><td>${scFecha(p.hasta)}</td>
                <td>${escapeHTML(p.motivo || "—")}</td>
                <td><button type="button" data-periodo="${p.id}" title="Quitar período">🗑</button></td>
            </tr>`).join("")
            : `<tr><td colspan="5" class="ho-aviso">No hay períodos vigentes ni a futuro.</td></tr>`;
    } catch (e) {
        cuerpo.innerHTML = `<tr><td colspan="5" class="ho-aviso">${escapeHTML(e.message)}</td></tr>`;
    }
}

async function scAgregar() {
    const usuario = document.getElementById("sc-usuario").value;
    const desde = document.getElementById("sc-desde").value;
    const hasta = document.getElementById("sc-hasta").value || desde;
    if (!desde) { hoToast("Elegí la fecha desde.", true); return; }
    try {
        const res = await fetch("/api/rrhh/sin-control", {
            method: "POST", headers: hoHeaders(true),
            body: JSON.stringify({ usuario_id: usuario ? Number(usuario) : null, desde, hasta,
                                   motivo: document.getElementById("sc-motivo").value }),
        });
        if (!res.ok) throw new Error(await hoError(res, "No se pudo guardar el período."));
        document.getElementById("sc-motivo").value = "";
        hoToast("Período agregado.");
        await scRefrescar();
    } catch (e) {
        hoToast(e.message, true);
    }
}

async function scBorrar(id) {
    if (!confirm("¿Quitar este período sin control?")) return;
    try {
        const res = await fetch(`/api/rrhh/sin-control/${id}`, { method: "DELETE", headers: hoHeaders() });
        if (!res.ok) throw new Error(await hoError(res, "No se pudo quitar el período."));
        await scRefrescar();
    } catch (e) {
        hoToast(e.message, true);
    }
}

// Recarga la lista de períodos y la marca "sin control" de cada persona, sin perder cambios pendientes
async function scRefrescar() {
    await scCargar();
    const res = await fetch("/api/rrhh/home-office", { headers: hoHeaders() }).catch(() => null);
    if (!res || !res.ok) return;
    const nuevos = Object.fromEntries((await res.json()).map(u => [u.usuario_id, u.sin_control]));
    HO.usuarios.forEach(u => { u.sin_control = nuevos[u.usuario_id] || null; });
    hoPintar();
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("sc-agregar").addEventListener("click", scAgregar);
    document.getElementById("sc-cuerpo").addEventListener("click", e => {
        const b = e.target.closest("button[data-periodo]");
        if (b) scBorrar(b.dataset.periodo);
    });
    scCargar();
    document.getElementById("ho-exportar").addEventListener("click", e => hoExportar(e.currentTarget));
    document.getElementById("ho-importar").addEventListener("click", () => document.getElementById("ho-archivo").click());
    document.getElementById("ho-archivo").addEventListener("change", e => {
        hoImportar(e.target.files[0]);
        e.target.value = "";
    });
    document.getElementById("ho-q").addEventListener("input", hoPintar);
    document.getElementById("ho-sector").addEventListener("change", hoPintar);
    document.getElementById("ho-area").addEventListener("change", hoPintar);
    document.getElementById("ho-solo").addEventListener("change", hoPintar);
    document.getElementById("ho-guardar").addEventListener("click", hoGuardar);
    document.getElementById("ho-descartar").addEventListener("click", hoDescartar);
    // Aviso del navegador si se sale de la página con cambios sin guardar
    window.addEventListener("beforeunload", e => {
        if (hoPendientes().length) { e.preventDefault(); e.returnValue = ""; }
    });
    document.getElementById("ho-cuerpo").addEventListener("click", e => {
        const boton = e.target.closest("button.ho-marca");
        if (boton) hoCambiar(boton);
    });
    hoCargar();
});
