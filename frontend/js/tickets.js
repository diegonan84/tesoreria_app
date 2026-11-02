// ============================================================================
// tickets.js - MESA DE AYUDA
// ============================================================================

const TK = {
    catalogos: { categorias: [], prioridades: [], estados: [], es_soporte: false },
    alcance: "todos",
    agentes: [],
    actual: null,       // ticket abierto en el panel
    miId: null,
    busquedaTimer: null,
};

function tkHeaders(json = false) {
    const h = { "Authorization": `Bearer ${localStorage.getItem("token")}` };
    if (json) h["Content-Type"] = "application/json";
    return h;
}

// Las fechas vienen en UTC sin zona: les agregamos la "Z" para que el navegador las pase a hora local
function tkFecha(iso) {
    if (!iso) return null;
    return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z");
}
function tkFormatoFecha(iso) {
    const d = tkFecha(iso);
    if (!d) return "—";
    return d.toLocaleString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
function tkHace(iso) {
    const d = tkFecha(iso);
    if (!d) return "—";
    const seg = Math.round((Date.now() - d.getTime()) / 1000);
    if (seg < 60) return "recién";
    const min = Math.round(seg / 60);
    if (min < 60) return `hace ${min} min`;
    const h = Math.round(min / 60);
    if (h < 24) return `hace ${h} h`;
    const dias = Math.round(h / 24);
    if (dias < 7) return `hace ${dias} día${dias > 1 ? "s" : ""}`;
    return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "2-digit" });
}
function slug(txt) { return String(txt || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, "-"); }
function badgeEstado(e) { return `<span class="tk-badge est-${slug(e)}">${escapeHTML(e)}</span>`; }
function badgePrioridad(p) { return `<span class="pri pri-${slug(p)}">${escapeHTML(p)}</span>`; }

function toast(msg, error = false) {
    const t = document.getElementById("tk-toast");
    t.textContent = msg;
    t.classList.toggle("error", error);
    t.classList.add("visible");
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove("visible"), 3000);
}

async function tkError(res) {
    try {
        const j = await res.json();
        if (typeof j.detail === "string") return j.detail;
        if (Array.isArray(j.detail) && j.detail[0]) return j.detail[0].msg;
    } catch (e) {}
    return "Ocurrió un error. Probá de nuevo.";
}

// ---------------------------------------------------------------------------
// Inicio
// ---------------------------------------------------------------------------
async function iniciarTickets() {
    const token = localStorage.getItem("token");
    if (!token) return;
    const datos = decodificarToken(token) || {};
    TK.miId = datos.id;

    try {
        const res = await fetch(`${API_URL}/api/tickets/catalogos`, { headers: tkHeaders() });
        if (res.ok) TK.catalogos = await res.json();
    } catch (e) {}

    const llenar = (id, lista) => {
        const sel = document.getElementById(id);
        lista.forEach(v => sel.insertAdjacentHTML("beforeend", `<option value="${escapeHTML(v)}">${escapeHTML(v)}</option>`));
    };
    llenar("f-estado", TK.catalogos.estados);
    llenar("f-prioridad", TK.catalogos.prioridades);
    llenar("f-categoria", TK.catalogos.categorias);
    llenar("n-categoria", TK.catalogos.categorias);
    llenar("n-prioridad", TK.catalogos.prioridades);
    document.getElementById("n-prioridad").value = "Media";
    document.getElementById("n-categoria").value = "Otro";

    if (TK.catalogos.es_soporte) {
        document.getElementById("tk-tabs").style.display = "flex";
        document.getElementById("btn-exportar").style.display = "inline-block";
        document.getElementById("c-interno-wrap").style.display = "flex";
        document.getElementById("tk-sub").textContent = "Atendé los pedidos de las áreas, asignalos y llevá el seguimiento.";
        cargarAgentes();
    } else {
        document.body.classList.add("tk-no-soporte");
    }

    document.querySelectorAll(".tk-tab").forEach(btn => btn.addEventListener("click", () => {
        document.querySelectorAll(".tk-tab").forEach(b => b.classList.remove("activa"));
        btn.classList.add("activa");
        TK.alcance = btn.dataset.alcance;
        refrescar();
    }));
    ["f-estado", "f-prioridad", "f-categoria"].forEach(id => document.getElementById(id).addEventListener("change", refrescar));
    document.getElementById("f-q").addEventListener("input", () => {
        clearTimeout(TK.busquedaTimer);
        TK.busquedaTimer = setTimeout(cargarTickets, 300);
    });
    document.addEventListener("keydown", e => {
        if (e.key !== "Escape") return;
        if (document.getElementById("modal-nuevo").classList.contains("abierto")) cerrarNuevoTicket();
        else cerrarDetalle();
    });

    await refrescar();

    // Enlace directo: /tickets?id=12
    // Enlace "Nuevo ticket" del menú: /tickets?nuevo=1
    const params = new URLSearchParams(location.search);
    const id = params.get("id");
    if (id) abrirDetalle(parseInt(id, 10));
    else if (params.get("nuevo")) {
        history.replaceState(null, "", "/tickets");
        abrirNuevoTicket();
    }
}

