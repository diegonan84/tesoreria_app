// ============================================================================
// usuarios.js - GESTIÓN DE USUARIOS Y AUDITORÍA
// ============================================================================

let usuariosGlobales = []; 
let columnaOrdenActual = 'apellido';
let ordenAscendente = true;

async function cargarUsuarios() {
    const tbody = document.getElementById("tabla-usuarios");
    if (!tbody) return;

    const token = localStorage.getItem("token");
    try {
        const res = await fetch(`${API_URL}/admin/usuarios`, { headers: { "Authorization": `Bearer ${token}` } });
        if (!res.ok) throw new Error("No autorizado");
        
        usuariosGlobales = await res.json();
        ordenarTabla('apellido', true); 
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#dc3545; padding: 20px;"><strong>Acceso Denegado.</strong></td></tr>`;
    }
}

function ordenarTabla(columna, forzarAscendente = null) {
    if (forzarAscendente !== null) ordenAscendente = forzarAscendente;
    else {
        if (columnaOrdenActual === columna) ordenAscendente = !ordenAscendente; 
        else ordenAscendente = true; 
    }
    columnaOrdenActual = columna;

    usuariosGlobales.sort((a, b) => {
        let valorA = extraerValorParaOrdenar(a, columna);
        let valorB = extraerValorParaOrdenar(b, columna);
        if (valorA < valorB) return ordenAscendente ? -1 : 1;
        if (valorA > valorB) return ordenAscendente ? 1 : -1;
        return 0;
    });

    actualizarIconosOrden(columna);
    renderizarTabla();
}

function extraerValorParaOrdenar(usuario, columna) {
    if (columna === 'apellido') return (usuario.apellido || "").toLowerCase();
    if (columna === 'puesto') return (usuario.puesto || usuario.reparticion || "").toLowerCase();
    if (columna === 'sector') return usuario.sector ? (usuario.sector.nombre || "").toLowerCase() : "zzzz"; 
    return "";
}

function actualizarIconosOrden(columna) {
    ['apellido', 'puesto', 'sector'].forEach(col => {
        const icon = document.getElementById(`sort-${col}`);
        if (icon) icon.innerHTML = ''; 
    });
    const iconActivo = document.getElementById(`sort-${columna}`);
    if (iconActivo) iconActivo.innerHTML = ordenAscendente ? ' ▲' : ' ▼';
}

