// ============================================================================
// banco_horas.js - RECURSOS HUMANOS / BANCO DE HORAS
// Saldo de horas por persona (por CUIL): saldo inicial importado + deudas de las
// fichadas sumadas a mano + ajustes. Negativo = horas que debe.
// ============================================================================

const BH = { lista: [], archivoFichadas: null };

function bhHeaders(json = false) {
    const h = { "Authorization": `Bearer ${localStorage.getItem("token")}` };
    if (json) h["Content-Type"] = "application/json";
    return h;
}

async function bhError(res, defecto) {
    const j = await res.json().catch(() => ({}));
    return typeof j.detail === "string" ? j.detail : defecto;
}

function bhCaja(html) {
    const caja = document.getElementById("bh-resultado");
    caja.innerHTML = html;
    caja.style.display = html ? "block" : "none";
    return caja;
}

function bhSaldo(x) {
    const clase = x.minutos < 0 ? "bh-debe" : x.minutos > 0 ? "bh-favor" : "fi-sub";
    return `<span class="${clase}">${escapeHTML(x.saldo_texto)}</span> <span class="fi-sub">(${escapeHTML(x.saldo)})</span>`;
}

async function bhCargar() {
    const cuerpo = document.getElementById("bh-cuerpo");
    try {
        const res = await fetch("/api/rrhh/banco-horas", { headers: bhHeaders() });
        if (!res.ok) throw new Error(await bhError(res, "No se pudo cargar el banco de horas."));
        BH.lista = await res.json();
        bhPintar();
    } catch (e) {
        cuerpo.innerHTML = `<tr><td colspan="4" class="fi-aviso">${escapeHTML(e.message)}</td></tr>`;
    }
}

function bhPintar() {
    const q = document.getElementById("bh-q").value.trim().toLowerCase();
    const lista = BH.lista.filter(x => !q || `${x.nombre} ${x.cuil}`.toLowerCase().includes(q));
    const deben = BH.lista.filter(x => x.minutos < 0).length;
    document.getElementById("bh-cuenta").textContent = BH.lista.length ? `(${deben} con horas adeudadas)` : "";
    document.getElementById("bh-cuerpo").innerHTML = lista.length ? lista.map(x => `
        <tr>
            <td><b>${escapeHTML(x.nombre)}</b><br><span class="fi-sub">${escapeHTML(x.sector || "")} · CUIL ${escapeHTML(x.cuil)}</span></td>
            <td>${bhSaldo(x)}</td>
            <td class="c">${x.movimientos}</td>
            <td class="c"><button type="button" data-cuil="${escapeHTML(x.cuil)}">Ver / ajustar</button></td>
        </tr>`).join("")
        : `<tr><td colspan="4" class="fi-aviso">${BH.lista.length ? "No hay coincidencias." : "Todavía no hay saldos. Importá el saldo inicial o sumá un Excel de fichadas."}</td></tr>`;
}

// ---- Saldo inicial (Excel con CUIL y horas) ----
async function bhEnviarSaldo(archivo, simular) {
    const datos = new FormData();
    datos.append("archivo", archivo);
    const res = await fetch(`/api/rrhh/banco-horas/saldo-inicial?simular=${simular}`, { method: "POST", headers: bhHeaders(), body: datos });
    if (!res.ok) throw new Error(await bhError(res, "No se pudo leer el archivo."));
    return res.json();
}

