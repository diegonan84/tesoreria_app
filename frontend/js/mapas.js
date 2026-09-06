// ============================================================================
// mapas.js - VISOR Y EDITOR DE PLANOS DE LA OFICINA
// ============================================================================

async function cargarListaMapas() {
    const res = await fetch('/mapas-disponibles', { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
    if (res.ok) {
        const mapas = await res.json();
        const select = document.getElementById("select-mapa");
        if (select) {
            select.innerHTML = mapas.map(m => `<option value="${escapeHTML(m.id)}">${escapeHTML(m.titulo)}</option>`).join('');
            if(mapas.length > 0) cargarMatriz(); // Carga el primer mapa automáticamente
        }
    }
}

async function cargarMatriz() {
    const mapaId = document.getElementById("select-mapa").value;
    if(!mapaId) return;

    const res = await fetch(`/mapa-puestos?mapa_id=${mapaId}`, { 
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } 
    });
    
    if (res.ok) {
        const data = await res.json();
        dibujarGrilla(data.estructura, data.puestos_data);
        dibujarObservaciones(data.observaciones);
    }
}

function dibujarGrilla(estructura, puestosData) {
    const grilla = document.getElementById("grilla-mapa");
    
    grilla.style.display = "grid";
    grilla.style.gridTemplateColumns = `repeat(${estructura.columnas}, 120px)`;
    grilla.style.gridTemplateRows = `repeat(${estructura.filas}, 120px)`;
    grilla.style.gap = "15px";
    grilla.style.justifyContent = "center";
    grilla.innerHTML = "";

    const infoPuestos = {};
    puestosData.forEach(p => infoPuestos[p.numero_puesto] = p);

    estructura.celdas.forEach(celda => {
        const div = document.createElement("div");

        if (!celda.habilitado) {
            div.style.visibility = "hidden";
            div.style.width = "120px";
            div.style.height = "120px";
        } else {
            const pData = infoPuestos[celda.numero_puesto] || { nombres_equipos: [], usuarios_asignados: [], colores: [], equipos_detalle: [] };
            
            div.className = "puesto-card";
            div.style.cssText = `width: 120px; height: 120px; display: flex; flex-direction: column; justify-content: center; background: #fff; border: 1px solid #d1d5db; border-radius: 8px; cursor: pointer; transition: transform 0.1s; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); transform: rotate(${celda.rotacion}deg);`;
            
            // ✨ NUEVO: Preparamos los datos técnicos y llamamos a la tarjeta
            const equiposEncoded = encodeURIComponent(JSON.stringify(pData.equipos_detalle || []));
            div.onclick = () => mostrarInfoPuesto(celda.numero_puesto, equiposEncoded);

            let estilosFondo = "background-color: #e5e7eb; border: 1px solid #9ca3af; color: #4b5563;";
            if (pData.colores.length === 1) estilosFondo = `background-color: ${pData.colores[0]}; border: 1px solid rgba(0,0,0,0.2); color: white; text-shadow: 0px 1px 2px rgba(0,0,0,0.4);`;
            else if (pData.colores.length > 1) {
                const pct = 100 / pData.colores.length;
                const stops = pData.colores.map((c, i) => `${c} ${i*pct}%, ${c} ${(i+1)*pct}%`).join(", ");
                estilosFondo = `background-image: linear-gradient(135deg, ${stops}); border: 1px solid rgba(0,0,0,0.2); color: white; text-shadow: 0px 1px 2px rgba(0,0,0,0.4);`;
            }

            const rotacionTexto = (celda.rotacion === 180) ? "rotate(180deg)" : "none";

            div.innerHTML = `
                <div style="font-size: 11px; font-weight: 700; color: #6b7280; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transform: ${rotacionTexto}; transition: transform 0.3s;">
                    ${escapeHTML(pData.nombres_equipos.join(" / ") || "Vacio")}
                </div>
                <div style="font-size: 16px; font-weight: 900; color: #111827; text-align: center; border-bottom: 1px solid #d1d5db; padding-bottom: 2px; width: 80%; margin: 0 auto; transform: ${rotacionTexto}; transition: transform 0.3s;">
                    ${escapeHTML(celda.numero_puesto)}
                </div>
                
                <div style="display: flex; justify-content: center; margin: 4px 0;">
                    <svg width="35" height="32" viewBox="0 0 100 90">
                        <rect x="25" y="5" width="50" height="25" rx="12" fill="#7f8384" stroke="#4b4f52" stroke-width="3"/>
                        <rect x="15" y="25" width="12" height="35" rx="6" fill="#7f8384" stroke="#4b4f52" stroke-width="3"/>
                        <rect x="73" y="25" width="12" height="35" rx="6" fill="#7f8384" stroke="#4b4f52" stroke-width="3"/>
                        <rect x="25" y="25" width="50" height="45" rx="8" fill="#7f8384" stroke="#4b4f52" stroke-width="3"/>
                    </svg>
                </div>

                <div style="margin: 0 auto; width: 90%; border-radius: 6px; min-height: 40px; display: flex; align-items: center; justify-content: center; text-align: center; ${estilosFondo}">
                    <span style="font-size: 10px; font-weight: bold; line-height: 1.1; padding: 2px; display: block; transform: ${rotacionTexto}; transition: transform 0.3s;">
                        ${pData.usuarios_asignados.map(u => escapeHTML(u)).join("<br>") || "---"}
                    </span>
                </div>
            `;
        }
        grilla.appendChild(div);
    });
}

function dibujarObservaciones(obs) {
    const panel = document.getElementById("panel-observaciones");
    const lista = document.getElementById("lista-observaciones");
    if (obs.length > 0) {
        lista.innerHTML = obs.map(o => `<div style="font-size: 11px; margin-bottom: 6px;">${escapeHTML(o)}</div>`).join('');
        panel.style.display = "block";
    } else {
        panel.style.display = "none";
    }
}

// ✨ NUEVO: Función para mostrar la tarjeta de detalles técnicos
function mostrarInfoPuesto(numero_puesto, equiposEncoded) {
    document.getElementById("info-puesto-id").innerText = numero_puesto;
    const contenedor = document.getElementById("info-puesto-contenido");
    contenedor.innerHTML = "";

    try {
        const equipos = JSON.parse(decodeURIComponent(equiposEncoded));

        if (!equipos || equipos.length === 0) {
            contenedor.innerHTML = `<p style="text-align: center; color: #888; font-style: italic; font-size: 14px;">No hay equipos informáticos asignados a este puesto.</p>`;
        } else {
            equipos.forEach((eq, index) => {
                contenedor.innerHTML += `
                    <div style="text-align: right; margin-bottom: 15px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
                        <div style="font-size: 20px; color: #333; margin-bottom: 4px;">${escapeHTML(eq.nombre || '')}</div>
                        <div style="font-size: 18px; color: #333; margin-bottom: 4px;">${escapeHTML(eq.marca || '')}</div>
                        <div style="font-size: 18px; color: #0056b3; margin-bottom: 4px;">${escapeHTML(eq.procesador || '')}</div>
                        <div style="font-size: 18px; color: #0056b3; margin-bottom: 4px;">${escapeHTML(eq.memoria || '')}</div>
                        <div style="font-size: 18px; color: #0056b3; margin-bottom: 4px;">${escapeHTML(eq.disco || '')}</div>
                    </div>
                    ${index < equipos.length - 1 ? '<hr style="border: 0; border-top: 1px dashed #ccc; margin: 15px 0;">' : ''}
                `;
            });
        }
        
        document.getElementById("modal-info-puesto").style.display = "flex";
    } catch (e) {
        console.error("Error al leer la información del equipo:", e);
    }
}

// --- FUNCIONES DE EXPORTACIÓN ---
function imprimirMapa() {
    window.print();
}

function exportarImagen(boton) {
    const elementoMapa = document.getElementById("grilla-mapa");
    const selectMapa = document.getElementById("select-mapa");
    const tituloMapa = selectMapa.options[selectMapa.selectedIndex].text;
    
    const btnOriginal = boton.innerHTML;
    boton.innerHTML = "⏳ Generando...";

    html2canvas(elementoMapa, {
        backgroundColor: "#f0f4f8", 
        scale: 2, 
        useCORS: true 
    }).then(canvas => {
        const enlace = document.createElement('a');
        enlace.download = `Mapa_${tituloMapa.replace(/\s+/g, '_')}.png`;
        enlace.href = canvas.toDataURL("image/png");
        enlace.click();
        
        boton.innerHTML = btnOriginal;
    }).catch(err => {
        console.error("Error al exportar la imagen:", err);
        alert("Hubo un problema al generar la imagen.");
        boton.innerHTML = btnOriginal;
    });
}

// ============================================================================
// LÓGICA DEL EDITOR DE MAPAS
// ============================================================================
let matrizDatos = []; 

const svgSilla = `
    <div style="display: flex; justify-content: center; margin: 4px 0;">
        <svg width="35" height="32" viewBox="0 0 100 90">
            <rect x="25" y="5" width="50" height="25" rx="12" fill="#7f8384" stroke="#4b4f52" stroke-width="3"/>
            <rect x="15" y="25" width="12" height="35" rx="6" fill="#7f8384" stroke="#4b4f52" stroke-width="3"/>
            <rect x="73" y="25" width="12" height="35" rx="6" fill="#7f8384" stroke="#4b4f52" stroke-width="3"/>
            <rect x="25" y="25" width="50" height="45" rx="8" fill="#7f8384" stroke="#4b4f52" stroke-width="3"/>
        </svg>
    </div>`;

async function cargarDesplegableMapas() {
    const res = await fetch('/mapas-disponibles', { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
    if (res.ok) {
        const mapas = await res.json();
        const select = document.getElementById("select-mapa-editar");
        select.innerHTML = '<option value="">-- Seleccione un mapa guardado --</option>' + mapas.map(m => `<option value="${escapeHTML(m.titulo)}">${escapeHTML(m.titulo)}</option>`).join('');
    }
}

async function cargarMapaSeleccionado() {
    const titulo = document.getElementById('select-mapa-editar').value;
    if(!titulo) return alert("Seleccione un mapa primero");

    const res = await fetch(`/editor-matriz/${encodeURIComponent(titulo)}`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }});
    if (res.ok) {
        const data = await res.json();
        if (data.existe) {
            const contenedor = document.getElementById('matriz-container');
            document.getElementById('mapa-titulo').value = data.titulo;
            document.getElementById('mapa-filas').value = data.filas;
            document.getElementById('mapa-cols').value = data.columnas;
            
            contenedor.style.gridTemplateColumns = `repeat(${data.columnas}, 120px)`;
            contenedor.style.gridTemplateRows = `repeat(${data.filas}, 120px)`;
            contenedor.innerHTML = '';
            matrizDatos = data.celdas;
            
            matrizDatos.forEach(c => dibujarCelda(c.fila, c.columna));
        }
    }
}

function prepararNuevoMapa() {
    document.getElementById('select-mapa-editar').value = "";
    document.getElementById('mapa-titulo').value = "";
    document.getElementById('mapa-filas').value = 4;
    document.getElementById('mapa-cols').value = 8;
    generarGrillaBase();
}

async function eliminarMapa() {
    const titulo = document.getElementById('select-mapa-editar').value;
    if(!titulo) return alert("Seleccione un mapa del desplegable para borrar.");
    if(!confirm(`¿Está seguro de eliminar todo el mapa "${titulo}" y sus puestos?`)) return;

    const res = await fetch(`/editor-matriz/borrar/${encodeURIComponent(titulo)}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });

    if(res.ok) {
        alert("Mapa eliminado correctamente.");
        prepararNuevoMapa();
        cargarDesplegableMapas();
    } else {
        alert("Error al eliminar el mapa.");
    }
}

function generarGrillaBase() {
    const contenedor = document.getElementById('matriz-container');
    const filas = parseInt(document.getElementById('mapa-filas').value);
    const cols = parseInt(document.getElementById('mapa-cols').value);
    
    contenedor.style.gridTemplateColumns = `repeat(${cols}, 120px)`;
    contenedor.style.gridTemplateRows = `repeat(${filas}, 120px)`;
    contenedor.innerHTML = '';
    matrizDatos = [];

    for (let f = 0; f < filas; f++) {
        for (let c = 0; c < cols; c++) {
            matrizDatos.push({ fila: f, columna: c, habilitado: false, numero_puesto: "", rotacion: 0 });
            dibujarCelda(f, c);
        }
    }
}

function dibujarCelda(f, c) {
    const contenedor = document.getElementById('matriz-container');
    const index = matrizDatos.findIndex(d => d.fila === f && d.columna === c);
    const data = matrizDatos[index];
    const div = document.createElement('div');
    div.id = `celda-${f}-${c}`;

    if (!data.habilitado) {
        div.className = 'celda-vacia';
        div.innerHTML = `<span style="color:#aaa; font-size:24px;">+</span>`;
        div.onclick = () => alternarCelda(f, c);
    } else {
        div.className = 'celda-activa';
        div.style.transform = `rotate(${data.rotacion}deg)`;
        
        const rotacionTexto = (data.rotacion === 180) ? "rotate(180deg)" : "none";

        div.innerHTML = `
            <div class="controles-edicion" style="transform: translate(-50%, -50%) rotate(-${data.rotacion}deg);">
                <button class="btn-mini" onclick="rotarCelda(${f}, ${c})" title="Girar 90°">↻</button>
                <button class="btn-mini" style="color:red;" onclick="alternarCelda(${f}, ${c})" title="Quitar Puesto">X</button>
            </div>
            
            <div style="font-size: 11px; font-weight: 700; color: #6b7280; text-align: center; margin-top: 6px; transform: ${rotacionTexto}; transition: transform 0.3s;">
                Vacío
            </div>

            <div style="border-bottom: 1px solid #d1d5db; width: 80%; margin: 0 auto 2px auto; padding-bottom: 2px; transform: ${rotacionTexto}; transition: transform 0.3s;">
                <input type="text" value="${escapeHTML(data.numero_puesto)}" placeholder="ID" onchange="actualizarNumero(${f}, ${c}, this.value)" 
                    style="width: 100%; text-align: center; font-size: 16px; font-weight: 900; border: none; outline: none; background: transparent;">
            </div>
            
            ${svgSilla}
            <div class="mesa-falsa"></div>
        `;
    }
    
    const existente = document.getElementById(`celda-${f}-${c}`);
    if (existente) contenedor.replaceChild(div, existente);
    else contenedor.appendChild(div);
}

function alternarCelda(f, c) {
    const index = matrizDatos.findIndex(d => d.fila === f && d.columna === c);
    matrizDatos[index].habilitado = !matrizDatos[index].habilitado;
    if(!matrizDatos[index].habilitado) { matrizDatos[index].numero_puesto = ""; matrizDatos[index].rotacion = 0; }
    dibujarCelda(f, c);
}

function rotarCelda(f, c) {
    const index = matrizDatos.findIndex(d => d.fila === f && d.columna === c);
    matrizDatos[index].rotacion = (matrizDatos[index].rotacion + 90) % 360;
    dibujarCelda(f, c);
}

function actualizarNumero(f, c, valor) {
    const index = matrizDatos.findIndex(d => d.fila === f && d.columna === c);
    matrizDatos[index].numero_puesto = valor;
}

async function guardarMapaCompleto() {
    const payload = {
        titulo: document.getElementById('mapa-titulo').value.trim(),
        filas: parseInt(document.getElementById('mapa-filas').value),
        columnas: parseInt(document.getElementById('mapa-cols').value),
        celdas: matrizDatos
    };

    if(!payload.titulo) return alert("El título del mapa es obligatorio.");

    const res = await fetch('/editor-matriz/guardar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        alert("✅ Mapa guardado exitosamente.");
        cargarDesplegableMapas(); 
    } else {
        alert("Error al guardar el mapa.");
    }
}

async function exportarBackup() {
    try {
        const res = await fetch('/editor-matriz/backup/exportar', { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } });
        if (res.ok) {
            const data = await res.json();
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
            const enlace = document.createElement('a');
            enlace.setAttribute("href", dataStr);
            enlace.setAttribute("download", "backup_mapas_tesoreria.json"); 
            document.body.appendChild(enlace);
            enlace.click();
            enlace.remove();
        } else {
            alert("Error al intentar exportar los mapas.");
        }
    } catch (error) {
        console.error(error);
        alert("Error de conexión al exportar.");
    }
}

function importarBackup(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            const contenido = JSON.parse(e.target.result); 
            if(!confirm(`¿Desea importar ${contenido.length} mapas? ATENCIÓN: Los mapas con el mismo nombre serán reemplazados por los del archivo.`)) {
                document.getElementById('file-import').value = ""; 
                return;
            }

            const res = await fetch('/editor-matriz/backup/importar', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(contenido)
            });

            if (res.ok) {
                const data = await res.json();
                alert("✅ " + data.mensaje);
                cargarDesplegableMapas(); 
                document.getElementById('file-import').value = ""; 
            } else {
                alert("Hubo un error del servidor. Verifique que el archivo sea un backup válido.");
            }
        } catch (error) {
            console.error("Error al leer/importar archivo:", error);
            alert("❌ El archivo seleccionado está corrupto o no es un JSON válido.");
        }
    };
    reader.readAsText(file);
}

// --- EXPORTAR UN SOLO MAPA ---
async function exportarMapaUnico() {
    const tituloMapa = document.getElementById('mapa-titulo').value.trim();
    if (!tituloMapa) return alert("Primero debes cargar o crear un mapa para exportarlo.");
    
    try {
        const res = await fetch(`/editor-matriz/exportar/${encodeURIComponent(tituloMapa)}`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (!res.ok) throw new Error("No se pudo exportar el mapa");
        
        const data = await res.json();
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const enlace = document.createElement("a");
        enlace.href = url;
        enlace.download = `Plano_${tituloMapa.replace(/\s+/g, '_')}.json`; 
        enlace.click();
        URL.revokeObjectURL(url);
        
    } catch (error) {
        alert("Error al intentar exportar el plano.");
    }
}

// --- IMPORTAR UN SOLO MAPA (Con lógica de reemplazo) ---
async function importarMapaUnico(event, intentarReemplazar = false) {
    const file = event.target ? event.target.files[0] : event; 
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("reemplazar", intentarReemplazar);

    try {
        const res = await fetch('/editor-matriz/importar-unico', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
            body: formData
        });

        if (res.status === 409) {
            const error = await res.json();
            const confirmar = confirm(error.detail + "\n\n¿Deseas reemplazar el plano existente en el sistema con este archivo?");
            
            if (confirmar) {
                importarMapaUnico(file, true);
            } else {
                if (document.getElementById('input-importar-unico')) {
                    document.getElementById('input-importar-unico').value = '';
                }
            }
            return;
        }

        const data = await res.json();
        
        if (res.ok) {
            alert("✅ " + data.mensaje);
            if (typeof cargarDesplegableMapas === 'function') cargarDesplegableMapas();
            if (data.titulo_importado) {
                document.getElementById('select-mapa-editar').value = data.titulo_importado;
                cargarMapaSeleccionado();
            }
        } else {
            alert("❌ Error: " + data.detail);
        }
    } catch (error) {
        console.error(error);
        alert("Error de conexión al importar.");
    } finally {
        if (!intentarReemplazar && event.target) {
            event.target.value = '';
        }
    }
}

// ============================================================================
// ARRANQUE DE LA PÁGINA (VISOR Y EDITOR)
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    verificarAcceso();

    // 1. Si estamos en el VISOR DE MAPA
    if (document.getElementById("select-mapa")) {
        cargarListaMapas();
    }

    // 2. Si estamos en el EDITOR DE MAPA
    if (document.getElementById("select-mapa-editar")) {
        cargarDesplegableMapas();
        generarGrillaBase();
    }
});