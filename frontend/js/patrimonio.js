/* ==================================================
   MÓDULO PATRIMONIO - LÓGICA FRONTEND
   ================================================== */

const PatrimonioModulo = (function() {
    
    // Variables privadas
    let jwtToken = localStorage.getItem('token'); 
    const API_BASE_URL = '/patrimonio';

    // --- VARIABLES DE PAGINACIÓN ---
    let paginaActual = 0;
    const LIMITE_POR_PAGINA = 50;
    let totalPaginas = 1;
    // --- VARIABLES DE ORDENAMIENTO Y MEMORIA ---
    let columnaOrden = 'numero_inventario';
    let ordenAscendente = true;
    let bienesActuales = []; // Guardamos los bienes en memoria para el modal

    // Configuración base para fetch
    const getFetchHeaders = () => {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${jwtToken}`
        };
    };

    // --- LÓGICA: CALCULAR TOTAL DE PÁGINAS Y MOSTRAR BADGE ---
    const cargarTotalPaginas = async () => {
        try {
            const inputBusqueda = document.getElementById('input-busqueda');
            const inputDesde = document.getElementById('input-desde');
            const inputHasta = document.getElementById('input-hasta');
            const inputAnio = document.getElementById('input-anio');
            const inputRubro = document.getElementById('input-rubro');
            const badgeTotal = document.getElementById('badge-total-registros');

            const busquedaQuery = inputBusqueda && inputBusqueda.value.trim() ? `&busqueda=${encodeURIComponent(inputBusqueda.value.trim())}` : '';
            const desdeQuery = inputDesde && inputDesde.value.trim() ? `&desde=${encodeURIComponent(inputDesde.value.trim())}` : '';
            const hastaQuery = inputHasta && inputHasta.value.trim() ? `&hasta=${encodeURIComponent(inputHasta.value.trim())}` : '';
            const anioQuery = inputAnio && inputAnio.value.trim() ? `&anio=${encodeURIComponent(inputAnio.value.trim())}` : '';
            const rubroQuery = inputRubro && inputRubro.value.trim() ? `&rubro=${encodeURIComponent(inputRubro.value.trim())}` : '';

            if (badgeTotal) {
                badgeTotal.style.display = 'inline-block';
                badgeTotal.innerText = 'Calculando...';
            }

            const response = await fetch(`${API_BASE_URL}/total?estado=Autorizado${busquedaQuery}${desdeQuery}${hastaQuery}${anioQuery}${rubroQuery}`, {
                method: 'GET',
                headers: getFetchHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                const totalRegistros = data.total;
                totalPaginas = Math.ceil(totalRegistros / LIMITE_POR_PAGINA) || 1;
                
                if (badgeTotal) badgeTotal.innerHTML = `Total: ${totalRegistros}`;
            } else {
                if (badgeTotal) badgeTotal.innerText = 'Total: Error';
            }
        } catch (error) {
            console.error('Error al obtener el total de registros:', error);
            const badgeTotal = document.getElementById('badge-total-registros');
            if (badgeTotal) badgeTotal.innerText = 'Total: Error';
        }
    };

    // --- LÓGICA: ACTUALIZAR BOTONES DE PÁGINA ---
    const actualizarControlesPaginacion = () => {
        const btnFirst = document.getElementById('btn-first-page');
        const btnPrev = document.getElementById('btn-prev-page');
        const btnNext = document.getElementById('btn-next-page');
        const btnLast = document.getElementById('btn-last-page');
        const pageInfo = document.getElementById('page-info');

        if (btnFirst && btnPrev && btnNext && btnLast && pageInfo) {
            pageInfo.textContent = `Página ${paginaActual + 1} de ${totalPaginas}`;
            
            const puedeRetroceder = paginaActual > 0;
            btnFirst.disabled = !puedeRetroceder;
            btnPrev.disabled = !puedeRetroceder;
            
            const puedeAvanzar = paginaActual < (totalPaginas - 1);
            btnNext.disabled = !puedeAvanzar;
            btnLast.disabled = !puedeAvanzar;
        }
    };

    const inicializarPaginacion = () => {
        const btnFirst = document.getElementById('btn-first-page');
        const btnPrev = document.getElementById('btn-prev-page');
        const btnNext = document.getElementById('btn-next-page');
        const btnLast = document.getElementById('btn-last-page');

        if (btnFirst && btnPrev && btnNext && btnLast) {
            btnFirst.addEventListener('click', () => { if (paginaActual > 0) { paginaActual = 0; cargarInventario(); } });
            btnPrev.addEventListener('click', () => { if (paginaActual > 0) { paginaActual--; cargarInventario(); } });
            btnNext.addEventListener('click', () => { if (paginaActual < (totalPaginas - 1)) { paginaActual++; cargarInventario(); } });
            btnLast.addEventListener('click', () => { if (paginaActual < (totalPaginas - 1)) { paginaActual = totalPaginas - 1; cargarInventario(); } });
        }
    };

    // --- LÓGICA: CARGAR INVENTARIO (TABLA) ---
    const cargarInventario = async () => {
        try {
            const tbody = document.getElementById('tabla-patrimonio-body');
            if (!tbody) return; 

            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">Cargando inventario...</td></tr>';

            await cargarTotalPaginas();
            
            const chkTodos = document.getElementById('chk-seleccionar-todos');
            if (chkTodos) chkTodos.checked = false;

            const skip = paginaActual * LIMITE_POR_PAGINA;
            const inputBusqueda = document.getElementById('input-busqueda');
            const inputDesde = document.getElementById('input-desde');
            const inputHasta = document.getElementById('input-hasta');
            const inputAnio = document.getElementById('input-anio');
            const inputRubro = document.getElementById('input-rubro');

            const busquedaQuery = inputBusqueda && inputBusqueda.value.trim() ? `&busqueda=${encodeURIComponent(inputBusqueda.value.trim())}` : '';
            const desdeQuery = inputDesde && inputDesde.value.trim() ? `&desde=${encodeURIComponent(inputDesde.value.trim())}` : '';
            const hastaQuery = inputHasta && inputHasta.value.trim() ? `&hasta=${encodeURIComponent(inputHasta.value.trim())}` : '';
            const anioQuery = inputAnio && inputAnio.value.trim() ? `&anio=${encodeURIComponent(inputAnio.value.trim())}` : '';
            const rubroQuery = inputRubro && inputRubro.value.trim() ? `&rubro=${encodeURIComponent(inputRubro.value.trim())}` : '';

            const ordenQuery = `&sort_by=${columnaOrden}&orden=${ordenAscendente ? 'asc' : 'desc'}`;

            const response = await fetch(`${API_BASE_URL}?skip=${skip}&limit=${LIMITE_POR_PAGINA}&estado=Autorizado${busquedaQuery}${desdeQuery}${hastaQuery}${anioQuery}${rubroQuery}${ordenQuery}`, {
                method: 'GET',
                headers: getFetchHeaders()
            });

            if (!response.ok) throw new Error('Error al obtener los datos');

            const data = await response.json();
            renderizarTabla(data);
            actualizarControlesPaginacion();

        } catch (error) {
            console.error('Error:', error);
            alert('Error al cargar el inventario de patrimonio.');
        }
    };

    const renderizarTabla = (bienes) => {
        bienesActuales = bienes;
        const tbody = document.getElementById('tabla-patrimonio-body');
        tbody.innerHTML = '';

        if (bienes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No se encontraron bienes.</td></tr>';
            return;
        }

        bienes.forEach(bien => {
            const formatearMonto = (monto) => {
                if (monto === null || monto === undefined) return '-';
                return `$ ${parseFloat(monto).toLocaleString('es-AR')}`;
            };

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="text-align: center;">
                    <input type="checkbox" class="chk-imprimir" value="${bien.numero_inventario}" style="cursor: pointer; width: 16px; height: 16px;">
                </td>
                <td><strong>${escapeHTML(bien.numero_inventario)}</strong></td>
                <td>${escapeHTML(bien.rubro_patrimonial_numero) || '-'}</td>
                <td>${escapeHTML(bien.rubro_patrimonial_descripcion) || '-'}</td>
                <td>${escapeHTML(bien.descripcion_bien || bien.descripcion_item || '-')}</td>
                
                <td style="text-align: center; font-weight: bold;">${escapeHTML(bien.anio || '-')}</td>
                
                <td>${formatearMonto(bien.monto_original)}</td>
                <td>${formatearMonto(bien.monto_residual)}</td>
                <td>
                    <button class="btn-patrimonio" style="background-color: #17a2b8; margin-bottom: 4px;" onclick="PatrimonioModulo.verDetalles('${escapeHTML(bien.numero_inventario)}')">Detalles</button><br>
                    <button class="btn-patrimonio" onclick="PatrimonioModulo.editarBien('${escapeHTML(bien.numero_inventario)}')">Editar</button>
                    <button class="btn-patrimonio" onclick="PatrimonioModulo.verHistorial('${escapeHTML(bien.numero_inventario)}')">Historial</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    };

    // --- LÓGICA: MODAL DETALLES ---
    const verDetalles = (nro_inventario) => {
        const bien = bienesActuales.find(b => b.numero_inventario === nro_inventario);
        const texto = (bien && bien.descripcion_detallada) ? bien.descripcion_detallada : 'No hay descripción detallada registrada para este bien.';
        document.getElementById('texto-detalles').textContent = texto;
        document.getElementById('modal-detalles').style.display = 'flex';
    };

    const cerrarDetalles = () => {
        document.getElementById('modal-detalles').style.display = 'none';
    };

    // --- LÓGICA: CARGAR DESPLEGABLE DE AÑOS ---
    const cargarAniosDropdown = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/anios/disponibles`, {
                method: 'GET',
                headers: getFetchHeaders()
            });
            if (response.ok) {
                const data = await response.json();
                const selectAnio = document.getElementById('input-anio');
                if (selectAnio && data.anios) {
                    data.anios.forEach(anio => {
                        selectAnio.innerHTML += `<option value="${escapeHTML(anio)}">${escapeHTML(anio)}</option>`;
                    });
                }
            }
        } catch (error) {
            console.error("Error cargando la lista de años:", error);
        }
    };

    // --- LÓGICA: CARGAR DESPLEGABLE DE RUBROS ---
    const cargarRubrosDropdown = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/rubros/disponibles`, {
                method: 'GET',
                headers: getFetchHeaders()
            });
            if (response.ok) {
                const data = await response.json();
                const selectRubro = document.getElementById('input-rubro');
                if (selectRubro && data.rubros) {
                    data.rubros.forEach(rubro => {
                        const label = rubro.descripcion ? `${rubro.numero} - ${rubro.descripcion}` : rubro.numero;
                        selectRubro.innerHTML += `<option value="${escapeHTML(rubro.numero)}">${escapeHTML(label)}</option>`;
                    });
                }
            }
        } catch (error) {
            console.error("Error cargando la lista de rubros:", error);
        }
    };

    // --- LÓGICA: BUSCADOR ---
    const inicializarBuscador = () => {
        const btnBuscar = document.getElementById('btn-buscar');
        const btnLimpiar = document.getElementById('btn-limpiar');
        const inputBusqueda = document.getElementById('input-busqueda');
        const inputDesde = document.getElementById('input-desde');
        const inputHasta = document.getElementById('input-hasta');
        const inputAnio = document.getElementById('input-anio'); 
        const inputRubro = document.getElementById('input-rubro');

        if (btnBuscar && btnLimpiar) {
            btnBuscar.addEventListener('click', () => { paginaActual = 0; cargarInventario(); });
            
            if(inputBusqueda) inputBusqueda.addEventListener('keypress', (e) => { if (e.key === 'Enter') { paginaActual = 0; cargarInventario(); } });
            if(inputDesde) inputDesde.addEventListener('keypress', (e) => { if (e.key === 'Enter') { paginaActual = 0; cargarInventario(); } });
            if(inputHasta) inputHasta.addEventListener('keypress', (e) => { if (e.key === 'Enter') { paginaActual = 0; cargarInventario(); } });
            
            if(inputAnio) inputAnio.addEventListener('change', () => { paginaActual = 0; cargarInventario(); }); 
            if(inputRubro) inputRubro.addEventListener('change', () => { paginaActual = 0; cargarInventario(); });
            
            btnLimpiar.addEventListener('click', () => { 
                if (inputBusqueda) inputBusqueda.value = ''; 
                if (inputDesde) inputDesde.value = ''; 
                if (inputHasta) inputHasta.value = ''; 
                if (inputAnio) inputAnio.value = ''; 
                if (inputRubro) inputRubro.value = '';
                paginaActual = 0; 
                cargarInventario(); 
            });
        }
    };

    // --- LÓGICA: EXPORTAR EXCEL ---
    const inicializarExportacion = () => {
        const btnExportar = document.getElementById('btn-exportar-excel');
        if (!btnExportar) return;

        btnExportar.addEventListener('click', async () => {
            try {
                btnExportar.disabled = true;
                btnExportar.textContent = 'Generando...';

                const inputBusqueda = document.getElementById('input-busqueda');
                const inputDesde = document.getElementById('input-desde');
                const inputHasta = document.getElementById('input-hasta');
                const inputAnio = document.getElementById('input-anio');
                const inputRubro = document.getElementById('input-rubro');

                const params = new URLSearchParams();
                if (inputBusqueda && inputBusqueda.value.trim()) params.set('busqueda', inputBusqueda.value.trim());
                if (inputDesde && inputDesde.value.trim()) params.set('desde', inputDesde.value.trim());
                if (inputHasta && inputHasta.value.trim()) params.set('hasta', inputHasta.value.trim());
                if (inputAnio && inputAnio.value.trim()) params.set('anio', inputAnio.value.trim());
                if (inputRubro && inputRubro.value.trim()) params.set('rubro', inputRubro.value.trim());

                const queryString = params.toString();
                const url = `${API_BASE_URL}/exportar/excel${queryString ? '?' + queryString : ''}`;

                const response = await fetch(url, {
                    method: 'GET',
                    headers: { 'Authorization': `Bearer ${jwtToken}` }
                });

                if (!response.ok) throw new Error('Error al generar el Excel');

                const blob = await response.blob();
                const blobUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = blobUrl;
                
                let filename = 'Inventario.xlsx';
                const disposition = response.headers.get('content-disposition');
                if (disposition && disposition.indexOf('filename=') !== -1) {
                    const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
                    if (matches != null && matches[1]) { 
                        filename = matches[1].replace(/['"]/g, '');
                    }
                }

                a.download = filename;
                document.body.appendChild(a);
                a.click();
                
                window.URL.revokeObjectURL(blobUrl);
                document.body.removeChild(a);

            } catch (error) {
                console.error('Error:', error);
                alert(`Hubo un error al exportar el archivo: ${error.message}`);
            } finally {
                btnExportar.disabled = false;
                btnExportar.textContent = 'Exportar Excel';
            }
        });
    };

    // --- LÓGICA: IMPORTACIÓN DE EXCEL ORIGINAL ---
    const inicializarImportacion = () => {
        const btnImportar = document.getElementById('btn-importar-excel');
        const inputFile = document.getElementById('input-file-excel');

        if (!btnImportar || !inputFile) return;

        btnImportar.addEventListener('click', () => { inputFile.click(); });

        inputFile.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                btnImportar.disabled = true;
                btnImportar.textContent = 'Importando...';

                const response = await fetch(`${API_BASE_URL}/importar`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${jwtToken}` },
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Error al importar el archivo');
                }

                const result = await response.json();
                alert(`${result.mensaje}\nNuevos: ${result.resumen.nuevos_creados}\nActualizados: ${result.resumen.bienes_actualizados}\nTransferidos (Faltantes): ${result.resumen.bienes_transferidos}\nOmitidos: ${result.resumen.omitidos_o_sin_cambios}`);
                
                paginaActual = 0;
                cargarInventario();

            } catch (error) {
                console.error('Error:', error);
                alert(`Hubo un error en la importación: ${error.message}`);
            } finally {
                btnImportar.disabled = false;
                btnImportar.textContent = 'Importar Excel Todos'; 
                inputFile.value = ''; 
            }
        });
    };

    // --- LÓGICA: IMPORTACIÓN AÑO / DETALLES ---
    const inicializarImportacionAnio = () => {
        const btnImportarAnio = document.getElementById('btn-importar-anio');
        const inputFileAnio = document.getElementById('input-file-anio');

        if (!btnImportarAnio || !inputFileAnio) return;

        btnImportarAnio.addEventListener('click', () => { inputFileAnio.click(); });

        inputFileAnio.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                btnImportarAnio.disabled = true;
                btnImportarAnio.textContent = 'Procesando...';

                const response = await fetch(`${API_BASE_URL}/importar-anio`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${jwtToken}` },
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Error al procesar el archivo');
                }

                const result = await response.json();
                alert(`${result.mensaje}\nBienes actualizados: ${result.actualizados}\nFilas omitidas o no encontradas: ${result.omitidos}`);
                
                cargarInventario();

            } catch (error) {
                console.error('Error:', error);
                alert(`Hubo un error en la actualización: ${error.message}`);
            } finally {
                btnImportarAnio.disabled = false;
                btnImportarAnio.textContent = 'Importar Excel Año/Detalles';
                inputFileAnio.value = ''; 
            }
        });
    };

    // --- ✨ LÓGICA: IMPORTACIÓN EXCEL INFORMÁTICA (Múltiples hojas) ✨ ---
    const inicializarImportacionInformatica = () => {
        const btnImportarInfo = document.getElementById('btn-importar-informatica');
        const inputFileInfo = document.getElementById('input-file-informatica');

        if (!btnImportarInfo || !inputFileInfo) return;

        btnImportarInfo.addEventListener('click', () => { inputFileInfo.click(); });

        inputFileInfo.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                btnImportarInfo.disabled = true;
                btnImportarInfo.textContent = 'Procesando...';

                const response = await fetch(`${API_BASE_URL}/importar-informatica`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${jwtToken}` },
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Error al procesar el archivo informático');
                }

                const result = await response.json();
                alert(`${result.mensaje}\nNuevos: ${result.resumen.nuevos_creados}\nActualizados: ${result.resumen.bienes_actualizados}\nOmitidos/Vacíos: ${result.resumen.omitidos_o_sin_cambios}`);
                
                paginaActual = 0;
                cargarInventario();

            } catch (error) {
                console.error('Error:', error);
                alert(`Hubo un error en la actualización: ${error.message}`);
            } finally {
                btnImportarInfo.disabled = false;
                btnImportarInfo.textContent = 'Importar Informática (DGTES)';
                inputFileInfo.value = ''; 
            }
        });
    };

    // --- LÓGICA: IMPRESIÓN DE ETIQUETAS ---
    const inicializarImpresion = () => {
        const btnImprimir = document.getElementById('btn-imprimir-seleccion');
        if (!btnImprimir) return;

        btnImprimir.addEventListener('click', () => {
            const checkboxes = document.querySelectorAll('.chk-imprimir:checked');
            
            if (checkboxes.length === 0) {
                alert("Por favor, selecciona al menos un equipo para imprimir.");
                return;
            }

            const numerosSeleccionados = Array.from(checkboxes).map(chk => chk.value);
            const numerosQuery = numerosSeleccionados.join(',');
            
            window.open(`/patrimonio-imprimir?numeros=${numerosQuery}`, '_blank');
        });
    };

    // --- UTILIDAD PARA FORMULARIOS ---
    const obtenerValorFormulario = (id) => {
        const elemento = document.getElementById(id);
        if (!elemento) return null;
        const valor = elemento.value.trim();
        return valor === '' ? null : valor;
    };

    // --- LÓGICA: ALTA DE BIEN ---
    const inicializarFormularioNuevo = () => {
        const form = document.getElementById('form-nuevo-bien');
        if (!form) return; 

        form.addEventListener('submit', async (e) => {
            e.preventDefault(); 
            
            const mensajeDiv = document.getElementById('mensaje-form');
            const botonSubmit = form.querySelector('button[type="submit"]');

            const elemInventario = document.getElementById('numero_inventario');
            const elemCantidad = document.getElementById('cantidad');

            const nuevoBien = {
                numero_inventario: elemInventario ? elemInventario.value.trim() : "",
                cantidad: elemCantidad ? (parseInt(elemCantidad.value) || 1) : 1,
                institucional: obtenerValorFormulario('institucional'),
                cuenta: obtenerValorFormulario('cuenta'),
                rubro_patrimonial_numero: obtenerValorFormulario('rubro_patrimonial_numero'),
                rubro_patrimonial_descripcion: obtenerValorFormulario('rubro_patrimonial_descripcion'),
                estado: obtenerValorFormulario('estado'),
                numero_migrado: obtenerValorFormulario('numero_migrado'),
                descripcion_item: obtenerValorFormulario('descripcion_item'),
                descripcion_bien: obtenerValorFormulario('descripcion_bien'),
                descripcion_detallada: obtenerValorFormulario('descripcion_detallada'),
                marca: obtenerValorFormulario('marca'),
                modelo: obtenerValorFormulario('modelo'),
                serie: obtenerValorFormulario('serie'),
                anio: obtenerValorFormulario('anio'),
                reparticion: obtenerValorFormulario('reparticion'),
                usuario: obtenerValorFormulario('usuario'), 
                observaciones: obtenerValorFormulario('observaciones'),
                monto_original: obtenerValorFormulario('monto_original'),
                monto_actualizado: obtenerValorFormulario('monto_actualizado'),
                monto_residual: obtenerValorFormulario('monto_residual'),
                
                usuario_destino: obtenerValorFormulario('usuario_destino'), 
                tipo: obtenerValorFormulario('tipo'),
                nombre_de_equipo: obtenerValorFormulario('nombre_de_equipo'),
                puesto: obtenerValorFormulario('puesto'),
                procesador: obtenerValorFormulario('procesador'),
                motherboard: obtenerValorFormulario('motherboard'),
                memoria: obtenerValorFormulario('memoria'),
                disco: obtenerValorFormulario('disco'),
                monitor: obtenerValorFormulario('monitor'),
                serie_monitor: obtenerValorFormulario('serie_monitor'),
                numero_inventario_monitor: obtenerValorFormulario('numero_inventario_monitor')
            };

            try {
                botonSubmit.disabled = true;
                botonSubmit.textContent = 'Guardando...';
                
                const response = await fetch(API_BASE_URL, {
                    method: 'POST',
                    headers: getFetchHeaders(),
                    body: JSON.stringify(nuevoBien)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    let msjError = 'Error al guardar';
                    if (Array.isArray(errorData.detail)) {
                        msjError = errorData.detail.map(err => `Campo '${err.loc[err.loc.length-1]}': ${err.msg}`).join(' | ');
                    } else if (errorData.detail) {
                        msjError = errorData.detail; 
                    }
                    throw new Error(msjError);
                }

                mensajeDiv.style.display = 'block';
                mensajeDiv.style.backgroundColor = '#d4edda';
                mensajeDiv.style.color = '#155724';
                mensajeDiv.textContent = '¡Bien patrimonial registrado con éxito!';
                form.reset();

                setTimeout(() => { window.location.href = '/patrimonio-vista'; }, 1500);

            } catch (error) {
                mensajeDiv.style.display = 'block';
                mensajeDiv.style.backgroundColor = '#f8d7da';
                mensajeDiv.style.color = '#721c24';
                mensajeDiv.textContent = error.message;
            } finally {
                botonSubmit.disabled = false;
                botonSubmit.textContent = 'Guardar Bien';
            }
        });
    };

    // --- LÓGICA: EDICIÓN DE BIEN ---
    const inicializarFormularioEdicion = async () => {
        const form = document.getElementById('form-editar-bien');
        if (!form) return; 

        const urlParams = new URLSearchParams(window.location.search);
        const numero = urlParams.get('numero');

        if (!numero) {
            alert("No se especificó un número de inventario válido.");
            window.location.href = '/patrimonio-vista';
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/${numero}`, {
                method: 'GET',
                headers: getFetchHeaders()
            });

            if (!response.ok) throw new Error("Error al cargar los datos del bien.");
            
            const bien = await response.json();

            const setValor = (id, valor) => {
                const el = document.getElementById(id);
                if (el && valor !== null && valor !== undefined) el.value = valor;
            };

            setValor('numero_inventario', bien.numero_inventario);
            setValor('institucional', bien.institucional);
            setValor('cuenta', bien.cuenta);
            setValor('rubro_patrimonial_numero', bien.rubro_patrimonial_numero);
            setValor('rubro_patrimonial_descripcion', bien.rubro_patrimonial_descripcion);
            setValor('estado', bien.estado);
            setValor('numero_migrado', bien.numero_migrado);
            setValor('descripcion_item', bien.descripcion_item);
            setValor('descripcion_bien', bien.descripcion_bien);
            setValor('descripcion_detallada', bien.descripcion_detallada);
            setValor('marca', bien.marca);
            setValor('modelo', bien.modelo);
            setValor('serie', bien.serie);
            setValor('anio', bien.anio);
            setValor('reparticion', bien.reparticion);
            setValor('usuario', bien.usuario);
            setValor('observaciones', bien.observaciones);
            setValor('monto_original', bien.monto_original);
            setValor('monto_actualizado', bien.monto_actualizado);
            setValor('monto_residual', bien.monto_residual);
            
            setValor('usuario_destino', bien.usuario_destino);
            setValor('tipo', bien.tipo);
            setValor('nombre_de_equipo', bien.nombre_de_equipo);
            setValor('puesto', bien.puesto);
            setValor('procesador', bien.procesador);
            setValor('motherboard', bien.motherboard);
            setValor('memoria', bien.memoria);
            setValor('disco', bien.disco);
            setValor('monitor', bien.monitor);
            setValor('serie_monitor', bien.serie_monitor);
            setValor('numero_inventario_monitor', bien.numero_inventario_monitor);

            form.style.display = 'block';

        } catch (error) {
            alert(error.message);
            window.location.href = '/patrimonio-vista';
            return;
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const mensajeDiv = document.getElementById('mensaje-form');
            const botonSubmit = form.querySelector('button[type="submit"]');

            const datosActualizados = {
                institucional: obtenerValorFormulario('institucional'),
                cuenta: obtenerValorFormulario('cuenta'),
                rubro_patrimonial_numero: obtenerValorFormulario('rubro_patrimonial_numero'),
                rubro_patrimonial_descripcion: obtenerValorFormulario('rubro_patrimonial_descripcion'),
                estado: obtenerValorFormulario('estado'),
                numero_migrado: obtenerValorFormulario('numero_migrado'),
                descripcion_item: obtenerValorFormulario('descripcion_item'),
                descripcion_bien: obtenerValorFormulario('descripcion_bien'),
                descripcion_detallada: obtenerValorFormulario('descripcion_detallada'),
                marca: obtenerValorFormulario('marca'),
                modelo: obtenerValorFormulario('modelo'),
                serie: obtenerValorFormulario('serie'),
                anio: obtenerValorFormulario('anio'),
                reparticion: obtenerValorFormulario('reparticion'),
                usuario: obtenerValorFormulario('usuario'), 
                observaciones: obtenerValorFormulario('observaciones'),
                monto_original: obtenerValorFormulario('monto_original'),
                monto_actualizado: obtenerValorFormulario('monto_actualizado'),
                monto_residual: obtenerValorFormulario('monto_residual'),
                
                usuario_destino: obtenerValorFormulario('usuario_destino'), 
                tipo: obtenerValorFormulario('tipo'),
                nombre_de_equipo: obtenerValorFormulario('nombre_de_equipo'),
                puesto: obtenerValorFormulario('puesto'),
                procesador: obtenerValorFormulario('procesador'),
                motherboard: obtenerValorFormulario('motherboard'),
                memoria: obtenerValorFormulario('memoria'),
                disco: obtenerValorFormulario('disco'),
                monitor: obtenerValorFormulario('monitor'),
                serie_monitor: obtenerValorFormulario('serie_monitor'),
                numero_inventario_monitor: obtenerValorFormulario('numero_inventario_monitor')
            };

            try {
                botonSubmit.disabled = true;
                botonSubmit.textContent = 'Actualizando...';
                
                const response = await fetch(`${API_BASE_URL}/${numero}`, {
                    method: 'PUT',
                    headers: getFetchHeaders(),
                    body: JSON.stringify(datosActualizados)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    let msjError = 'Error al actualizar';
                    if (Array.isArray(errorData.detail)) {
                        msjError = errorData.detail.map(err => `Campo '${err.loc[err.loc.length-1]}': ${err.msg}`).join(' | ');
                    } else if (errorData.detail) {
                        msjError = errorData.detail; 
                    }
                    throw new Error(msjError);
                }

                mensajeDiv.style.display = 'block';
                mensajeDiv.style.backgroundColor = '#d4edda';
                mensajeDiv.style.color = '#155724';
                mensajeDiv.textContent = '¡Bien patrimonial actualizado con éxito!';

                setTimeout(() => { window.location.href = '/patrimonio-vista'; }, 1500);

            } catch (error) {
                mensajeDiv.style.display = 'block';
                mensajeDiv.style.backgroundColor = '#f8d7da';
                mensajeDiv.style.color = '#721c24';
                mensajeDiv.textContent = error.message;
            } finally {
                botonSubmit.disabled = false;
                botonSubmit.textContent = 'Guardar Cambios';
            }
        });
    };

    // --- LÓGICA: SELECCIONAR TODOS ---
    const inicializarSeleccionMasiva = () => {
        const chkTodos = document.getElementById('chk-seleccionar-todos');
        if (chkTodos) {
            chkTodos.addEventListener('change', (e) => {
                const checkboxes = document.querySelectorAll('.chk-imprimir');
                checkboxes.forEach(chk => {
                    chk.checked = e.target.checked;
                });
            });
        }
    };

    // --- LÓGICA: HISTORIAL DE BIEN ---
    const inicializarHistorial = async () => {
        const tbody = document.getElementById('tabla-historial-body');
        const titulo = document.getElementById('historial-titulo');
        if (!tbody || !titulo) return;

        const urlParams = new URLSearchParams(window.location.search);
        const numero = urlParams.get('numero');

        if (!numero) {
            alert("No se especificó un número de inventario válido.");
            window.location.href = '/patrimonio-vista';
            return;
        }

        titulo.textContent = `Historial del Bien Nº ${numero}`;

        try {
            const response = await fetch(`${API_BASE_URL}/historial/${numero}`, {
                method: 'GET',
                headers: getFetchHeaders()
            });

            if (!response.ok) throw new Error("Error al cargar el historial");
            
            const historial = await response.json();
            tbody.innerHTML = '';

            if (historial.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No hay registros para este bien.</td></tr>';
                return;
            }

            historial.forEach(reg => {
                const tr = document.createElement('tr');
                
                const fecha = new Date(reg.fecha + 'Z').toLocaleString('es-AR');
                
                let detalle = '-';
                if (reg.campo_modificado) {
                    detalle = `<strong>${reg.campo_modificado}</strong>: <br> 
                               <span style="color: #dc3545; text-decoration: line-through;">${reg.valor_anterior || '(Vacío)'}</span> 
                               ➔ <span style="color: #28a745; font-weight: bold;">${reg.valor_nuevo || '(Vacío)'}</span>`;
                }

                let colorBadge = '#6c757d'; 
                if (reg.accion.includes('ALTA')) colorBadge = '#28a745'; 
                if (reg.accion.includes('BAJA')) colorBadge = '#dc3545'; 
                if (reg.accion === 'MODIFICACION') colorBadge = '#17a2b8'; 
                if (reg.accion.includes('AUTOMATICA')) colorBadge = '#ffc107'; 

                tr.innerHTML = `
                    <td style="font-size: 13px; color: #555;">${fecha}</td>
                    <td><strong>${reg.usuario}</strong><br><small style="color: #888;">IP: ${reg.ip}</small></td>
                    <td>
                        <span style="background-color: ${colorBadge}; color: ${reg.accion.includes('AUTOMATICA') ? '#333' : 'white'}; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">
                            ${reg.accion}
                        </span>
                    </td>
                    <td style="font-size: 13px;">${detalle}</td>
                    <td style="font-size: 13px; color: #666;">${reg.observaciones || '-'}</td>
                `;
                tbody.appendChild(tr);
            });

        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red;">${escapeHTML(error.message)}</td></tr>`;
        }
    };

    // --- LÓGICA: ORDENAMIENTO DESDE CABECERA ---
    const actualizarIconosOrden = () => {
        const columnas = ['numero_inventario', 'rubro_patrimonial_numero', 'rubro_patrimonial_descripcion', 'descripcion_bien', 'anio'];
        
        columnas.forEach(col => {
            const th = document.getElementById(`th-${col}`);
            if (th) {
                const span = th.querySelector('span');
                if (span) {
                    if (columnaOrden === col) {
                        span.textContent = ordenAscendente ? '▲' : '▼';
                    } else {
                        span.textContent = '';
                    }
                }
            }
        });
    };

    const ordenarPor = (columna) => {
        if (columnaOrden === columna) {
            ordenAscendente = !ordenAscendente; 
        } else {
            columnaOrden = columna;
            ordenAscendente = true; 
        }
        actualizarIconosOrden();
        paginaActual = 0; 
        cargarInventario();
    };

    // API Pública del Módulo
    return {
        init: function() {
            console.log('Módulo Patrimonio Inicializado');
            
            if (document.getElementById('tabla-patrimonio-body')) {
                cargarAniosDropdown();
                cargarRubrosDropdown();
                inicializarPaginacion(); 
                cargarInventario(); 
                inicializarImportacion();
                inicializarImportacionAnio(); 
                inicializarImportacionInformatica(); // ✨ NUEVO: Inicializar el botón de Informática
                inicializarExportacion(); 
                inicializarBuscador(); 
                inicializarImpresion(); 
                inicializarSeleccionMasiva();
            }
            
            if (document.getElementById('form-nuevo-bien')) {
                inicializarFormularioNuevo(); 
            }

            if (document.getElementById('form-editar-bien')) {
                inicializarFormularioEdicion(); 
            }

            if (document.getElementById('tabla-historial-body')) {
                inicializarHistorial(); 
            }
        },
        
        editarBien: function(numero_inventario) {
            window.location.href = `/patrimonio-editar?numero=${numero_inventario}`;
        },

        verHistorial: function(numero_inventario) {
            window.location.href = `/patrimonio-historial-vista?numero=${numero_inventario}`;
        },
        
        verDetalles: verDetalles, 
        cerrarDetalles: cerrarDetalles, 
        ordenarPor: ordenarPor
    };

})();

// Inicializar el módulo cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    PatrimonioModulo.init();
});