function refrescar() {
    return Promise.all([cargarResumen(), cargarTickets()]);
}

async function cargarAgentes() {
    try {
        const res = await fetch(`${API_URL}/api/tickets/agentes`, { headers: tkHeaders() });
        if (res.ok) TK.agentes = await res.json();
    } catch (e) {}
}

// ---------------------------------------------------------------------------
// Contadores
// ---------------------------------------------------------------------------
async function cargarResumen() {
    let r;
    try {
        const res = await fetch(`${API_URL}/api/tickets/resumen`, { headers: tkHeaders() });
        if (!res.ok) return;
        r = await res.json();
    } catch (e) { return; }

    const pe = r.por_estado || {};
    const activos = (pe["Abierto"] || 0) + (pe["En curso"] || 0) + (pe["En espera"] || 0);
    const tarjetas = [
        { n: activos, l: "Activos", estado: "activos", color: "#1a3644" },
        { n: pe["Abierto"] || 0, l: "Abiertos", estado: "Abierto", color: "#3b7dbf" },
        { n: pe["En curso"] || 0, l: "En curso", estado: "En curso", color: "#e5b800" },
        { n: pe["En espera"] || 0, l: "En espera", estado: "En espera", color: "#8a55b5" },
        { n: pe["Resuelto"] || 0, l: "Resueltos", estado: "Resuelto", color: "#58a598" },
    ];
    if (TK.catalogos.es_soporte) {
        tarjetas.push({ n: r.sin_asignar || 0, l: "Sin asignar", alcance: "sin_asignar", color: "#d9534f" });
    }
    const estadoActual = document.getElementById("f-estado").value;
    document.getElementById("tk-stats").innerHTML = tarjetas.map(t => {
        const activa = t.alcance ? TK.alcance === t.alcance : (estadoActual === t.estado && TK.alcance !== "sin_asignar");
        const data = t.alcance ? `data-alcance="${t.alcance}"` : `data-estado="${escapeHTML(t.estado)}"`;
        return `<button class="tk-stat ${activa ? "activa" : ""}" style="border-left-color:${t.color}" ${data} onclick="filtrarDesdeStat(this)">
                    <span class="n">${t.n}</span><span class="l">${t.l}</span>
                </button>`;
    }).join("");
}

function filtrarDesdeStat(btn) {
    if (btn.dataset.alcance) {
        TK.alcance = btn.dataset.alcance;
        document.getElementById("f-estado").value = "activos";
    } else {
        document.getElementById("f-estado").value = btn.dataset.estado;
        if (TK.alcance === "sin_asignar") TK.alcance = "todos";
    }
    document.querySelectorAll(".tk-tab").forEach(b => b.classList.toggle("activa", b.dataset.alcance === TK.alcance));
    refrescar();
}