function renderizarTabla() {
    const tbody = document.getElementById("tabla-usuarios");
    if (!tbody) return;
    tbody.innerHTML = ""; 

    usuariosGlobales.forEach(u => {
        const tr = document.createElement("tr");
        const inactivo = u.aprobado === true && u.activo === false;
        let badgeActivo;
        if (inactivo) badgeActivo = `<span class="badge badge-rejected">INHABILITADO</span>`;
        else badgeActivo = u.activo ? `<span class="badge badge-approved">APROBADO</span>` : `<span class="badge badge-pending">PENDIENTE</span>`;

        let btnEstado;
        if (inactivo) {
            btnEstado = `<button class="btn-action btn-approve" style="margin-right:5px;" onclick="darDeAlta(${u.id})">Dar de Alta</button>`;
        } else if (u.activo) {
            btnEstado = `<button class="btn-action" style="background:#dc3545; color:white; margin-right:5px;" onclick="darDeBaja(${u.id})">Dar de Baja</button>`;
        } else {
            btnEstado = `<button class="btn-action btn-approve" style="margin-right:5px;" onclick="aprobarUsuario(${u.id})">Aprobar</button>`;
        }
        const btnModificar = `<button class="btn-action" style="background:#8ed1d4; color:#1a3644;" onclick="abrirEdicion(${u.id})">Modificar</button>`;
        const btnReset = `<button class="btn-mini" style="background: #ffc107; color: black; border: none; padding: 7px 10px; border-radius: 4px; cursor: pointer; font-weight: bold; margin-left: 5px;" onclick="resetearClave(${u.id})">🔑 Reset Clave</button>`;

        const listaRoles = u.roles ? u.roles.split(',') : [];
        let badgesRoles = '';
        
        // ✨ FILTRO MÁGICO: Solo mostramos los roles que NO tengan un guion bajo (_)
        const rolesPrincipales = listaRoles.filter(r => !r.includes('_'));
        
        rolesPrincipales.forEach(r => {
            let bg = r === 'Administrador' ? '#ffcc00' : '#e0e6e8';
            let txt = r === 'Administrador' ? '#0b3a47' : '#333';
            // Le damos un toque visual especial a "Operador" si quieres, o queda estándar
            if (r === 'Operador') { bg = '#f8f9fa'; txt = '#6c757d'; }
            
            badgesRoles += `<span style="background:${bg}; color:${txt}; padding:3px 8px; border-radius:4px; font-size:11px; font-weight:bold; margin-right:4px; display:inline-block; margin-bottom:4px;">${r}</span>`;
        });

        const sectorHtml = u.sector ? `<span style="background-color: ${u.sector.color || '#1a3644'}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; display: inline-block; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">${u.sector.nombre}</span>` : '<span style="color: #999; font-size: 11px; font-style: italic;">N/A</span>';
        const puestoTexto = u.puesto ? `<br><span style="font-size:11px; color:#58a598; font-weight:bold;">${u.puesto}</span>` : '';

        tr.innerHTML = `
            <td><strong>${u.apellido}, ${u.nombre}</strong><br><span style="font-size:12px; color:#666;">${u.email}</span></td>
            <td>${u.cuil}</td>
            <td><strong>${u.reparticion}</strong>${puestoTexto}</td>
            <td>${sectorHtml}</td>
            <td>${badgesRoles}</td>
            <td>${badgeActivo}</td>
            <td style="white-space: nowrap;">${btnEstado} ${btnModificar} ${btnReset}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function aprobarUsuario(id) {
    const token = localStorage.getItem("token");
    const res = await fetch(`${API_URL}/admin/usuarios/${id}/aprobar`, { method: "PUT", headers: { "Authorization": `Bearer ${token}` } });
    if (res.ok) cargarUsuarios(); 
}

async function darDeBaja(id) {
    const usuario = usuariosGlobales.find(u => u.id === id);
    const nombre = usuario ? `${usuario.apellido}, ${usuario.nombre}` : id;
    if (!confirm(`¿Estás seguro de dar de baja (inhabilitar) al usuario "${nombre}"? Podrás darlo de alta más adelante.`)) return;
    try {
        const res = await fetch(`${API_URL}/admin/usuarios/${id}/baja`, { method: "PUT", headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` } });
        if (res.ok) { const data = await res.json(); alert("✅ " + data.mensaje); cargarUsuarios(); }
        else { const error = await res.json(); alert("❌ Error: " + (error.detail || "No se pudo dar de baja")); }
    } catch (error) { alert("❌ Error de conexión al dar de baja."); }
}

