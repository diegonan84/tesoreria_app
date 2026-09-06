// ============================================================================
// chat.js - MÓDULO DE CHAT EN TIEMPO REAL (MSN STYLE) Y EMOJIS
// ============================================================================

let chatSocket = null;
let miUsuarioId = null;
let directorioUsuarios = {}; 

let estadoGuardado = JSON.parse(sessionStorage.getItem("estadoChat")) || { historialChat: {}, noLeidos: {}, destinatarioActivoId: null, widgetAbierto: false };
let historialChat = estadoGuardado.historialChat;
let noLeidos = estadoGuardado.noLeidos;
let destinatarioActivoId = estadoGuardado.destinatarioActivoId;
let widgetAbierto = estadoGuardado.widgetAbierto;

function guardarMemoriaChat() {
    sessionStorage.setItem("estadoChat", JSON.stringify({ historialChat, noLeidos, destinatarioActivoId, widgetAbierto }));
}

function cambiarPestanaChat(pestana) {
    document.getElementById("pantalla-contactos").style.display = pestana === 'contactos' ? 'block' : 'none';
    document.getElementById("pantalla-buscar").style.display = pestana === 'buscar' ? 'block' : 'none';
    document.getElementById("tab-contactos").style.background = pestana === 'contactos' ? 'white' : 'transparent';
    document.getElementById("tab-buscar").style.background = pestana === 'buscar' ? 'white' : 'transparent';
}

function toggleChat() {
    const body = document.getElementById("chat-body");
    widgetAbierto = body.style.display !== "flex";
    body.style.display = widgetAbierto ? "flex" : "none";
    document.getElementById("notif-chat").style.display = "none";
    guardarMemoriaChat();
}

async function inicializarChat() {
    const token = localStorage.getItem("token");
    if (!token) return;
    miUsuarioId = decodificarToken(token).id; // Requiere app.js

    if (widgetAbierto) document.getElementById("chat-body").style.display = "flex";

    await cargarDirectorioY_Solicitudes();

    chatSocket = new WebSocket(`ws://${window.location.host}/ws/chat/${miUsuarioId}?token=${encodeURIComponent(token)}`);
    chatSocket.onmessage = function(event) {
        const msg = JSON.parse(event.data);
        
        if (msg.tipo === "estado") {
            moverContactoDOM(msg.usuario_id, msg.online);
            return;
        }
        
        if (!historialChat[msg.remitente_id]) historialChat[msg.remitente_id] = [];
        historialChat[msg.remitente_id].push({ texto: msg.contenido, tipo: 'msg-in' });
        
        if (destinatarioActivoId === msg.remitente_id) {
            dibujarMensaje(msg.contenido, 'msg-in');
        } else {
            if(document.getElementById(`contacto-${msg.remitente_id}`)) {
                noLeidos[msg.remitente_id] = (noLeidos[msg.remitente_id] || 0) + 1;
                actualizarBadge(msg.remitente_id);
                document.getElementById("notif-chat").style.display = "inline-block";
            }
        }
        guardarMemoriaChat();
    };
}

async function cargarDirectorioY_Solicitudes() {
    const res = await fetch(`${API_URL}/directorio-chat`, { headers: { "Authorization": `Bearer ${localStorage.getItem('token')}` } });
    if (!res.ok) return;
    const data = await res.json();
    
    const panelSol = document.getElementById("panel-solicitudes");
    const listaSol = document.getElementById("lista-solicitudes");
    listaSol.innerHTML = "";
    if (data.pendientes.length > 0) {
        panelSol.style.display = "block";
        data.pendientes.forEach(p => {
            listaSol.innerHTML += `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px; font-size:12px;">
                    <span>👤 ${escapeHTML(p.nombre)}</span>
                    <button onclick="aceptarSolicitud(${p.id_solicitud})" style="background:#28a745; color:white; border:none; padding:3px 6px; border-radius:3px; cursor:pointer;">Aceptar</button>
                </div>`;
        });
    } else panelSol.style.display = "none";

    const divConectados = document.getElementById("lista-conectados");
    const divDesconectados = document.getElementById("lista-desconectados");
    divConectados.innerHTML = ""; divDesconectados.innerHTML = "";
    
    data.amigos.forEach(c => {
        directorioUsuarios[c.id] = c.nombre;
        if (noLeidos[c.id] === undefined) noLeidos[c.id] = 0;
        
        const html = `
            <div class="chat-contact-item" id="contacto-${c.id}" onclick="abrirConversacion(${c.id}, '${escapeHTML(c.nombre)}')" style="display:flex; justify-content:space-between; padding: 8px; border-bottom: 1px solid #eee; cursor: pointer;">
                <span style="font-size: 13px;"><span id="estado-icon-${c.id}">${c.online ? '🟢' : '⚪'}</span> ${escapeHTML(c.nombre)}</span> 
                <span id="badge-${c.id}" style="display: ${noLeidos[c.id] > 0 ? 'inline' : 'none'}; background: #ffcc00; border-radius: 50%; padding: 2px 6px; font-size: 10px;">
                    <span id="count-${c.id}">${noLeidos[c.id]}</span>
                </span>
            </div>`;
        c.online ? divConectados.innerHTML += html : divDesconectados.innerHTML += html;
    });
    actualizarContadoresGrupos();
}