// ---------------------------------------------------------------------------
// Listado
// ---------------------------------------------------------------------------
async function cargarTickets() {
    const p = new URLSearchParams();
    p.set("alcance", TK.alcance);
    const estado = document.getElementById("f-estado").value;
    const prioridad = document.getElementById("f-prioridad").value;
    const categoria = document.getElementById("f-categoria").value;
    const q = document.getElementById("f-q").value.trim();
    if (estado) p.set("estado", estado);
    if (prioridad) p.set("prioridad", prioridad);
    if (categoria) p.set("categoria", categoria);
    if (q) p.set("q", q);

    const tbody = document.getElementById("tk-tbody");
    const vacio = document.getElementById("tk-vacio");
    let lista = [];
    try {
        const res = await fetch(`${API_URL}/api/tickets?${p.toString()}`, { headers: tkHeaders() });
        if (!res.ok) { toast(await tkError(res), true); return; }
        lista = await res.json();
    } catch (e) {
        tbody.innerHTML = "";
        vacio.style.display = "block";
        vacio.textContent = "No se pudo conectar con el servidor.";
        return;
    }

    if (!lista.length) {
        tbody.innerHTML = "";
        vacio.style.display = "block";
        const hayFiltros = q || prioridad || categoria || (estado && estado !== "activos");
        vacio.innerHTML = hayFiltros
            ? "No hay tickets que coincidan con los filtros."
            : (TK.catalogos.es_soporte && TK.alcance !== "mios"
                ? "No hay tickets pendientes. 🎉"
                : "Todavía no cargaste ningún ticket.<br><br><button class='tk-btn primario' onclick='abrirNuevoTicket()'>+ Crear el primero</button>");
        return;
    }
    vacio.style.display = "none";
    tbody.innerHTML = lista.map(t => `
        <tr onclick="abrirDetalle(${t.id})">
            <td><span class="tk-num">${escapeHTML(t.numero || "—")}</span></td>
            <td>
                <div class="tk-titulo">${escapeHTML(t.titulo)}${t.cantidad_comentarios ? `<span class="tk-coment">💬 ${t.cantidad_comentarios}</span>` : ""}</div>
                <div class="tk-meta">${escapeHTML(t.categoria)}${t.numero_inventario ? " · Inv. " + escapeHTML(t.numero_inventario) : ""}</div>
            </td>
            <td class="col-soporte">
                ${t.solicitante ? escapeHTML(t.solicitante.nombre) : "—"}
                ${t.solicitante && t.solicitante.sector ? `<div class="tk-meta">${escapeHTML(t.solicitante.sector)}</div>` : ""}
            </td>
            <td>${badgePrioridad(t.prioridad)}</td>
            <td>${badgeEstado(t.estado)}</td>
            <td>${t.asignado ? escapeHTML(t.asignado.nombre) : `<span class="tk-nadie">Sin asignar</span>`}</td>
            <td title="${tkFormatoFecha(t.fecha_actualizacion || t.fecha_creacion)}">${tkHace(t.fecha_actualizacion || t.fecha_creacion)}</td>
        </tr>`).join("");
}

// ---------------------------------------------------------------------------
// Detalle (panel lateral)
// ---------------------------------------------------------------------------
async function abrirDetalle(id) {
    let t;
    try {
        const res = await fetch(`${API_URL}/api/tickets/${id}`, { headers: tkHeaders() });
        if (!res.ok) { toast(await tkError(res), true); return; }
        t = await res.json();
    } catch (e) { toast("No se pudo abrir el ticket.", true); return; }

    TK.actual = t;
    pintarDetalle(t);
    document.getElementById("tk-overlay").classList.add("abierto");
    const drawer = document.getElementById("tk-drawer");
    drawer.classList.add("abierto");
    drawer.setAttribute("aria-hidden", "false");
    history.replaceState(null, "", `/tickets?id=${t.id}`);
}

function cerrarDetalle() {
    document.getElementById("tk-overlay").classList.remove("abierto");
    const drawer = document.getElementById("tk-drawer");
    drawer.classList.remove("abierto");
    drawer.setAttribute("aria-hidden", "true");
    TK.actual = null;
    history.replaceState(null, "", "/tickets");
}