async function darDeAlta(id) {
    const usuario = usuariosGlobales.find(u => u.id === id);
    const nombre = usuario ? `${usuario.apellido}, ${usuario.nombre}` : id;
    if (!confirm(`¿Dar de alta (reactivar) al usuario "${nombre}"?`)) return;
    try {
        const res = await fetch(`${API_URL}/admin/usuarios/${id}/alta`, { method: "PUT", headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` } });
        if (res.ok) { const data = await res.json(); alert("✅ " + data.mensaje); cargarUsuarios(); }
        else { const error = await res.json(); alert("❌ Error: " + (error.detail || "No se pudo dar de alta")); }
    } catch (error) { alert("❌ Error de conexión al dar de alta."); }
}

async function resetearClave(usuarioId) {
    if (!confirm("¿Estás seguro de que deseas resetear la clave de este usuario a '12345678'?")) return;
    try {
        const res = await fetch(`/admin/usuarios/${usuarioId}/reset-password`, { method: "PUT", headers: { "Authorization": `Bearer ${localStorage.getItem("token")}`, "Content-Type": "application/json" }});
        if (res.ok) { const data = await res.json(); alert("✅ " + data.mensaje); } 
        else { const error = await res.json(); alert("❌ Error: " + (error.detail || "No se pudo resetear la clave")); }
    } catch (error) { alert("❌ Error de conexión al intentar resetear la clave."); }
}

async function importarUsuariosExcel(event) {
    const file = event.target.files[0];
    if (!file) return;
    const formData = new FormData(); formData.append("file", file);

    try {
        const res = await fetch('/admin/usuarios/importar', { method: 'POST', headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }, body: formData });
        const data = await res.json();
        if (res.ok) {
            alert(data.mensaje);
            if (data.errores && data.errores.length > 0) alert("Atención: Hubo " + data.errores.length + " filas omitidas por duplicado.");
            cargarUsuarios(); 
            if (typeof cargarSectores === "function") cargarSectores(); 
        } else alert("❌ Error: " + (data.detail || "No se pudo importar el archivo."));
    } catch (error) { alert("❌ Error de comunicación al intentar subir el archivo."); } 
    finally { event.target.value = ""; }
}

// --- EDICIÓN Y ALTA MANUAL ---
function abrirAlta() {
    document.getElementById("panel-edicion").style.display = "none";
    document.getElementById("alta-nombre").value = "";
    document.getElementById("alta-apellido").value = "";
    document.getElementById("alta-cuil").value = "";
    document.getElementById("alta-email").value = "";
    document.getElementById("alta-reparticion").value = "";
    document.getElementById("alta-puesto").value = ""; 
    if (document.getElementById("alta-sector")) document.getElementById("alta-sector").value = "";
    document.querySelectorAll('#panel-alta .check-rol-alta').forEach(cb => cb.checked = (cb.value === "Operador"));

    const panel = document.getElementById("panel-alta");
    panel.style.display = "block";
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function cerrarAlta() { document.getElementById("panel-alta").style.display = "none"; }

async function guardarAlta(event) {
    event.preventDefault();
    const rolesSeleccionados = Array.from(document.querySelectorAll('#panel-alta .check-rol-alta:checked')).map(cb => cb.value);
    const selSector = document.getElementById("alta-sector");
    const datosNuevos = {
        nombre: document.getElementById("alta-nombre").value,
        apellido: document.getElementById("alta-apellido").value,
        cuil: document.getElementById("alta-cuil").value,
        email: document.getElementById("alta-email").value,
        reparticion: document.getElementById("alta-reparticion").value,
        puesto: document.getElementById("alta-puesto").value || null,
        sector_id: (selSector && selSector.value) ? parseInt(selSector.value) : null,
        roles: rolesSeleccionados
    };

    try {
        const res = await fetch(`${API_URL}/admin/usuarios/manual`, { method: "POST", headers: { "Authorization": `Bearer ${localStorage.getItem("token")}`, "Content-Type": "application/json" }, body: JSON.stringify(datosNuevos) });
        const respuesta = await res.json();
        if (res.ok) { alert(respuesta.mensaje); cerrarAlta(); cargarUsuarios(); } 
        else alert(respuesta.detail);
    } catch (error) { alert("Error de conexión con el servidor."); }
}

function abrirEdicion(id) {
    document.getElementById("panel-alta").style.display = "none";
    const usuario = usuariosGlobales.find(u => u.id === id);
    if (!usuario) return;

    document.getElementById("edit-id").value = usuario.id;
    document.getElementById("edit-nombre").value = usuario.nombre;
    document.getElementById("edit-apellido").value = usuario.apellido;
    document.getElementById("edit-cuil").value = usuario.cuil;
    document.getElementById("edit-email").value = usuario.email;
    document.getElementById("edit-reparticion").value = usuario.reparticion;
    document.getElementById("edit-puesto").value = usuario.puesto || ""; 
    if (document.getElementById("edit-sector")) document.getElementById("edit-sector").value = usuario.sector_id || "";

    const listaRoles = usuario.roles ? usuario.roles.split(',') : [];
    document.querySelectorAll('#panel-edicion .check-rol-edit').forEach(cb => { 
        cb.checked = listaRoles.includes(cb.value); 
    });

    // ✨ APLICAMOS LA LÓGICA VISUAL DEL ÁRBOL ✨
    toggleAdmin('edit');

    const panel = document.getElementById("panel-edicion");
    panel.style.display = "block";
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
}


function cerrarEdicion() { document.getElementById("panel-edicion").style.display = "none"; }

async function guardarEdicion(event) {
    event.preventDefault();
    const id = document.getElementById("edit-id").value;
    
    let rolesSeleccionados = Array.from(document.querySelectorAll('#panel-edicion .check-rol-edit:checked')).map(cb => cb.value);
    
    // ✨ ASEGURAMOS EL ROL OPERADOR ✨
    if (!rolesSeleccionados.includes("Operador")) {
        rolesSeleccionados.push("Operador");
    }

    const selSector = document.getElementById("edit-sector");

    const datosModificados = {
        nombre: document.getElementById("edit-nombre").value,
        apellido: document.getElementById("edit-apellido").value,
        cuil: document.getElementById("edit-cuil").value,
        email: document.getElementById("edit-email").value,
        reparticion: document.getElementById("edit-reparticion").value,
        puesto: document.getElementById("edit-puesto").value || null,
        sector_id: (selSector && selSector.value) ? parseInt(selSector.value) : null,
        roles: rolesSeleccionados
    };

    try {
        const res = await fetch(`${API_URL}/admin/usuarios/${id}/editar`, { 
            method: "PUT", 
            headers: { 
                "Authorization": `Bearer ${localStorage.getItem("token")}`, 
                "Content-Type": "application/json" 
            }, 
            body: JSON.stringify(datosModificados) 
        });
        
        if (res.ok) { 
            cerrarEdicion(); 
            cargarUsuarios(); 
        } else { 
            alert("Ocurrió un error al intentar modificar el usuario.");
        }
    } catch (error) { 
        alert("Error de conexión con el servidor."); 
    }
}

// --- AUDITORÍA ---
let paginaActual = 0;
const TAM_PAGINA = 100;

async function cargarAuditoria(pagina = 0) {
    const tbody = document.getElementById("tabla-auditoria");
    if (!tbody) return;
    paginaActual = pagina;

    const buscar = document.getElementById("filtro-buscar")?.value || "";
    const accion = document.getElementById("filtro-accion")?.value || "";
    const fechaDesde = document.getElementById("filtro-fecha-desde")?.value || "";
    const fechaHasta = document.getElementById("filtro-fecha-hasta")?.value || "";

    const params = new URLSearchParams();
    params.set("skip", pagina * TAM_PAGINA);
    params.set("limit", TAM_PAGINA);
    if (buscar) params.set("buscar", buscar);
    if (accion) params.set("accion", accion);
    if (fechaDesde) params.set("fecha_desde", fechaDesde);
    if (fechaHasta) params.set("fecha_hasta", fechaHasta);

    try {
        const res = await fetch(`${API_URL}/admin/auditoria?${params}`, { headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` } });
        if (!res.ok) throw new Error("No autorizado");
        
        const data = await res.json();
        const logs = data.registros || [];
        const total = data.total || 0;
        tbody.innerHTML = "";
        
        const coloresAcciones = {
            "INICIO_SESION": "#58a598", "CIERRE_SESION": "#dc3545",
            "CREAR_USUARIO_MANUAL": "#0d6efd", "APROBAR_USUARIO": "#198754",
            "EDITAR_USUARIO": "#fd7e14", "ADMIN_RESET_CLAVE": "#dc3545",
            "CAMBIAR_CONTRASENA": "#6f42c1", "RESET_CONTRASENA": "#6f42c1",
            "CREAR_SECTOR": "#0d6efd", "EDITAR_SECTOR": "#fd7e14",
            "CREAR_NOTIFICACION": "#20c997", "IMPORTAR_USUARIOS_EXCEL": "#0d6efd",
            "CREAR_PATRIMONIO": "#198754", "EDITAR_PATRIMONIO": "#fd7e14",
            "BAJA_PATRIMONIO": "#dc3545", "IMPORTAR_PATRIMONIO": "#0d6efd",
            "ASIGNAR_EQUIPO": "#6f42c1", "IMPORTAR_INFORMATICA": "#0d6efd",
            "GUARDAR_MAPA": "#20c997", "BORRAR_MAPA": "#dc3545",
            "GENERAR_NOTA_SALIDA": "#6f42c1"
        };

        logs.forEach(log => {
            const tr = document.createElement("tr");
            const fechaHora = new Date(log.fecha + "Z").toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const colorAccion = coloresAcciones[log.accion] || "#555";
            const pcParts = [];
            if (log.pc_nombre && log.pc_nombre !== "No resuelto" && log.pc_nombre !== "LOCAL") pcParts.push(`<strong>${escapeHTML(log.pc_nombre)}</strong>`);
            if (log.equipo_patrimonio) pcParts.push(`Nº ${escapeHTML(log.equipo_patrimonio)}`);
            if (log.ip_address) pcParts.push(escapeHTML(log.ip_address));
            const pcInfo = pcParts.length ? pcParts.join(" · ") : "-";

            tr.innerHTML = `
                <td style="font-family: monospace; color: #666; font-size: 12px;">${escapeHTML(fechaHora)}</td>
                <td><strong>${escapeHTML(log.usuario)}</strong><br><span style="font-size:11px; color:#666;">${escapeHTML(log.reparticion || "")}</span></td>
                <td><strong style="color: ${colorAccion}; font-size: 12px;">${escapeHTML(log.accion)}</strong></td>
                <td style="font-size: 12px;">${escapeHTML(log.detalle || "")}</td>
                <td style="font-size: 11px; color: #888; font-family: monospace;">${escapeHTML(pcInfo)}</td>
            `;
            tbody.appendChild(tr);
        });

        const totalPaginas = Math.ceil(total / TAM_PAGINA);
        document.getElementById("contador-registros").textContent = `${total} registros encontrados`;
        document.getElementById("info-paginacion").textContent = `Página ${pagina + 1} de ${totalPaginas || 1}`;
        document.getElementById("btn-prev").disabled = pagina === 0;
        document.getElementById("btn-next").disabled = (pagina + 1) >= totalPaginas;

        cargarFiltrosAuditoria();
    } catch (error) { tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#dc3545;">Acceso Denegado.</td></tr>`; }
}