async function bhSaldoInicial(archivo) {
    if (!archivo) return;
    try {
        const r = await bhEnviarSaldo(archivo, true);
        const caja = bhCaja(`<b>Saldo inicial desde "${escapeHTML(archivo.name)}"</b> (todavía no se guardó nada)<br>
            Columna de horas: <b>${escapeHTML(r.columna)}</b> (${r.modo === "DEUDA" ? "horas que debe" : "saldo con signo: negativo = debe"}).<br>
            ${r.personas} personas · ${r.nuevos} nuevas · ${r.cambiados} cambian · ${r.iguales} iguales · total ${escapeHTML(r.total)} h.
            ${r.sin_usuario.length ? `<details><summary>${r.sin_usuario.length} CUIL que no están como usuarios (se cargan igual)</summary><ul>${r.sin_usuario.map(x => `<li>${escapeHTML(x)}</li>`).join("")}</ul></details>` : ""}
            ${r.avisos.length ? `<details><summary>Avisos (${r.avisos.length})</summary><ul>${r.avisos.map(x => `<li>${escapeHTML(x)}</li>`).join("")}</ul></details>` : ""}
            <div class="fi-botones">
                ${r.nuevos || r.cambiados ? `<button type="button" id="bh-aplicar">Guardar saldo inicial</button>` : ""}
                <button type="button" id="bh-cancelar">${r.nuevos || r.cambiados ? "Cancelar" : "Cerrar"}</button>
            </div>`);
        caja.querySelector("#bh-cancelar").onclick = () => bhCaja("");
        const aplicar = caja.querySelector("#bh-aplicar");
        if (aplicar) aplicar.onclick = async () => {
            aplicar.disabled = true;
            try {
                const f = await bhEnviarSaldo(archivo, false);
                bhCaja("");
                fiToast(`Saldo inicial guardado: ${f.nuevos} nuevos, ${f.cambiados} cambiados.`);
                await bhCargar();
            } catch (e) { aplicar.disabled = false; fiToast(e.message, true); }
        };
    } catch (e) {
        fiToast(e.message, true);
    }
}

// ---- Sumar al banco lo que deben según el último Excel de fichadas analizado ----
async function bhEnviarFichadas(simular) {
    const datos = new FormData();
    datos.append("archivo", BH.archivoFichadas);
    const res = await fetch(`/api/rrhh/banco-horas/sumar-fichadas?simular=${simular}`, { method: "POST", headers: bhHeaders(), body: datos });
    if (!res.ok) throw new Error(await bhError(res, "No se pudo sumar al banco."));
    return res.json();
}

async function bhSumarFichadas() {
    if (!BH.archivoFichadas) { fiToast("Primero analizá un Excel de fichadas.", true); return; }
    try {
        const r = await bhEnviarFichadas(true);
        const rango = fiFecha(r.desde) + (r.desde === r.hasta ? "" : " al " + fiFecha(r.hasta));
        const caja = bhCaja(`<b>Sumar al banco de horas las fichadas del ${rango}</b> (todavía no se guardó nada)<br>
            ${r.sumados ? `Se suman ${r.sumados} deuda(s), en total ${escapeHTML(r.total)}.` : "No hay deudas nuevas para sumar."}
            ${r.ya_sumados ? `<br>${r.ya_sumados} ya se habían sumado antes para esa fecha y no se vuelven a sumar.` : ""}
            ${r.detalle.length ? `<details><summary>Ver detalle</summary><ul>${r.detalle.map(x => `<li>${escapeHTML(x.nombre)}: debe ${escapeHTML(x.debe)}</li>`).join("")}</ul></details>` : ""}
            <div class="fi-botones">
                ${r.sumados ? `<button type="button" id="bh-aplicar">Sumar al banco</button>` : ""}
                <button type="button" id="bh-cancelar">${r.sumados ? "Cancelar" : "Cerrar"}</button>
            </div>`);
        caja.scrollIntoView({ behavior: "smooth", block: "start" });
        caja.querySelector("#bh-cancelar").onclick = () => bhCaja("");
        const aplicar = caja.querySelector("#bh-aplicar");
        if (aplicar) aplicar.onclick = async () => {
            aplicar.disabled = true;
            try {
                const f = await bhEnviarFichadas(false);
                bhCaja("");
                fiToast(`Se sumaron ${f.sumados} deuda(s) al banco de horas.`);
                await bhCargar();
            } catch (e) { aplicar.disabled = false; fiToast(e.message, true); }
        };
    } catch (e) {
        fiToast(e.message, true);
    }
}

// ---- Detalle de una persona y ajuste manual ----
const BH_TIPOS = { SALDO_INICIAL: "Saldo inicial", FICHADA: "Fichada", AJUSTE: "Ajuste" };