async function buscarGlobalChat() {
    const q = document.getElementById("input-buscar-chat").value;
    if(q.length < 3) return alert("Escribe al menos 3 letras");
    
    const res = await fetch(`${API_URL}/chat/buscar?q=${q}`, { headers: { "Authorization": `Bearer ${localStorage.getItem('token')}` } });
    const usuarios = await res.json();
    const caja = document.getElementById("resultados-busqueda");
    
    caja.innerHTML = usuarios.length === 0 ? "<div style='font-size:12px; color:#666;'>No hay resultados.</div>" : "";
    usuarios.forEach(u => {
        const botonAgregar = directorioUsuarios[u.id] ? `<span style="color:#28a745; font-size:11px;">Ya es contacto</span>` : `<button onclick="enviarSolicitud(${u.id})" style="background:#1a3644; color:white; border:none; padding:4px 8px; border-radius:4px; font-size:11px; cursor:pointer;">+ Agregar</button>`;
        caja.innerHTML += `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px; border:1px solid #eee; margin-bottom:5px;">
                <span style="font-size: 12px;">${escapeHTML(u.nombre)}</span>
                ${botonAgregar}
            </div>`;
    });
}

async function enviarSolicitud(id) {
    const res = await fetch(`${API_URL}/chat/solicitud/${id}`, { method: 'POST', headers: { "Authorization": `Bearer ${localStorage.getItem('token')}` } });
    if(res.ok) { alert("Solicitud enviada"); buscarGlobalChat(); }
    else alert("Ya enviaste una solicitud a esta persona.");
}

async function aceptarSolicitud(solicitudId) {
    await fetch(`${API_URL}/chat/solicitud/${solicitudId}/aceptar`, { method: 'PUT', headers: { "Authorization": `Bearer ${localStorage.getItem('token')}` } });
    cargarDirectorioY_Solicitudes(); 
}

async function eliminarContactoActivo() {
    if(!confirm("¿Seguro que deseas eliminar este contacto? Se borrará el historial.")) return;
    await fetch(`${API_URL}/chat/contacto/${destinatarioActivoId}`, { method: 'DELETE', headers: { "Authorization": `Bearer ${localStorage.getItem('token')}` } });
    
    delete historialChat[destinatarioActivoId];
    delete directorioUsuarios[destinatarioActivoId];
    guardarMemoriaChat();
    volverDirectorio();
    cargarDirectorioY_Solicitudes(); 
}

function abrirConversacion(id, nombre) {
    destinatarioActivoId = id;
    noLeidos[id] = 0;
    actualizarBadge(id);

    document.getElementById("pantalla-contactos").style.display = "none";
    document.getElementById("pantalla-buscar").style.display = "none";
    
    document.getElementById("chat-conversation").style.display = "flex";
    document.getElementById("chat-nombre-activo").innerText = nombre;
    
    const box = document.getElementById("chat-messages");
    box.innerHTML = ""; 
    if (historialChat[id]) historialChat[id].forEach(m => dibujarMensaje(m.texto, m.tipo));
    guardarMemoriaChat();
}

function volverDirectorio() {
    destinatarioActivoId = null;
    document.getElementById("chat-conversation").style.display = "none";
    cambiarPestanaChat('contactos'); 
    guardarMemoriaChat();
}

