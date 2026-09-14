// ============================================================================
// chat_historial.js - MÓDULO DE CHAT ESTILO FACEBOOK MESSENGER (PÁGINA /chat)
// ============================================================================
const ChatHistorial = (function() {

    const token = localStorage.getItem('token');
    const API = 'http://localhost:8000';
    let miUsuarioId = token ? decodificarToken(token).id : null;

    let conversaciones = [];
    let contactoActivoId = null;
    let nombreActivo = '';
    let conversacionActiva = null;
    let socket = null;

    const palette = ['#58a598', '#5b8bb1', '#7d6fb4', '#c0608f', '#b08a5b', '#5aa05a', '#b1625b', '#4f8b8b'];

    const colorDe = (nombre) => {
        let h = 0;
        for (let i = 0; i < nombre.length; i++) h = (h * 31 + nombre.charCodeAt(i)) >>> 0;
        return palette[h % palette.length];
    };

    const inicialesDe = (nombre) => {
        const partes = (nombre || '?').trim().split(/\s+/);
        return (partes[0][0] + (partes[1] ? partes[1][0] : '')).toUpperCase();
    };

    const formatearHora = (iso) => {
        if (!iso) return '';
        const d = new Date(iso);
        return d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
    };

    const etiquetaDia = (iso) => {
        if (!iso) return '';
        const d = new Date(iso);
        const hoy = new Date();
        const ayer = new Date();
        ayer.setDate(hoy.getDate() - 1);
        if (d.toDateString() === hoy.toDateString()) return 'Hoy';
        if (d.toDateString() === ayer.toDateString()) return 'Ayer';
        return d.toLocaleDateString('es-AR', { day: 'numeric', month: 'long' });
    };

    const horaParaLista = (iso) => {
        if (!iso) return '';
        const d = new Date(iso);
        const hoy = new Date();
        return d.toDateString() === hoy.toDateString()
            ? formatearHora(iso)
            : d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' });
    };

    const resumenMensaje = (contenido) => {
        const t = String(contenido || '');
        if (/(https?:\/\/.*\.(?:png|jpg|jpeg|gif|webp)(\?.*)?)/i.test(t)) return '🖼️ Imagen';
        return t.replace(/\s+/g, ' ').slice(0, 60);
    };

    const aplicarFotoAvatar = (el, foto, nombre) => {
        if (foto) {
            el.style.backgroundImage = `url("${foto}")`;
            el.style.backgroundSize = 'cover';
            el.style.backgroundPosition = 'center';
            el.innerText = '';
        } else {
            el.style.backgroundImage = '';
            el.style.background = colorDe(nombre);
            el.innerText = inicialesDe(nombre);
        }
    };

    const avatarHTML = (nombre, foto) => {
        if (foto) {
            return `<div class="messenger-avatar" style="background-image:url("${foto}"); background-size:cover; background-position:center;"></div>`;
        }
        const iniciales = inicialesDe(nombre);
        const color = colorDe(nombre);
        return `<div class="messenger-avatar" style="background:${color};">${escapeHTML(iniciales)}</div>`;
    };

    // ---------------- LISTA DE CONVERSACIONES ----------------
    const cargarConversaciones = async () => {
        try {
            const res = await fetch(`${API}/chat/conversaciones`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Error al listar conversaciones');
            conversaciones = await res.json();
            conversaciones = conversaciones.conversaciones || [];
            renderizarConversaciones();

            const vacia = document.getElementById('lista-vacia');
            if (vacia) vacia.style.display = conversaciones.length === 0 ? 'block' : 'none';
        } catch (e) {
            console.error('Error cargando conversaciones:', e);
        }
    };

    const renderizarConversaciones = () => {
        conversaciones.sort((a, b) => (b.fecha_ultimo || '').localeCompare(a.fecha_ultimo || ''));
        const lista = document.getElementById('lista-conversaciones');
        if (!lista) return;
        lista.innerHTML = '';

        if (conversaciones.length === 0) return;

        conversaciones.forEach(c => {
            const activa = c.contacto_id === contactoActivoId;
            const online = c.online ? '<span class="punto-online" title="En línea"></span>' : '';
            const preview = c.fue_mio ? `Yo: ${resumenMensaje(c.ultimo_mensaje)}` : resumenMensaje(c.ultimo_mensaje);
            const badge = c.no_leidos > 0
                ? `<span class="conversacion-badge">${c.no_leidos > 99 ? '99+' : c.no_leidos}</span>`
                : '';

            lista.innerHTML += `
                <div class="conversacion ${activa ? 'activa' : ''}" data-id="${c.contacto_id}" onclick="ChatHistorial.abrir(${c.contacto_id})">
                    ${avatarHTML(c.nombre, c.foto)}
                    ${online}
                    <div class="conversacion-cuerpo">
                        <div class="conversacion-fila">
                            <strong class="conversacion-nombre">${escapeHTML(c.nombre)}</strong>
                            <span class="conversacion-hora">${horaParaLista(c.fecha_ultimo)}</span>
                        </div>
                        <div class="conversacion-fila">
                            <span class="conversacion-preview ${c.no_leidos > 0 ? 'no-leidos' : ''}">${escapeHTML(preview)}</span>
                            ${badge}
                        </div>
                    </div>
                </div>`;
        });
    };

    const actualizarItemEnLista = (conv) => {
        const idx = conversaciones.findIndex(c => c.contacto_id === conv.contacto_id);
        if (idx >= 0) conversaciones[idx] = { ...conversaciones[idx], ...conv };
        else conversaciones.push(conv);
        renderizarConversaciones();
    };

    // ---------------- ABRIR CONVERSACIÓN ----------------
    const abrirConversacion = async (id) => {
        contactoActivoId = id;
        const conv = conversaciones.find(c => c.contacto_id === id);
        conversacionActiva = conv || null;
        nombreActivo = conv ? conv.nombre : 'Contacto';

        document.getElementById('pantalla-vacia').style.display = 'none';
        const panel = document.getElementById('pantalla-conversacion');
        panel.style.display = 'flex';

        document.getElementById('nombre-activo').innerText = nombreActivo;
        const avatarActivo = document.getElementById('avatar-activo');
        aplicarFotoAvatar(avatarActivo, conv ? conv.foto : null, nombreActivo);
        actualizarEstadoActivo(conv ? conv.online : false);
        cerrarMenuConversacion();

        if (conv && conv.no_leidos > 0) {
            conv.no_leidos = 0;
            renderizarConversaciones();
        }

        await cargarHistorial(id);
    };

    const actualizarEstadoActivo = (online) => {
        const el = document.getElementById('estado-activo');
        if (!el) return;
        el.innerText = online ? 'En línea' : 'Desconectado';
        el.style.color = online ? '#2e9e5b' : '#999';
    };

    const cargarHistorial = async (id) => {
        try {
            const res = await fetch(`${API}/chat/historial/${id}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Error al cargar historial');
            const mensajes = await res.json();
            renderizarHilo(mensajes);
        } catch (e) {
            console.error('Error cargando historial:', e);
        }
    };

    const renderizarHilo = (mensajes) => {
        const hilo = document.getElementById('hilo-mensajes');
        if (!hilo) return;
        hilo.innerHTML = '';

        if (mensajes.length === 0) {
            hilo.innerHTML = '<div style="text-align:center; color:#b0bec5; padding:30px; font-size:13px;">Sin mensajes todavía. ¡Escribí el primero!</div>';
            return;
        }

        let diaActual = null;
        mensajes.forEach(m => {
            const dia = etiquetaDia(m.fecha);
            if (dia !== diaActual) {
                diaActual = dia;
                hilo.innerHTML += `<div class="separador-dia"><span>${escapeHTML(dia)}</span></div>`;
            }
            hilo.innerHTML += `
                <div class="msg-burbuja ${m.es_mio ? 'salida' : 'entrada'}">
                    <div class="msg-contenido">${contenidoRico(m.contenido)}</div>
                    <div class="msg-hora">${formatearHora(m.fecha)}</div>
                </div>`;
        });

        hilo.scrollTop = hilo.scrollHeight;
    };

    const contenidoRico = (texto) => {
        const regexImagen = /(https?:\/\/.*\.(?:png|jpg|jpeg|gif|webp)(\?.*)?)/i;
        const regexSoloEmojis = /^[\p{Emoji_Presentation}\p{Extended_Pictographic}\s]+$/u;

        if (regexImagen.test(texto)) {
            const urlImagen = texto.match(regexImagen)[1];
            return escapeHTML(texto) + `<br><img src="${escapeHTML(urlImagen)}" class="msg-imagen">`;
        }
        if (regexSoloEmojis.test(texto.trim()) && texto.trim().length > 0) {
            return `<span style="font-size:45px;">${escapeHTML(texto.trim())}</span>`;
        }
        return escapeHTML(texto).replace(/\n/g, '<br>');
    };

    // ---------------- ENVÍO ----------------
    const enviarMensaje = () => {
        const input = document.getElementById('input-mensaje');
        const texto = input.value.trim();
        if (!texto || !socket || contactoActivoId === null) return;

        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ destinatario_id: contactoActivoId, contenido: texto }));
        }

        const hilo = document.getElementById('hilo-mensajes');
        hilo.innerHTML += `
            <div class="msg-burbuja salida">
                <div class="msg-contenido">${contenidoRico(texto)}</div>
                <div class="msg-hora">${formatearHora(new Date().toISOString())}</div>
            </div>`;
        hilo.scrollTop = hilo.scrollHeight;
        input.value = '';

        const conv = conversaciones.find(c => c.contacto_id === contactoActivoId);
        if (conv) {
            actualizarItemEnLista({
                ...conv,
                ultimo_mensaje: texto,
                fecha_ultimo: new Date().toISOString(),
                fue_mio: true,
                no_leidos: 0
            });
        }
    };

    // ---------------- WEBSOCKET (TIEMPO REAL) ----------------
    const conectarWebSocket = () => {
        if (!miUsuarioId) return;
        socket = new WebSocket(`ws://${window.location.host}/ws/chat/${miUsuarioId}?token=${encodeURIComponent(token)}`);

        socket.onmessage = (event) => {
            const msg = JSON.parse(event.data);

            if (msg.tipo === 'estado') {
                const conv = conversaciones.find(c => c.contacto_id === msg.usuario_id);
                if (conv) {
                    conv.online = msg.online;
                    if (msg.usuario_id === contactoActivoId) actualizarEstadoActivo(msg.online);
                    renderizarConversaciones();
                }
                return;
            }

            // Los que el servidor entrega al conectar (historico) ya están en /conversaciones
            if (msg.historico) return;

            const conv = conversaciones.find(c => c.contacto_id === msg.remitente_id);
            if (conv) {
                conv.ultimo_mensaje = msg.contenido;
                conv.fecha_ultimo = msg.fecha;
                conv.fue_mio = false;

                if (msg.remitente_id === contactoActivoId) {
                    hiloAgregarEntrante(msg);
                    conv.no_leidos = 0;
                } else {
                    conv.no_leidos = (conv.no_leidos || 0) + 1;
                }
                renderizarConversaciones();
            } else {
                // Primera vez que esta persona me escribe: recargar lista completa
                cargarConversaciones();
            }
        };

        socket.onclose = () => {
            setTimeout(conectarWebSocket, 3000);
        };
    };

    const hiloAgregarEntrante = (msg) => {
        const hilo = document.getElementById('hilo-mensajes');
        hilo.innerHTML += `
            <div class="msg-burbuja entrada">
                <div class="msg-contenido">${contenidoRico(msg.contenido)}</div>
                <div class="msg-hora">${formatearHora(msg.fecha)}</div>
            </div>`;
        hilo.scrollTop = hilo.scrollHeight;
    };

    // ---------------- MENÚ DE OPCIONES (⋮) ----------------
    const toggleMenuConversacion = (e) => {
        e.stopPropagation();
        const menu = document.getElementById('menu-conversacion');
        if (!menu) return;
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    };

    const cerrarMenuConversacion = () => {
        const menu = document.getElementById('menu-conversacion');
        if (menu) menu.style.display = 'none';
    };

    const abrirPerfil = () => {
        cerrarMenuConversacion();
        if (!conversacionActiva) return;

        const c = conversacionActiva;
        const avatar = document.getElementById('perfil-avatar');
        aplicarFotoAvatar(avatar, c.foto, c.nombre);
        avatar.style.backgroundSize = 'cover';

        document.getElementById('perfil-nombre').innerText = c.nombre;
        document.getElementById('perfil-sector').innerText = c.reparticion ? `Sector: ${c.reparticion}` : 'Sector: —';
        document.getElementById('perfil-estado').innerText = c.online ? '🟢 En línea' : '⚪ Desconectado';
        document.getElementById('perfil-contacto').innerText = c.es_contacto ? 'Es tu contacto' : 'Ya no es tu contacto';

        const modal = document.getElementById('modal-perfil');
        modal.style.display = 'flex';
    };

    const cerrarPerfil = () => {
        document.getElementById('modal-perfil').style.display = 'none';
    };

    const volverAPantallaVacia = () => {
        contactoActivoId = null;
        conversacionActiva = null;
        nombreActivo = '';
        document.getElementById('pantalla-conversacion').style.display = 'none';
        document.getElementById('pantalla-vacia').style.display = 'flex';
        cerrarMenuConversacion();
    };

    const borrarChat = async () => {
        cerrarMenuConversacion();
        if (contactoActivoId === null) return;
        if (!confirm(`¿Seguro que querés borrar la conversación con ${nombreActivo}?`)) return;

        try {
            const res = await fetch(`${API}/chat/historial/${contactoActivoId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Error al borrar el historial');

            conversaciones = conversaciones.filter(c => c.contacto_id !== contactoActivoId);
            renderizarConversaciones();
            volverAPantallaVacia();

            const vacia = document.getElementById('lista-vacia');
            if (vacia) vacia.style.display = conversaciones.length === 0 ? 'block' : 'none';
        } catch (e) {
            console.error('Error borrando historial:', e);
        }
    };

    // ---------------- EMOJIS ----------------
    const listaEmojisPropios = [
        "😀","😂","🤣","😊","😍","🥰","😘","😜","🤪","😎","🤩","🥳","😏","😒","😞","😔",
        "😟","😕","🥺","😢","😭","😤","😠","😡","🤬","🤯","😳","🥵","🥶","😱","😨","😰",
        "🤗","🤔","🤭","🤫","🙄","😮","😴","🤤","😵","🤢","🤮","😷","👍","👎","👏","🙌",
        "🤝","🙏","💪","🧠","👀","❤️","🔥","✨","🌟","🎉","🎊","💯","✅","❌","❓","❗"
    ];

    const toggleEmojis = (e) => {
        e.stopPropagation();
        const picker = document.getElementById('emoji-picker-page');
        if (!picker) return;

        if (picker.children.length === 0) {
            const fuente = (typeof window.listaEmojis !== 'undefined') ? window.listaEmojis : listaEmojisPropios;
            fuente.forEach(emoji => {
                const span = document.createElement('span');
                span.innerText = emoji;
                span.style.cssText = 'cursor:pointer; font-size:22px; padding:4px; display:inline-block; transition:transform .1s;';
                span.onmouseover = () => span.style.transform = 'scale(1.2)';
                span.onmouseout = () => span.style.transform = 'scale(1)';
                span.onclick = (ev) => {
                    ev.stopPropagation();
                    const input = document.getElementById('input-mensaje');
                    input.value += emoji;
                    input.focus();
                };
                picker.appendChild(span);
            });
        }

        picker.style.display = picker.style.display === 'none' ? 'flex' : 'none';
    };

    // ---------------- INIT ----------------
    const init = () => {
        if (!token || !miUsuarioId) return;

        cargarConversaciones();
        conectarWebSocket();

        const btnEnviar = document.getElementById('btn-enviar');
        const inputMensaje = document.getElementById('input-mensaje');
        const inputBuscar = document.getElementById('input-buscar-conversaciones');
        const btnEmojis = document.getElementById('btn-emojis-page');
        const btnMenu = document.getElementById('btn-menu-conv');
        const opcionPerfil = document.getElementById('opcion-ver-perfil');
        const opcionBorrar = document.getElementById('opcion-borrar-chat');
        const btnCerrarPerfil = document.getElementById('btn-cerrar-perfil');
        const modalPerfil = document.getElementById('modal-perfil');

        if (btnEnviar && inputMensaje) {
            btnEnviar.addEventListener('click', enviarMensaje);
            inputMensaje.addEventListener('keypress', (e) => { if (e.key === 'Enter') enviarMensaje(); });
        }

        if (inputBuscar) {
            inputBuscar.addEventListener('input', () => {
                const q = inputBuscar.value.trim().toLowerCase();
                document.querySelectorAll('.conversacion').forEach(item => {
                    const nombre = item.querySelector('.conversacion-nombre').innerText.toLowerCase();
                    item.style.display = nombre.includes(q) ? '' : 'none';
                });
            });
        }

        if (btnEmojis) {
            btnEmojis.addEventListener('click', toggleEmojis);
        }

        if (btnMenu) {
            btnMenu.addEventListener('click', toggleMenuConversacion);
        }

        if (opcionPerfil) {
            opcionPerfil.addEventListener('click', abrirPerfil);
        }

        if (opcionBorrar) {
            opcionBorrar.addEventListener('click', borrarChat);
        }

        if (btnCerrarPerfil) {
            btnCerrarPerfil.addEventListener('click', cerrarPerfil);
        }

        if (modalPerfil) {
            modalPerfil.addEventListener('click', (e) => {
                if (e.target === modalPerfil) cerrarPerfil();
            });
        }

        window.addEventListener('click', () => {
            const picker = document.getElementById('emoji-picker-page');
            if (picker && picker.style.display === 'flex') picker.style.display = 'none';
            cerrarMenuConversacion();
        });
    };

    document.addEventListener('DOMContentLoaded', init);

    return { abrir: abrirConversacion };
})();