async function bhDetalle(cuil) {
    try {
        const res = await fetch(`/api/rrhh/banco-horas/${encodeURIComponent(cuil)}`, { headers: bhHeaders() });
        if (!res.ok) throw new Error(await bhError(res, "No se pudo cargar el detalle."));
        const d = await res.json();
        const x = BH.lista.find(p => p.cuil === d.cuil) || { nombre: d.cuil };
        const caja = bhCaja(`<b>${escapeHTML(x.nombre)}</b> · ${bhSaldo(d)}
            <table class="fi-tabla" style="margin-top:8px;"><thead><tr><th>Fecha</th><th>Tipo</th><th class="c">Horas</th><th>Detalle</th><th>Cargado por</th></tr></thead>
            <tbody>${d.movimientos.map(m => `<tr>
                <td>${fiFecha(m.fecha)}</td><td>${escapeHTML(BH_TIPOS[m.tipo] || m.tipo)}</td>
                <td class="c ${m.minutos < 0 ? "bh-debe" : "bh-favor"}">${escapeHTML(m.horas)}</td>
                <td>${escapeHTML(m.detalle || "")}${m.archivo ? `<br><span class="fi-sub">${escapeHTML(m.archivo)}</span>` : ""}</td>
                <td class="fi-sub">${escapeHTML(m.cargado_por || "")}</td></tr>`).join("")}</tbody></table>
            <div class="fi-filtros" style="margin-top:10px;">
                <label>Ajuste<br><select id="bh-signo"><option value="1">Compensa (resta deuda)</option><option value="-1">Agrega deuda</option></select></label>
                <label>Horas (H:MM)<br><input type="text" id="bh-horas" placeholder="1:30" style="width:80px;"></label>
                <label style="flex:1; min-width:180px;">Detalle<br><input type="text" id="bh-detalle" maxlength="255" placeholder="Ej: compensó el sábado 21/11" style="width:100%;"></label>
                <button type="button" id="bh-ajustar">Guardar ajuste</button>
                <button type="button" id="bh-cancelar">Cerrar</button>
            </div>`);
        caja.scrollIntoView({ behavior: "smooth", block: "start" });
        caja.querySelector("#bh-cancelar").onclick = () => bhCaja("");
        caja.querySelector("#bh-ajustar").onclick = () => bhAjustar(d.cuil);
    } catch (e) {
        fiToast(e.message, true);
    }
}

function bhLeerHoras(texto) {
    const m = String(texto || "").trim().match(/^(\d{1,3})(?::(\d{1,2}))?$/);
    if (!m) return null;
    const min = Number(m[1]) * 60 + Number(m[2] || 0);
    return min > 0 ? min : null;
}

async function bhAjustar(cuil) {
    const minutos = bhLeerHoras(document.getElementById("bh-horas").value);
    if (!minutos) { fiToast("Escribí las horas como H:MM, por ejemplo 1:30.", true); return; }
    const signo = Number(document.getElementById("bh-signo").value);
    try {
        const res = await fetch("/api/rrhh/banco-horas/ajuste", {
            method: "POST", headers: bhHeaders(true),
            body: JSON.stringify({ cuil, minutos: signo * minutos, detalle: document.getElementById("bh-detalle").value }),
        });
        if (!res.ok) throw new Error(await bhError(res, "No se pudo guardar el ajuste."));
        fiToast("Ajuste guardado.");
        await bhCargar();
        await bhDetalle(cuil);
    } catch (e) {
        fiToast(e.message, true);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("bh-importar").addEventListener("click", () => document.getElementById("bh-archivo").click());
    document.getElementById("bh-archivo").addEventListener("change", e => { bhSaldoInicial(e.target.files[0]); e.target.value = ""; });
    document.getElementById("bh-sumar").addEventListener("click", bhSumarFichadas);
    document.getElementById("bh-q").addEventListener("input", bhPintar);
    document.getElementById("bh-cuerpo").addEventListener("click", e => {
        const b = e.target.closest("button[data-cuil]");
        if (b) bhDetalle(b.dataset.cuil);
    });
    bhCargar();
});