function pintarDetalle(t) {
    const soporte = TK.catalogos.es_soporte;
    const esMio = t.solicitante && t.solicitante.id === TK.miId;
    const finalizado = t.estado === "Resuelto" || t.estado === "Cerrado";

    document.getElementById("d-numero").textContent = t.numero || "";
    document.getElementById("d-estado-badge").innerHTML = badgeEstado(t.estado);

    const opciones = (lista, actual) => lista.map(v => `<option ${v === actual ? "selected" : ""}>${escapeHTML(v)}</option>`).join("");
    const opcionesAgentes = `<option value="">— Sin asignar —</option>` + TK.agentes.map(a =>
        `<option value="${a.id}" ${t.asignado && t.asignado.id === a.id ? "selected" : ""}>${escapeHTML(a.nombre)}</option>`).join("");

    let gestion = "";
    if (soporte) {
        const tomar = (!t.asignado || t.asignado.id !== TK.miId) && !finalizado
            ? `<button class="tk-btn menta" onclick="tomarTicket()">🙋 Tomar ticket</button>` : "";
        const resolver = !finalizado ? `<button class="tk-btn primario" onclick="cambiarEstado('Resuelto')">✔ Marcar resuelto</button>` : "";
        const esperar = t.estado !== "En espera" && !finalizado ? `<button class="tk-btn ghost" onclick="cambiarEstado('En espera')">Esperar respuesta</button>` : "";
        gestion = `
            <div class="tk-gestion">
                <h4>Gestión</h4>
                <div class="tk-gestion-grid">
                    <div><label>Estado</label><select id="g-estado" onchange="cambiarCampo('estado', this.value)">${opciones(TK.catalogos.estados, t.estado)}</select></div>
                    <div><label>Prioridad</label><select id="g-prioridad" onchange="cambiarCampo('prioridad', this.value)">${opciones(TK.catalogos.prioridades, t.prioridad)}</select></div>
                    <div><label>Asignado a</label><select id="g-asignado" onchange="cambiarAsignado(this.value)">${opcionesAgentes}</select></div>
                </div>
                <div class="tk-gestion-acciones">${tomar}${resolver}${esperar}</div>
            </div>`;
    } else if (esMio) {
        gestion = `<div class="tk-gestion-acciones" style="margin-top:14px;">
            ${finalizado
                ? `<button class="tk-btn ghost" onclick="cambiarEstado('Abierto')">↺ Reabrir ticket</button>`
                : `<button class="tk-btn peligro" onclick="cambiarEstado('Cerrado')">Cerrar ticket (ya no lo necesito)</button>`}
        </div>`;
    }

    const equipo = t.equipo
        ? `<div class="tk-equipo">🖥️ <strong>${escapeHTML(t.equipo.numero_inventario)}</strong> · ${escapeHTML([t.equipo.tipo, t.equipo.marca, t.equipo.modelo].filter(Boolean).join(" "))}
             ${t.equipo.nombre_de_equipo ? `<br><span style="color:#8a989e;">Nombre de red: ${escapeHTML(t.equipo.nombre_de_equipo)}${t.equipo.puesto ? " · Puesto " + escapeHTML(t.equipo.puesto) : ""}</span>` : ""}</div>`
        : (t.numero_inventario ? `<div class="tk-equipo">🖥️ Inventario <strong>${escapeHTML(t.numero_inventario)}</strong> <span style="color:#8a989e;">(no figura en Patrimonio)</span></div>` : "");

    const hilo = (t.comentarios || []).map(c => {
        if (c.tipo === "sistema") {
            return `<div class="tk-sistema">${escapeHTML(c.texto)} — ${c.usuario ? escapeHTML(c.usuario.nombre) : "Sistema"}, ${tkHace(c.fecha)}</div>`;
        }
        const propio = c.usuario && c.usuario.id === TK.miId;
        return `<div class="tk-msg ${propio ? "propio" : ""} ${c.es_interno ? "interno" : ""}">
                    <div class="tk-msg-cab"><strong>${c.usuario ? escapeHTML(c.usuario.nombre) : "—"}</strong> · <span title="${tkFormatoFecha(c.fecha)}">${tkHace(c.fecha)}</span>${c.es_interno ? `<span class="tk-msg-tag">INTERNO</span>` : ""}</div>
                    <div class="tk-msg-cuerpo">${escapeHTML(c.texto)}</div>
                </div>`;
    }).join("");

    document.getElementById("d-body").innerHTML = `
        <h3>${escapeHTML(t.titulo)}</h3>
        <dl class="tk-datos">
            <div><dt>Solicitante</dt><dd>${t.solicitante ? escapeHTML(t.solicitante.nombre) : "—"}${t.solicitante && t.solicitante.sector ? ` <span style="color:#8a989e;">· ${escapeHTML(t.solicitante.sector)}</span>` : ""}</dd></div>
            <div><dt>Creado</dt><dd>${tkFormatoFecha(t.fecha_creacion)}</dd></div>
            <div><dt>Categoría</dt><dd>${escapeHTML(t.categoria)}</dd></div>
            <div><dt>Prioridad</dt><dd>${badgePrioridad(t.prioridad)}</dd></div>
            <div><dt>Asignado a</dt><dd>${t.asignado ? escapeHTML(t.asignado.nombre) : `<span class="tk-nadie">Sin asignar</span>`}</dd></div>
            <div><dt>${t.fecha_cierre ? "Finalizado" : "Última actividad"}</dt><dd>${tkFormatoFecha(t.fecha_cierre || t.fecha_actualizacion)}</dd></div>
        </dl>
        <div class="tk-desc">${escapeHTML(t.descripcion)}</div>
        ${equipo}
        ${gestion}
        <div class="tk-hilo">
            <h4>Actividad</h4>
            ${hilo || `<div class="tk-sistema">Sin actividad todavía.</div>`}
        </div>`;

    const form = document.getElementById("form-comentario");
    form.style.display = (t.estado === "Cerrado" && !soporte) ? "none" : "block";
    document.getElementById("c-texto").placeholder = soporte && !esMio
        ? "Respondé al solicitante…" : "Agregá información o respondé a Soporte…";

    const body = document.getElementById("d-body");
    body.scrollTop = body.scrollHeight;
}

