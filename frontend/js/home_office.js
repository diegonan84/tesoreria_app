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

const HO_TIPOS = { HOME: "Home", CONVOCADO: "Convocado" };
const HO_SIGUIENTE = { HOME: "CONVOCADO", CONVOCADO: "HOME" };

function hoFiltrados() {
    const q = hoNormalizar(document.getElementById("ho-q").value.trim());
    const sector = document.getElementById("ho-sector").value;
    const mostrar = document.getElementById("ho-solo").value;
    return HO.usuarios.filter(u =>
        (!q || hoNormalizar(`${u.apellido} ${u.nombre} ${u.cuil}`).includes(q)) &&
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
    const pendiente = tipo !== HO.guardado[u.usuario_id][d] ? " pendiente" : "";
    return `<button type="button" class="ho-marca ${tipo.toLowerCase()}${pendiente}" data-usuario="${u.usuario_id}" data-dia="${d}"
                title="${HO_DIAS[d]}: clic para cambiar${pendiente ? " (sin guardar)" : ""}">${HO_TIPOS[tipo]}</button>`;
}

function hoPintar() {
    const lista = hoFiltrados();
    const cuerpo = document.getElementById("ho-cuerpo");
    if (!lista.length) {
        cuerpo.innerHTML = `<tr><td colspan="8" class="ho-aviso">No hay personas para mostrar.</td></tr>`;
    } else {
        cuerpo.innerHTML = lista.map(u => `
            <tr>
                <td>${escapeHTML(u.apellido)}, ${escapeHTML(u.nombre)}</td>
                <td class="ho-sub">${escapeHTML(u.cuil)}</td>
                <td class="ho-sub">${escapeHTML(u.sector || "Sin sector")}</td>
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
        const sectores = [...new Set(HO.usuarios.map(u => u.sector || "Sin sector"))].sort();
        document.getElementById("ho-sector").innerHTML = `<option value="">Todos</option>` +
            sectores.map(s => `<option>${escapeHTML(s)}</option>`).join("");
        hoPintar();
    } catch (e) {
        aviso("No se pudo conectar con el servidor.");
    }
}

async function hoExportar(boton) {
    if (hoPendientes().length) hoToast("Ojo: el Excel sale con lo guardado; tenés cambios sin guardar.", true);
    boton.disabled = true;
    try {
        const res = await fetch("/api/rrhh/home-office/exportar", { headers: hoHeaders() });
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

async function hoImportar(archivo) {
    if (!archivo) return;
    if (hoPendientes().length && !confirm("Tenés cambios sin guardar en pantalla: la importación los va a reemplazar. ¿Seguir?")) return;
    if (!confirm(`Se va a cargar la semana de cada persona que figure en "${archivo.name}" (se busca por CUIL). ` +
                 "Los días vacíos o en verde quedan Convocado. ¿Continuar?")) return;
    const caja = document.getElementById("ho-resultado");
    const boton = document.getElementById("ho-importar");
    boton.disabled = true;
    try {
        const datos = new FormData();
        datos.append("archivo", archivo);
        const res = await fetch("/api/rrhh/home-office/importar", { method: "POST", headers: hoHeaders(), body: datos });
        if (!res.ok) throw new Error(await hoError(res, "No se pudo importar."));
        const r = await res.json();
        caja.innerHTML = `<b>Importación terminada:</b> ${r.actualizados} persona(s) actualizada(s), ${r.sin_cambios} sin cambios.` +
            (r.problemas.length ? `<ul>${r.problemas.map(p => `<li>${escapeHTML(p)}</li>`).join("")}</ul>` : "");
        caja.style.display = "block";
        await hoCargar();
    } catch (e) {
        hoToast(e.message || "No se pudo conectar con el servidor.", true);
    }
    boton.disabled = false;
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("ho-exportar").addEventListener("click", e => hoExportar(e.currentTarget));
    document.getElementById("ho-importar").addEventListener("click", () => document.getElementById("ho-archivo").click());
    document.getElementById("ho-archivo").addEventListener("change", e => {
        hoImportar(e.target.files[0]);
        e.target.value = "";
    });
    document.getElementById("ho-q").addEventListener("input", hoPintar);
    document.getElementById("ho-sector").addEventListener("change", hoPintar);
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
