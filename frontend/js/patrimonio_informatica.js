// ============================================================================
// patrimonio_informatica.js - LÓGICA DE LA TABLA DE INFORMÁTICA
// ============================================================================

const API_BASE = '/patrimonio';
let datosEnMemoria = [];
let configuracionActual = [];
let columnaOrden = null;
let ordenAscendente = true;

// Definición estricta de columnas según requerimiento
const configColumnas = {
    'PC': [
        { key: 'numero_inventario', label: 'N° Inventario' },
        { key: 'nombre_de_equipo', label: 'Nombre de Equipo' },
        { key: 'puesto', label: 'Puesto' },
        { key: 'usuario_destino_comb', label: 'Usuario/Destino' },
        { key: 'caract_pc', label: 'Caracteristicas' },
        { key: 'serie', label: 'Serie' },
        { key: 'monitor', label: 'Monitor' },
        { key: 'serie_monitor', label: 'Serie Monitor' },
        { key: 'numero_inventario_monitor', label: 'N° Inv. Monitor' },
        { key: 'acciones', label: 'Acciones' }
    ],
    'Notebook': [
        { key: 'numero_inventario', label: 'N° Inventario' },
        { key: 'usuario_destino_comb', label: 'Usuario/Destino' },
        { key: 'caract_nb', label: 'Caracteristicas' },
        { key: 'marca', label: 'Marca' },
        { key: 'modelo', label: 'Modelo' },
        { key: 'acciones', label: 'Acciones' }
    ],
    'Scanner': [
        { key: 'numero_inventario', label: 'N° Inventario' },
        { key: 'marca', label: 'Marca' },
        { key: 'modelo', label: 'Modelo' },
        { key: 'serie', label: 'Serie' },
        { key: 'usuario_destino_comb', label: 'Usuario/Destino' },
        { key: 'anio', label: 'Año' },
        { key: 'acciones', label: 'Acciones' }
    ],
    'Impresora': [
        { key: 'numero_inventario', label: 'N° Inventario' },
        { key: 'marca', label: 'Marca' },
        { key: 'modelo', label: 'Modelo' },
        { key: 'serie', label: 'Serie' },
        { key: 'usuario_destino_comb', label: 'Usuario/Destino' },
        { key: 'anio', label: 'Año' },
        { key: 'acciones', label: 'Acciones' }
    ],
    'Otros': [
        { key: 'numero_inventario', label: 'N° Inventario' },
        { key: 'descripcion_item', label: 'Descripción del item' },
        { key: 'descripcion_bien', label: 'Descripción del Bien' },
        { key: 'marca', label: 'Marca' },
        { key: 'modelo', label: 'Modelo' },
        { key: 'serie', label: 'Serie' },
        { key: 'usuario_destino_comb', label: 'Usuario/Destino' },
        { key: 'anio', label: 'Año' },
        { key: 'acciones', label: 'Acciones' }
    ]
};