async function actualizarTicket(cambios, mensajeOk) {
    if (!TK.actual) return;
    try {
        const res = await fetch(`${API_URL}/api/tickets/${TK.actual.id}`, {
            method: "PUT", headers: tkHeaders(true), body: JSON.stringify(cambios)
        });
        if (!res.ok) { toast(await tkError(res), true); await abrirDetalle(TK.actual.id); return; }
        toast(mensajeOk || "Ticket actualizado");
        await abrirDetalle(TK.actual.id);
        refrescar();
    } catch (e) { toast("No se pudo actualizar el ticket.", true); }
}

function cambiarCampo(campo, valor) { actualizarTicket({ [campo]: valor }); }
function cambiarEstado(estado) {
    const msg = { "Resuelto": "Ticket marcado como resuelto", "Cerrado": "Ticket cerrado", "Abierto": "Ticket reabierto", "En espera": "Ticket en espera de respuesta" }[estado];
    actualizarTicket({ estado }, msg);
}
function cambiarAsignado(valor) {
    actualizarTicket(valor ? { asignado_id: parseInt(valor, 10) } : { desasignar: true }, valor ? "Ticket asignado" : "Asignación quitada");
}

async function tomarTicket() {
    if (!TK.actual) return;
    try {
        const res = await fetch(`${API_URL}/api/tickets/${TK.actual.id}/tomar`, { method: "POST", headers: tkHeaders() });
        if (!res.ok) { toast(await tkError(res), true); return; }
        toast("Tomaste el ticket");
        await abrirDetalle(TK.actual.id);
        refrescar();
    } catch (e) { toast("No se pudo tomar el ticket.", true); }
}

async function enviarComentario(ev) {
    ev.preventDefault();
    if (!TK.actual) return;
    const txt = document.getElementById("c-texto");
    const interno = document.getElementById("c-interno");
    const texto = txt.value.trim();
    if (!texto) return;
    const btn = ev.target.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
        const res = await fetch(`${API_URL}/api/tickets/${TK.actual.id}/comentarios`, {
            method: "POST", headers: tkHeaders(true),
            body: JSON.stringify({ texto, es_interno: !!(interno && interno.checked) })
        });
        if (!res.ok) { toast(await tkError(res), true); return; }
        txt.value = "";
        if (interno) interno.checked = false;
        await abrirDetalle(TK.actual.id);
        refrescar();
    } catch (e) {
        toast("No se pudo enviar el comentario.", true);
    } finally {
        btn.disabled = false;
    }
}

