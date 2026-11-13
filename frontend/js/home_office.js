// ============================================================================
// home_office.js - RECURSOS HUMANOS / TABLERO DE HOME OFFICE
// ============================================================================

const HO = { usuarios: [] };
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

function hoBoton(u, d) {
    const tipo = u.dias[d] || "CONVOCADO";
    const clase = tipo.toLowerCase();
    return `<button type="button" class="ho-marca ${clase}" data-usuario="${u.usuario_id}" data-dia="${d}"
                title="${HO_DIAS[d]}: clic para cambiar">${HO_TIPOS[tipo]}</button>`;
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
}

async function hoCambiar(boton) {
    const u = HO.usuarios.find(x => x.usuario_id === Number(boton.dataset.usuario));
    const d = Number(boton.dataset.dia);
    const dias = [...u.dias];
    dias[d] = HO_SIGUIENTE[dias[d] || "CONVOCADO"];
    boton.disabled = true;
    try {
        const res = await fetch(`/api/rrhh/home-office/${u.usuario_id}`, {
            method: "PUT", headers: hoHeaders(true), body: JSON.stringify({ dias }),
        });
        if (!res.ok) throw new Error(await hoError(res, "No se pudo guardar."));
        u.dias = (await res.json()).dias;
        hoToast(`${u.apellido}, ${HO_DIAS[d]}: ${HO_TIPOS[u.dias[d]]}`);
    } catch (e) {
        hoToast(e.message || "No se pudo conectar con el servidor.", true);
    }
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
        const sectores = [...new Set(HO.usuarios.map(u => u.sector || "Sin sector"))].sort();
        document.getElementById("ho-sector").innerHTML = `<option value="">Todos</option>` +
            sectores.map(s => `<option>${escapeHTML(s)}</option>`).join("");
        hoPintar();
    } catch (e) {
        aviso("No se pudo conectar con el servidor.");
    }
}

async function hoExportar(boton) {
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
    document.getElementById("ho-cuerpo").addEventListener("click", e => {
        const boton = e.target.closest("button.ho-marca");
        if (boton) hoCambiar(boton);
    });
    hoCargar();
});