async function cargarFiltrosAuditoria() {
    try {
        const res = await fetch(`${API_URL}/admin/auditoria/acciones`, { headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` } });
        if (!res.ok) return;
        const acciones = await res.json();
        const select = document.getElementById("filtro-accion");
        if (!select) return;
        const actual = select.value;
        select.innerHTML = '<option value="">Todas</option>';
        acciones.forEach(a => {
            const opt = document.createElement("option");
            opt.value = a; opt.textContent = a;
            if (a === actual) opt.selected = true;
            select.appendChild(opt);
        });
    } catch (e) {}
}

function limpiarFiltros() {
    document.getElementById("filtro-buscar").value = "";
    document.getElementById("filtro-accion").value = "";
    document.getElementById("filtro-fecha-desde").value = "";
    document.getElementById("filtro-fecha-hasta").value = "";
    cargarAuditoria(0);
}


let listaSectoresGlobales = [];

function abrirAlta() {
    // Resetea el formulario por si quedó algo escrito
    document.getElementById('form-alta').reset();
    
    // Oculta el panel de edición si estaba abierto para no pisarse
    document.getElementById('panel-edicion').style.display = 'none';
    
    // Muestra el panel de alta
    document.getElementById('panel-alta').style.display = 'block';
    
    // Hace un scroll suave hacia el panel
    document.getElementById('panel-alta').scrollIntoView({ behavior: 'smooth' });
}

function cerrarAlta() {
    document.getElementById('panel-alta').style.display = 'none';
}

async function guardarAlta(event) {
    event.preventDefault(); // Evita que la página se recargue bruscamente

    // 1. Recolectamos los roles que tengan el tilde puesto
    let rolesSeleccionados = Array.from(document.querySelectorAll('#panel-alta .check-rol-alta:checked')).map(cb => cb.value);
    
    // ✨ ASEGURAMOS EL ROL OPERADOR ✨
    if (!rolesSeleccionados.includes("Operador")) {
        rolesSeleccionados.push("Operador");
    }

    const selSector = document.getElementById("alta-sector");

    // 2. Armamos el paquete de datos para enviar al backend
    const payload = {
        nombre: document.getElementById("alta-nombre").value.trim(),
        apellido: document.getElementById("alta-apellido").value.trim(),
        cuil: document.getElementById("alta-cuil").value.trim(),
        email: document.getElementById("alta-email").value.trim(),
        reparticion: document.getElementById("alta-reparticion").value.trim(),
        puesto: document.getElementById("alta-puesto").value.trim(),
        sector_id: (selSector && selSector.value) ? parseInt(selSector.value) : null,
        roles: rolesSeleccionados
    };

    try {
        const res = await fetch('/admin/usuarios/manual', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok) {
            alert(data.mensaje); 
            cerrarAlta();
            cargarUsuarios();
        } else {
            alert("Error: " + (data.detail || "No se pudo crear el usuario."));
        }
    } catch (error) {
        console.error("Error de red:", error);
        alert("Ocurrió un error de conexión al intentar crear el usuario.");
    }
}

async function cargarSectores() {
    try {
        const response = await fetch('/sectores', {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (response.ok) {
            listaSectoresGlobales = await response.json();
            const opciones = '<option value="">-- Sin sector asignado --</option>' + 
                                listaSectoresGlobales.map(s => `<option value="${s.id}">${s.nombre}</option>`).join('');
            
            // ✨ CORRECCIÓN: Solo inyectamos si los elementos existen en el HTML actual
            if (document.getElementById('alta-sector')) {
                document.getElementById('alta-sector').innerHTML = opciones;
            }
            if (document.getElementById('edit-sector')) {
                document.getElementById('edit-sector').innerHTML = opciones;
            }
        }
    } catch (error) {
        console.error("Error al cargar los sectores:", error);
    }
}

function abrirModalSector() {
    document.getElementById('modal-sector').style.display = 'block';
    document.getElementById('modal-backdrop-sector').style.display = 'block';
}

function cerrarModalSector() {
    document.getElementById('modal-sector').style.display = 'none';
    document.getElementById('modal-backdrop-sector').style.display = 'none';
    document.getElementById('nuevo-sector-nombre').value = '';
    document.getElementById('nuevo-sector-color').value = '#1a3644';
}

async function guardarNuevoSector() {
    const nombre = document.getElementById('nuevo-sector-nombre').value;
    const color = document.getElementById('nuevo-sector-color').value;

    if (!nombre || nombre.trim() === "") return alert("El nombre es obligatorio");

    try {
        const response = await fetch('/sectores', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}` 
            },
            body: JSON.stringify({ nombre: nombre.trim(), color: color })
        });

        if (response.ok) {
            alert("¡Sector creado exitosamente!");
            cerrarModalSector();
            cargarSectores(); 
        } else {
            const error = await response.json();
            alert("Error: " + (error.detail || "No se pudo crear el sector."));
        }
    } catch (error) {
        alert("Error de conexión al intentar crear el sector.");
    }
}