// ---------------------------------------------------------------------------
// Alta de ticket
// ---------------------------------------------------------------------------
async function abrirNuevoTicket() {
    document.getElementById("form-nuevo").reset();
    document.getElementById("n-prioridad").value = "Media";
    document.getElementById("n-categoria").value = "Otro";
    document.getElementById("n-inventario").style.display = "none";

    const sel = document.getElementById("n-equipo");
    sel.innerHTML = `<option value="">— Ninguno / no aplica —</option>`;
    try {
        const res = await fetch(`${API_URL}/api/tickets/mis-equipos`, { headers: tkHeaders() });
        if (res.ok) {
            const equipos = await res.json();
            if (equipos.length) {
                sel.insertAdjacentHTML("beforeend", `<optgroup label="Mis equipos asignados">` + equipos.map(e =>
                    `<option value="${escapeHTML(e.numero_inventario)}">${escapeHTML(e.numero_inventario)} · ${escapeHTML(e.descripcion)}</option>`).join("") + `</optgroup>`);
            }
        }
    } catch (e) {}
    sel.insertAdjacentHTML("beforeend", `<option value="__otro__">Otro equipo (ingresar Nº de inventario)…</option>`);

    document.getElementById("modal-nuevo").classList.add("abierto");
    setTimeout(() => document.getElementById("n-titulo").focus(), 50);
}

function cerrarNuevoTicket() { document.getElementById("modal-nuevo").classList.remove("abierto"); }

function toggleInventarioManual() {
    const otro = document.getElementById("n-equipo").value === "__otro__";
    const inp = document.getElementById("n-inventario");
    inp.style.display = otro ? "block" : "none";
    if (otro) inp.focus();
}

async function crearTicket(ev) {
    ev.preventDefault();
    const equipoSel = document.getElementById("n-equipo").value;
    const inventario = equipoSel === "__otro__" ? document.getElementById("n-inventario").value.trim() : equipoSel;
    const body = {
        titulo: document.getElementById("n-titulo").value.trim(),
        descripcion: document.getElementById("n-descripcion").value.trim(),
        categoria: document.getElementById("n-categoria").value,
        prioridad: document.getElementById("n-prioridad").value,
        numero_inventario: inventario || null,
    };
    const btn = document.getElementById("btn-crear");
    btn.disabled = true;
    try {
        const res = await fetch(`${API_URL}/api/tickets`, { method: "POST", headers: tkHeaders(true), body: JSON.stringify(body) });
        if (!res.ok) { toast(await tkError(res), true); return; }
        const t = await res.json();
        cerrarNuevoTicket();
        toast(`Ticket ${t.numero} creado`);
        await refrescar();
        abrirDetalle(t.id);
    } catch (e) {
        toast("No se pudo crear el ticket.", true);
    } finally {
        btn.disabled = false;
    }
}

// ---------------------------------------------------------------------------
// Exportar (Soporte)
// ---------------------------------------------------------------------------
async function exportarTickets() {
    const p = new URLSearchParams({ alcance: TK.alcance });
    ["estado", "prioridad", "categoria"].forEach(k => {
        const v = document.getElementById("f-" + k).value;
        if (v) p.set(k, v);
    });
    const q = document.getElementById("f-q").value.trim();
    if (q) p.set("q", q);
    try {
        const res = await fetch(`${API_URL}/api/tickets/exportar?${p.toString()}`, { headers: tkHeaders() });
        if (!res.ok) { toast(await tkError(res), true); return; }
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "Tickets_Mesa_de_Ayuda.xlsx";
        a.click();
        URL.revokeObjectURL(a.href);
    } catch (e) { toast("No se pudo exportar.", true); }
}

document.addEventListener("DOMContentLoaded", iniciarTickets);