function dibujarMensaje(texto, claseCss) {
    const box = document.getElementById("chat-messages");
    
    const regexImagen = /(https?:\/\/.*\.(?:png|jpg|jpeg|gif|webp)(\?.*)?)/i;
    const regexSoloEmojis = /^[\p{Emoji_Presentation}\p{Extended_Pictographic}\s]+$/u;
    
    let contenidoHTML = escapeHTML(texto);
    let estiloExtra = ""; 

    if (regexImagen.test(texto)) {
        const urlImagen = texto.match(regexImagen)[1];
        contenidoHTML = escapeHTML(texto) + `<br><img src="${escapeHTML(urlImagen)}" style="max-width: 100%; max-height: 150px; border-radius: 6px; margin-top: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);">`;
    } 
    else if (regexSoloEmojis.test(texto.trim()) && texto.trim().length > 0) {
        estiloExtra = "font-size: 45px; background: transparent; padding: 0; box-shadow: none;";
    }

    box.innerHTML += `<div class="msg-bubble ${claseCss}" style="${estiloExtra}">${contenidoHTML}</div>`;
    box.scrollTop = box.scrollHeight; 
}

function enviarMensaje() {
    const input = document.getElementById("chat-input");
    const texto = input.value.trim();
    if (texto === "" || !chatSocket || !destinatarioActivoId) return;

    if (!historialChat[destinatarioActivoId]) historialChat[destinatarioActivoId] = [];
    historialChat[destinatarioActivoId].push({ texto: texto, tipo: 'msg-out' });

    dibujarMensaje(texto, 'msg-out');
    chatSocket.send(JSON.stringify({ destinatario_id: destinatarioActivoId, contenido: texto }));
    input.value = "";
    guardarMemoriaChat();
}

function toggleGrupoChat(id) { 
    document.getElementById(id).style.display = document.getElementById(id).style.display === "none" ? "block" : "none"; 
}

function moverContactoDOM(usuario_id, online) {
    const item = document.getElementById(`contacto-${usuario_id}`);
    const icono = document.getElementById(`estado-icon-${usuario_id}`);
    if (!item || !icono) return; 

    icono.innerText = online ? '🟢' : '⚪';
    if (online) document.getElementById("lista-conectados").appendChild(item);
    else document.getElementById("lista-desconectados").appendChild(item);
    actualizarContadoresGrupos();
}

function actualizarContadoresGrupos() {
    if (document.getElementById("count-conectados")) document.getElementById("count-conectados").innerText = document.getElementById("lista-conectados").children.length;
    if (document.getElementById("count-desconectados")) document.getElementById("count-desconectados").innerText = document.getElementById("lista-desconectados").children.length;
}

function actualizarBadge(id) {
    const badge = document.getElementById(`badge-${id}`);
    const countSpan = document.getElementById(`count-${id}`);
    if (badge && countSpan) {
        if (noLeidos[id] > 0) {
            badge.style.display = "inline";
            countSpan.innerText = noLeidos[id];
        } else {
            badge.style.display = "none";
            countSpan.innerText = "0";
        }
    }
}

// --- PANEL DE EMOJIS ---
const listaEmojis = [
    "😀","😂","🤣","😊","😍","🥰","😘","😜","🤪","😎","🤩","🥳","😏",
    "😒","😞","😔","😟","😕","🙁","😣","😖","😫","😩","🥺","😢","😭",
    "😤","😠","😡","🤬","🤯","😳","🥵","🥶","😱","😨","😰","😥","😓",
    "🤗","🤔","🤭","🤫","🤥","😶","😐","😑","😬","🙄","😯","😦","😧",
    "😮","😲","🥱","😴","🤤","😪","😵","🤐","🥴","🤢","🤮","🤧","😷",
    "👍","👎","👏","🙌","👐","🤲","🤝","🙏","💪","🧠","👀","👁️","❤️",
    "🔥","✨","🌟","🎉","🎊","💯","✅","❌","❓","❔","❕","❗"
];

function toggleEmojiPicker(event) {
    if (event) event.stopPropagation();
    const picker = document.getElementById('emoji-picker');
    if (!picker) return;
    
    if (picker.children.length === 0) {
        listaEmojis.forEach(emoji => {
            const span = document.createElement('span');
            span.innerText = emoji;
            span.style.cursor = "pointer";
            span.style.fontSize = "22px";
            span.style.padding = "4px";
            span.style.display = "inline-block";
            span.style.transition = "transform 0.1s";
            
            span.onmouseover = () => span.style.transform = "scale(1.2)";
            span.onmouseout = () => span.style.transform = "scale(1)";
            
            span.onclick = function(e) {
                e.stopPropagation(); 
                const input = document.getElementById('chat-input');
                input.value += emoji;
                input.focus(); 
            };
            picker.appendChild(span);
        });
    }
    
    picker.style.display = picker.style.display === 'none' ? 'flex' : 'none';
}

window.addEventListener("click", () => {
    const picker = document.getElementById("emoji-picker");
    if (picker && picker.style.display === "flex") {
        picker.style.display = "none";
    }
});