function abrirModalEditarSector(selectId) {
    const selectElement = document.getElementById(selectId);
    const sectorId = selectElement.value;

    if (!sectorId) {
        alert("Por favor, seleccione un sector de la lista para poder editarlo.");
        return;
    }

    const sectorEncontrado = listaSectoresGlobales.find(s => s.id == sectorId);
    if (!sectorEncontrado) return;

    document.getElementById('edit-sector-id').value = sectorEncontrado.id;
    document.getElementById('edit-sector-nombre').value = sectorEncontrado.nombre;
    document.getElementById('edit-sector-color').value = sectorEncontrado.color || '#1a3644';

    document.getElementById('modal-editar-sector').style.display = 'block';
    document.getElementById('modal-backdrop-editar-sector').style.display = 'block';
}

function cerrarModalEditarSector() {
    document.getElementById('modal-editar-sector').style.display = 'none';
    document.getElementById('modal-backdrop-editar-sector').style.display = 'none';
}

async function guardarEdicionSector() {
    const id = document.getElementById('edit-sector-id').value;
    const nombre = document.getElementById('edit-sector-nombre').value;
    const color = document.getElementById('edit-sector-color').value;

    if (!nombre || nombre.trim() === "") return alert("El nombre es obligatorio");

    try {
        const response = await fetch(`/sectores/${id}`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}` 
            },
            body: JSON.stringify({ nombre: nombre.trim(), color: color })
        });

        if (response.ok) {
            alert("¡Sector actualizado exitosamente!");
            cerrarModalEditarSector();
            cargarSectores();
            cargarUsuarios();
        } else {
            const error = await response.json();
            alert("Error: " + (error.detail || "No se pudo actualizar el sector."));
        }
    } catch (error) {
        alert("Error de conexión al intentar actualizar el sector.");
    }
}
// ✨ NUEVA FUNCIÓN: RESETEAR CLAVE A 12345678
async function resetearClave(usuarioId) {
    if (!confirm("¿Estás seguro de que deseas resetear la clave de este usuario a '12345678'?")) {
        return;
    }

    try {
        const res = await fetch(`/admin/usuarios/${usuarioId}/reset-password`, {
            method: "PUT",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`,
                "Content-Type": "application/json"
            }
        });

        if (res.ok) {
            const data = await res.json();
            alert("✅ " + data.mensaje);
        } else {
            const error = await res.json();
            alert("❌ Error: " + (error.detail || "No se pudo resetear la clave"));
        }
    } catch (error) {
        console.error("Error en el reseteo:", error);
        alert("❌ Error de conexión al intentar resetear la clave.");
    }
}

