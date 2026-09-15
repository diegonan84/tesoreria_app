// ============================================================================
// calendario.js - AGENDA / CALENDARIO PERSONAL
// ============================================================================

const DOW = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

let cursor = new Date(); // primer día del mes mostrado (se fuerza el día 1)
let seleccion = new Date();
let eventos = {}; // { "YYYY-MM-DD": [evento, ...] }

function pad(n) { return String(n).padStart(2, "0"); }
function fmtFecha(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
function fmtDiaLargo(d) {
    return `${DOW[(d.getDay() + 6) % 7]}, ${d.getDate()} de ${MESES[d.getMonth()]} de ${d.getFullYear()}`;
}

function authHeaders() {
    return { "Authorization": `Bearer ${localStorage.getItem("token")}` };
}

function recordarTexto(min) {
    if (!min) return "En el momento";
    if (min === 10) return "10 min antes";
    if (min === 30) return "30 min antes";
    if (min === 60) return "1 h antes";
    if (min === 1440) return "1 día antes";
    return `${min} min antes`;
}

function formatHora(iso) {
    const d = new Date(iso);
    return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function cargarEventosMes() {
    const desde = new Date(cursor.getFullYear(), cursor.getMonth(), 1, 0, 0, 0);
    const hasta = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0, 23, 59, 59);
    try {
        const url = `${API_URL}/agenda/eventos?desde=${fmtFecha(desde)}T00:00:00&hasta=${fmtFecha(hasta)}T23:59:59`;
        const res = await fetch(url, { headers: authHeaders() });
        if (!res.ok) return;
        const lista = await res.json();
        eventos = {};
        lista.forEach(ev => {
            const clave = fmtFecha(new Date(ev.fecha_evento));
            (eventos[clave] = eventos[clave] || []).push(ev);
        });
        Object.values(eventos).forEach(arr => arr.sort((a, b) => new Date(a.fecha_evento) - new Date(b.fecha_evento)));
    } catch (e) {}
}

async function cargarProximos() {
    const ahora = new Date();
    const hasta = new Date(ahora.getTime());
    hasta.setDate(hasta.getDate() + 7);
    try {
        const url = `${API_URL}/agenda/eventos?desde=${fmtFecha(ahora)}T00:00:00&hasta=${fmtFecha(hasta)}T23:59:59`;
        const res = await fetch(url, { headers: authHeaders() });
        if (!res.ok) { document.getElementById("lista-proximos").innerHTML = `<div class="cal-vacio">No hay próximos eventos.</div>`; return; }
        const lista = await res.json();
        lista.sort((a, b) => new Date(a.fecha_evento) - new Date(b.fecha_evento));
        const caja = document.getElementById("lista-proximos");
        if (lista.length === 0) {
            caja.innerHTML = `<div class="cal-vacio">No hay próximos eventos.</div>`;
            return;
        }
        caja.innerHTML = lista.slice(0, 8).map(ev => {
            const d = new Date(ev.fecha_evento);
            return `
                <div class="ev-item">
                    <div>
                        <strong style="color:#1a3644; font-size:13px;">${escapeHTML(ev.titulo)}</strong><br>
                        <small>${fmtDiaLargo(d)} · ${formatHora(ev.fecha_evento)} · ${recordarTexto(ev.recordar_antes_min)}</small>
                    </div>
                    <div class="acciones">
                        <button class="btn-mini editar" onclick="abrirEditar(${ev.id})">✏️</button>
                        <button class="btn-mini borrar" onclick="borrarEvento(${ev.id})">🗑️</button>
                    </div>
                </div>`;
        }).join("");
    } catch (e) {
        document.getElementById("lista-proximos").innerHTML = `<div class="cal-vacio">No hay próximos eventos.</div>`;
    }
}

function renderCalendario() {
    const grid = document.getElementById("cal-grid");
    const anio = cursor.getFullYear();
    const mes = cursor.getMonth();
    const primero = new Date(anio, mes, 1);
    const offset = (primero.getDay() + 6) % 7; // lunes = 0
    const diasEnMes = new Date(anio, mes + 1, 0).getDate();
    const totalCeldas = 42;

    document.getElementById("titulo-dia").textContent = fmtDiaLargo(seleccion);

    let html = DOW.map(d => `<div class="cal-dow">${d}</div>`).join("");

    const hoy = new Date();
    for (let i = 0; i < totalCeldas; i++) {
        const num = i - offset + 1;
        const esMesActual = num >= 1 && num <= diasEnMes;
        const fecha = esMesActual ? new Date(anio, mes, num) : null;
        const clave = fecha ? fmtFecha(fecha) : null;
        const esHoy = fecha && fmtFecha(fecha) === fmtFecha(hoy);
        const esSel = fecha && fmtFecha(fecha) === fmtFecha(seleccion);

        let dots = "";
        if (fecha && eventos[clave]) {
            const urgente = eventos[clave].some(ev => {
                const dEv = new Date(ev.fecha_evento);
                const aviso = new Date(dEv.getTime() - (ev.recordar_antes_min || 0) * 60000);
                return aviso <= new Date() && !ev.visto;
            });
            dots = `<div class="cal-dots">` +
                eventos[clave].slice(0, 4).map((ev, idx) =>
                    `<span class="ev-dot ${ev.visto ? '' : urgente ? 'urgente' : ''}" title="${escapeHTML(ev.titulo)}"></span>`
                ).join("") +
                (eventos[clave].length > 4 ? `<span class="ev-dot" title="+${eventos[clave].length - 4} más"></span>` : "") +
                `</div>`;
        }

        html += `
            <div class="cal-cell ${esMesActual ? "" : "other"} ${esSel ? "sel" : ""}" onclick="${fecha ? `seleccionarDia('${clave}')` : ""}" data-fecha="${clave || ""}">
                <span class="cal-num">${esMesActual ? num : ""}</span>
                ${esHoy ? `<span style="font-size:9px; color:#1a3644; font-weight:bold;">HOY</span>` : ""}
                ${dots}
            </div>`;
    }

    document.getElementById("cal-titulo-mes").textContent = `${MESES[mes]} ${anio}`;
    grid.innerHTML = html;
}

async function seleccionarDia(clave) {
    seleccion = new Date(clave + "T12:00:00");
    document.getElementById("titulo-dia").textContent = fmtDiaLargo(seleccion);
    renderCalendario();
    renderDia();
}

function renderDia() {
    const caja = document.getElementById("lista-dia");
    const clave = fmtFecha(seleccion);
    const lista = eventos[clave] || [];
    if (lista.length === 0) {
        caja.innerHTML = `<div class="cal-vacio">Sin eventos este día.</div>
            <div style="text-align:center; margin-top:6px;">
                <button class="btn-mini editar" onclick="abrirNuevo()">+ Agregar</button>
            </div>`;
        return;
    }
    caja.innerHTML = lista.map(ev => `
        <div class="ev-item">
            <div>
                <strong style="color:#1a3644; font-size:13px;">${escapeHTML(ev.titulo)}</strong><br>
                <small>${formatHora(ev.fecha_evento)} · ${recordarTexto(ev.recordar_antes_min)}${ev.visto ? "" : " · ⏰ pendiente"}</small>
                ${ev.descripcion ? `<div style="color:#555; font-size:12px; margin-top:4px;">${escapeHTML(ev.descripcion)}</div>` : ""}
            </div>
            <div class="acciones">
                <button class="btn-mini editar" onclick="abrirEditar(${ev.id})">✏️</button>
                <button class="btn-mini borrar" onclick="borrarEvento(${ev.id})">🗑️</button>
            </div>
        </div>
        <div style="text-align:center; margin:4px 0 10px;">
            <button class="btn-mini editar" onclick="abrirNuevo()">+ Agregar</button>
        </div>`).join("");
}

function abrirNuevo() {
    document.getElementById("ev-id").value = "";
    document.getElementById("ev-titulo").value = "";
    document.getElementById("ev-desc").value = "";
    document.getElementById("ev-recordar").value = "0";
    const d = seleccion;
    document.getElementById("ev-fecha").value = `${fmtFecha(d)}T09:00`;
    document.getElementById("modal-titulo").textContent = "Nuevo evento";
    document.getElementById("modal-evento").classList.add("abierto");
}

function abrirEditar(id) {
    const ev = Object.values(eventos).flat().find(e => e.id === id);
    if (!ev) return;
    document.getElementById("ev-id").value = ev.id;
    document.getElementById("ev-titulo").value = ev.titulo;
    document.getElementById("ev-desc").value = ev.descripcion || "";
    document.getElementById("ev-recordar").value = String(ev.recordar_antes_min || 0);
    document.getElementById("ev-fecha").value = ev.fecha_evento.slice(0, 16);
    document.getElementById("modal-titulo").textContent = "Editar evento";
    document.getElementById("modal-evento").classList.add("abierto");
}

function cerrarModal() {
    document.getElementById("modal-evento").classList.remove("abierto");
}

async function guardarEvento(event) {
    event.preventDefault();
    const id = document.getElementById("ev-id").value;
    const payload = {
        titulo: document.getElementById("ev-titulo").value,
        descripcion: document.getElementById("ev-desc").value,
        fecha_evento: document.getElementById("ev-fecha").value,
        recordar_antes_min: parseInt(document.getElementById("ev-recordar").value, 10)
    };
    const url = id ? `${API_URL}/agenda/eventos/${id}` : `${API_URL}/agenda/eventos`;
    const res = await fetch(url, {
        method: id ? "PUT" : "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    if (res.ok) {
        cerrarModal();
        await recargarTodo();
    } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Error al guardar el evento.");
    }
}

async function borrarEvento(id) {
    if (!confirm("¿Eliminar este evento de la agenda?")) return;
    const res = await fetch(`${API_URL}/agenda/eventos/${id}`, { method: "DELETE", headers: authHeaders() });
    if (res.ok) await recargarTodo();
    else alert("Error al eliminar el evento.");
}

async function recargarTodo() {
    await cargarEventosMes();
    await cargarProximos();
    renderCalendario();
    renderDia();
    if (typeof cargarCampana === "function") cargarCampana();
}

async function initCalendario() {
    // cursor en el primer día del mes de hoy
    cursor = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
    seleccion = new Date();

    const tituloMes = document.createElement("div");
    tituloMes.id = "cal-titulo-mes";
    tituloMes.style.cssText = "font-size:18px; font-weight:bold; color:#1a3644;";
    document.querySelector(".cal-nav").insertBefore(tituloMes, document.getElementById("btn-mes-ant"));

    document.getElementById("btn-mes-ant").addEventListener("click", () => {
        cursor = new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1);
        recargarTodo();
    });
    document.getElementById("btn-mes-sig").addEventListener("click", () => {
        cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
        recargarTodo();
    });
    document.getElementById("btn-hoy").addEventListener("click", () => {
        cursor = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
        seleccion = new Date();
        recargarTodo();
    });
    document.getElementById("modal-evento").addEventListener("click", e => {
        if (e.target.id === "modal-evento") cerrarModal();
    });

    await recargarTodo();
}

document.addEventListener("DOMContentLoaded", initCalendario);