// --- FETCH DE DATOS ---
async function cargarTiposOtros() {
    try {
        const res = await fetch(`${API_BASE}/informatica/tipos`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await res.json();
        
        const selectOtro = document.getElementById('select-tipo-otro');
        selectOtro.innerHTML = '<option value="OTROS_GENERAL">Todos los Otros</option>';
        data.tipos_otros.forEach(t => {
            selectOtro.innerHTML += `<option value="${escapeHTML(t)}">${escapeHTML(t)}</option>`;
        });
    } catch (err) { console.error("Error al cargar subtipos:", err); }
}

async function buscarYRenderizar(valorBusquedaBackend, grupoColumnas) {
    document.getElementById('contenedor-tabla').style.display = 'block';
    document.getElementById('titulo-tabla').style.display = 'block';
    document.getElementById('titulo-tabla').innerHTML = `Resultados para: ${grupoColumnas} <span style="font-size: 14px; color: #666; font-weight: normal; margin-left: 10px;">(Calculando...)</span>`;
    document.getElementById('tabla-body').innerHTML = '<tr><td colspan="15" style="text-align:center;">Buscando equipos...</td></tr>';

    try {
        const res = await fetch(`${API_BASE}?limit=1000&estado=Autorizado&tipo=${encodeURIComponent(valorBusquedaBackend)}`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await res.json();

        // Pre-procesamos los campos calculados
        datosEnMemoria = data.map(b => ({
            ...b,
            usuario_destino_comb: b.usuario_destino || b.usuario || '-',
            caract_pc: [b.procesador, b.motherboard, b.memoria, b.disco].filter(v => v && v.trim() !== '').join(' '),
            caract_nb: [b.procesador, b.memoria, b.disco].filter(v => v && v.trim() !== '').join(' ')
        }));

        configuracionActual = configColumnas[grupoColumnas];
        columnaOrden = null; // Reiniciamos el orden
        
        // ✨ AQUÍ INYECTAMOS EL TOTAL DE REGISTROS ✨
        document.getElementById('titulo-tabla').innerHTML = `Resultados para: <strong>${grupoColumnas}</strong> <span style="background-color: #e0e6e8; color: #1a3644; padding: 4px 10px; border-radius: 12px; font-size: 13px; font-weight: bold; margin-left: 10px;">Total: ${datosEnMemoria.length}</span>`;

        renderizarTabla();
    } catch (err) {
        console.error(err);
        document.getElementById('tabla-body').innerHTML = '<tr><td colspan="15" style="color:red; text-align:center;">Error al cargar datos.</td></tr>';
    }
}

// --- LÓGICA DE ORDENAMIENTO Y DIBUJADO ---
function ordenarDatos(key) {
    if (columnaOrden === key) {
        ordenAscendente = !ordenAscendente;
    } else {
        columnaOrden = key;
        ordenAscendente = true;
    }

    datosEnMemoria.sort((a, b) => {
        let valA = a[key] ? a[key].toString().toLowerCase().trim() : '';
        let valB = b[key] ? b[key].toString().toLowerCase().trim() : '';

        let numA = parseFloat(valA);
        let numB = parseFloat(valB);

        // Ordenamiento numérico si ambos son números válidos
        if (!isNaN(numA) && !isNaN(numB) && valA !== '' && valB !== '') {
            return ordenAscendente ? numA - numB : numB - numA;
        }
        
        // Ordenamiento alfabético
        if (valA < valB) return ordenAscendente ? -1 : 1;
        if (valA > valB) return ordenAscendente ? 1 : -1;
        return 0;
    });

    renderizarTabla();
}

function renderizarTabla() {
    const thead = document.getElementById('tabla-head');
    const tbody = document.getElementById('tabla-body');
    
    // 1. Dibujar Cabeceras (con las flechitas de orden)
    thead.innerHTML = '';
    const trHead = document.createElement('tr');
    
    configuracionActual.forEach(col => {
        const th = document.createElement('th');
        th.className = 'th-sortable';
        
        let flecha = '';
        if (columnaOrden === col.key) {
            flecha = ordenAscendente ? '<span>▲</span>' : '<span>▼</span>';
        }
        
        th.innerHTML = `${col.label} ${flecha}`;
        th.onclick = () => ordenarDatos(col.key);
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);

    // 2. Dibujar Filas
    tbody.innerHTML = '';
    if (datosEnMemoria.length === 0) {
        tbody.innerHTML = `<tr><td colspan="${configuracionActual.length}" style="text-align:center;">No se encontraron equipos de este tipo.</td></tr>`;
        return;
    }

    datosEnMemoria.forEach(bien => {
        const tr = document.createElement('tr');
        
        configuracionActual.forEach(col => {
            const td = document.createElement('td');
            let valor = bien[col.key] || '-';
            
            if (col.key === 'numero_inventario') {
                td.innerHTML = `<strong>${escapeHTML(valor)}</strong>`;
            } else if (col.key === 'acciones') {
                // ✨ AÑADIDO: Botón Asignar junto con Editar e Historial
                td.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <button class="btn-patrimonio" style="background-color: #007bff; font-size: 11px;" onclick="PatrimonioModulo.editarBien('${bien.numero_inventario}')">Editar</button>
                        <button class="btn-patrimonio" style="background-color: #17a2b8; font-size: 11px;" onclick="PatrimonioModulo.verHistorial('${bien.numero_inventario}')">Historial</button>
                        <button class="btn-patrimonio" style="background-color: #28a745; font-size: 11px;" onclick="abrirModalAsignar('${escapeHTML(bien.numero_inventario)}', '${escapeHTML(bien.usuario_id || '')}', '${escapeHTML(bien.puesto || '')}')">Asignar</button>
                    </div>
                `;
            } else {
                td.textContent = valor;
            }
            tr.appendChild(td);
        });
        
        tbody.appendChild(tr);
    });
}

// ============================================================================
// ✨ LÓGICA DE ASIGNACIÓN DE EQUIPOS (MODAL) ✨
// ============================================================================
let inventarioSeleccionado = null;

async function cargarUsuariosSelect() {
    const select = document.getElementById("asignar-usuario");
    try {
        const res = await fetch('/admin/usuarios', {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const usuarios = await res.json();
        
        select.innerHTML = '<option value="">-- Sin Asignar / Devolver a Stock --</option>';
        
        usuarios.forEach(u => {
            if(u.activo) {
                const option = document.createElement("option");
                option.value = u.id;
                option.textContent = `${u.nombre} ${u.apellido} (CUIL: ${u.cuil})`;
                select.appendChild(option);
            }
        });
    } catch (e) {
        console.error("Error cargando usuarios", e);
    }
}

async function abrirModalAsignar(numero_inventario, usuario_id_actual, puesto_actual) {
    inventarioSeleccionado = numero_inventario;
    document.getElementById("asignar-nro-inv").innerText = numero_inventario;
    
    await cargarUsuariosSelect();
    
    // Auto-completar con la info actual (si la tiene)
    document.getElementById("asignar-usuario").value = (usuario_id_actual && usuario_id_actual !== 'null') ? usuario_id_actual : "";
    document.getElementById("asignar-puesto").value = (puesto_actual && puesto_actual !== 'null') ? puesto_actual : "";
    
    document.getElementById("modal-asignar").style.display = "flex";
}

function cerrarModalAsignar() {
    document.getElementById("modal-asignar").style.display = "none";
    document.getElementById("form-asignar").reset();
    inventarioSeleccionado = null;
}

// ============================================================================
// ARRANQUE DE LA PÁGINA Y LISTENERS
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    
    const selectPrincipal = document.getElementById('select-tipo-principal');
    const selectOtro = document.getElementById('select-tipo-otro');

    if (selectPrincipal) {
        selectPrincipal.addEventListener('change', async (e) => {
            const tipo = e.target.value;
            const contenedorTabla = document.getElementById('contenedor-tabla');
            const tituloTabla = document.getElementById('titulo-tabla');

            if (!tipo) {
                contenedorTabla.style.display = 'none';
                tituloTabla.style.display = 'none';
                selectOtro.style.display = 'none';
                return;
            }

            if (tipo === 'Otros') {
                selectOtro.style.display = 'inline-block';
                await cargarTiposOtros();
                await buscarYRenderizar('OTROS_GENERAL', 'Otros');
            } else {
                selectOtro.style.display = 'none';
                selectOtro.value = 'OTROS_GENERAL'; 
                await buscarYRenderizar(tipo, tipo);
            }
        });
    }

    if (selectOtro) {
        selectOtro.addEventListener('change', async (e) => {
            const tipoEspecifico = e.target.value;
            await buscarYRenderizar(tipoEspecifico, 'Otros');
        });
    }

    // ✨ LISTENER PARA EL FORMULARIO DE ASIGNACIÓN ✨
    const formAsignar = document.getElementById("form-asignar");
    if (formAsignar) {
        formAsignar.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!inventarioSeleccionado) return;

            const datos = {
                usuario_id: document.getElementById("asignar-usuario").value ? parseInt(document.getElementById("asignar-usuario").value) : null,
                puesto: document.getElementById("asignar-puesto").value.trim() || null
            };

            const btnSubmit = formAsignar.querySelector('button[type="submit"]');
            const originalText = btnSubmit.textContent;
            btnSubmit.disabled = true;
            btnSubmit.textContent = "Guardando...";

            try {
                const response = await fetch(`${API_BASE}/${inventarioSeleccionado}/asignar`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify(datos)
                });

                if (response.ok) {
                    alert("Equipo asignado correctamente.");
                    cerrarModalAsignar();
                    
                    // Recargar la tabla actual automáticamente
                    if (selectPrincipal.value === 'Otros') {
                        buscarYRenderizar(selectOtro.value, 'Otros');
                    } else if (selectPrincipal.value) {
                        buscarYRenderizar(selectPrincipal.value, selectPrincipal.value);
                    }
                } else {
                    const err = await response.json();
                    alert("Error: " + err.detail);
                }
            } catch (error) {
                alert("Error de conexión al asignar.");
            } finally {
                btnSubmit.disabled = false;
                btnSubmit.textContent = originalText;
            }
        });
    }
});