// ============================================================================
// LÓGICA DE UX PARA PERMISOS EN ÁRBOL
// ============================================================================

// Si tilda "Administrador", deshabilita y marca todo lo demás
function toggleAdmin(modo) {
    const isAdmin = document.getElementById(`${modo}-rol-admin`).checked;
    const checkboxes = document.querySelectorAll(`.check-rol-${modo}`);
    
    checkboxes.forEach(cb => {
        if (cb.value !== "Administrador" && cb.value !== "Operador") {
            cb.checked = isAdmin;
            cb.disabled = isAdmin; 
        }
    });
}

// Si tilda un Módulo padre, marca o desmarca todos sus hijos
function toggleModulo(modo, modulo) {
    const isChecked = document.getElementById(`${modo}-mod-${modulo}`).checked;
    const subRoles = document.querySelectorAll(`.sub-${modo}-${modulo}`);
    subRoles.forEach(cb => cb.checked = isChecked);
}

// Si tilda un hijo, automáticamente marca el Padre
function checkPadre(modo, modulo) {
    const subRolesChecked = document.querySelectorAll(`.sub-${modo}-${modulo}:checked`).length;
    const parentCheck = document.getElementById(`${modo}-mod-${modulo}`);
    
    if (subRolesChecked > 0) {
        parentCheck.checked = true;
    } else {
        parentCheck.checked = false;
    }
}




// ============================================================================
// ARRANQUE DE LA PÁGINA (INIT)
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    verificarAcceso(); 
    
    // 1. Si estamos en la vista de USUARIOS, cargamos la tabla y los sectores
    if (document.getElementById("tabla-usuarios")) {
        cargarUsuarios(); 
        cargarSectores(); 
    }
    
    // 2. Si estamos en la vista de AUDITORÍA, cargamos solo los logs
    if (document.getElementById("tabla-auditoria")) {
        cargarAuditoria();
    }
});

