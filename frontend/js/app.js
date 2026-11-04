// ============================================================================
// app.js - NÚCLEO Y CONFIGURACIÓN GLOBAL
// ============================================================================
const API_URL = window.location.origin; // mismo servidor que sirve la página (local o Proxmox)

/* ============================================================================
   CATÁLOGO DE PERMISOS (módulos y páginas a las que se puede entrar)
   Lo usan el sidebar, el control de acceso por ruta y el formulario de Usuarios.
   El código de módulo y el de cada página se guardan en User.roles.
   Ayuda y Mi Perfil son de acceso básico (Operador); Mesa de Ayuda se habilita por usuario.
   ============================================================================ */
const CATALOGO_PERMISOS = [
    { codigo: "Calendario", nombre: "Calendario", icono: "📅", paginas: [
        { codigo: "Cal_Agenda", nombre: "Agenda / Calendario", rutas: ["/calendario"], defecto: true },
        { codigo: "Cal_Notificaciones", nombre: "Gestión de Notificaciones", rutas: ["/notificaciones"] },
    ]},
    { codigo: "Chat", nombre: "Chat", icono: "💬", paginas: [
        { codigo: "Chat_Mensajes", nombre: "Mensajes", rutas: ["/chat"], defecto: true },
    ]},
    { codigo: "EstFin", nombre: "Estudios Financieros", icono: "🧮", paginas: [
        { codigo: "EstFin_Planillas", nombre: "Planillas de liquidación", rutas: [] },
        { codigo: "EstFin_Historico", nombre: "Histórico anual", rutas: [] },
    ]},
    { codigo: "RRHH", nombre: "Recursos Humanos", icono: "🧑‍💼", paginas: [
        { codigo: "RRHH_Fichadas", nombre: "Control de Fichadas", rutas: ["/control-fichadas"] },
    ]},
    { codigo: "Rendicion", nombre: "Rendición y Control", icono: "📋", paginas: [
        { codigo: "Rend_Rendiciones", nombre: "Rendiciones presentadas", rutas: [] },
        { codigo: "Rend_Arqueos", nombre: "Arqueos de caja", rutas: [] },
    ]},
    { codigo: "Patrimonio", nombre: "Patrimonio", icono: "🏛️", paginas: [
        { codigo: "Patr_Inventario", nombre: "Inventario", rutas: ["/patrimonio-vista", "/patrimonio-editar", "/patrimonio-imprimir"] },
        { codigo: "Patr_Alta", nombre: "Alta de Bien", rutas: ["/patrimonio-nuevo"] },
        { codigo: "Patr_Informatica", nombre: "Informática", rutas: ["/patrimonio-informatica"] },
        { codigo: "Patr_Asignaciones", nombre: "Elementos por Usuario/Destino", rutas: ["/consulta-asignaciones"] },
        { codigo: "Patr_Total", nombre: "Inventario Total", rutas: ["/patrimonio-inventario-total"] },
        { codigo: "Patr_Historial", nombre: "Historial", rutas: ["/patrimonio-historial-vista"] },
        { codigo: "Patr_Importar", nombre: "Importar Excel", rutas: ["/patrimonio-importar"] },
        { codigo: "Patr_Barras", nombre: "Códigos de Barras", rutas: ["/patrimonio-codigos"] },
        { codigo: "Patr_Reportes", nombre: "Reportes", rutas: ["/patrimonio-reportes"] },
    ]},
    { codigo: "Usuarios", nombre: "Usuarios", icono: "👥", paginas: [
        { codigo: "Usu_Gestion", nombre: "Gestión de Usuarios", rutas: ["/usuarios"] },
        { codigo: "Usu_Mapa", nombre: "Mapa de Puestos", rutas: ["/mapa"] },
        { codigo: "Usu_Plano", nombre: "Editor de Plano", rutas: ["/editor-mapa"] },
        { codigo: "Usu_Auditoria", nombre: "Auditoría de Accesos", rutas: ["/auditoria"] },
    ]},
    { codigo: "Sistemas", nombre: "Sistemas", icono: "💻", paginas: [
        { codigo: "Sis_Aplicaciones", nombre: "Gestión de Aplicaciones", rutas: ["/sistemas"] },
        { codigo: "Sis_Permisos", nombre: "Permisos y Accesos", rutas: [] },
    ]},
    // No viene tildado por defecto: se habilita por usuario. El rol "Soporte" también da acceso.
    { codigo: "Tickets", nombre: "Mesa de Ayuda", icono: "🎫", paginas: [
        { codigo: "Tick_Tickets", nombre: "Tickets (crear y consultar)", rutas: ["/tickets"] },
    ]},
];

// Roles que dan acceso a una página aunque no esté tildada en el árbol
const PERMISOS_IMPLICITOS = { Tick_Tickets: ["Soporte"] };

// ¿El usuario (lista de roles) puede entrar a esta página/módulo?
// Compatibilidad: si tiene el módulo pero ninguna página del módulo tildada, ve todas.
function tienePermiso(roles, codigo) {
    if (roles.includes("Administrador") || roles.includes(codigo)) return true;
    if ((PERMISOS_IMPLICITOS[codigo] || []).some(r => roles.includes(r))) return true;
    const modulo = CATALOGO_PERMISOS.find(m => m.paginas.some(p => p.codigo === codigo));
    return !!modulo && roles.includes(modulo.codigo) && !modulo.paginas.some(p => roles.includes(p.codigo));
}

function paginaDeRuta(path) {
    for (const m of CATALOGO_PERMISOS) {
        const pagina = m.paginas.find(p => p.rutas.includes(path));
        if (pagina) return pagina;
    }
    return null;
}

// Oculta del sidebar los ítems sin permiso, y los módulos que quedan vacíos
function aplicarPermisosSidebar(roles) {
    const sidebar = document.getElementById("global-sidebar");
    if (!sidebar) return;
    sidebar.querySelectorAll("[data-permiso]").forEach(a => {
        const li = a.closest("li") || a;
        li.style.display = tienePermiso(roles, a.dataset.permiso) ? "" : "none";
    });
    sidebar.querySelectorAll("details.sidebar-item").forEach(det => {
        const items = det.querySelectorAll(".submenu > li");
        if (items.length && [...items].every(li => li.style.display === "none")) det.style.display = "none";
    });
}

/* ============================================================================
   INTERCEPTOR GLOBAL DE SEGURIDAD (El "Guardia" de las peticiones)
   ============================================================================ */
const originalFetch = window.fetch;

window.fetch = async function() {
    const response = await originalFetch.apply(this, arguments);
    
    // Si el servidor responde 401 (Unauthorized), el token expiró o es inválido
    if (response.status === 401) {
        console.warn("⚠️ Acceso denegado (401). El token caducó. Redirigiendo al login...");
        localStorage.removeItem('token');
        sessionStorage.removeItem('estadoChat'); 
        window.location.href = '/login';  
        throw new Error("Token expirado"); // Lanza error para detener la promesa
    }

    // 403 con CAMBIO_CLAVE_REQUERIDO: tiene la clave por defecto y solo puede usar su perfil
    if (response.status === 403) {
        const datos = await response.clone().json().catch(() => null);
        if (datos && datos.detail === "CAMBIO_CLAVE_REQUERIDO") {
            if (window.location.pathname !== "/perfil") window.location.href = "/perfil";
            throw new Error("Cambio de clave requerido");
        }
    }

    return response; 
};

// --- FUNCIÓN MAESTRA (PLANTILLA COMÚN Y CACHE BUSTER) ---
async function cargarPlantillaComun() {
    const path = window.location.pathname;
    const esPaginaChat = path === "/chat";

    if (path.includes("/login") || path.includes("/registro") || path.includes("/recuperar")) return; 

    // Verificamos antes de intentar traer los HTML de la plantilla
    if (!verificarAcceso()) return; 
    
    try {
        const cacheBuster = "?v=" + new Date().getTime();

        // 1. Inyectar la Navbar
        const resNavbar = await fetch('/archivos/componentes/navbar.html' + cacheBuster);
        if (resNavbar.ok && document.getElementById("global-navbar")) {
            document.getElementById("global-navbar").innerHTML = await resNavbar.text();
            const subtitulo = document.getElementById("nav-subtitle");
            if (subtitulo) {
const titulosModulo = [
                    ["/control-fichadas", "Control de Fichadas"],
                    ["/consulta-asignaciones", "Elementos por Usuario/Destino"],
                    ["/calendario", "Calendario"],
                    ["/patrimonio", "Patrimonio"],
                    ["/editor-mapa", "Editor de Plano"],
                    ["/mapa", "Mapa de Puestos"],
                    ["/sistemas", "Sistemas"],
                    ["/tickets", "Mesa de Ayuda"],
                    ["/usuarios", "Gestión de Usuarios"],
                    ["/auditoria", "Auditoría de Accesos"],
                    ["/notificaciones", "Gestión de Avisos"],
                    ["/ayuda", "Centro de Ayuda"],
                    ["/perfil", "Mi Perfil"],
                    ["/chat", "Chat"]
                ];
                const encontrado = titulosModulo.find(([ruta]) => path.includes(ruta));
                subtitulo.innerText = encontrado ? encontrado[1] : "Panel Operativo";
            }
        }

        // 2. Inyectar la Sidebar
        const resSidebar = await fetch('/archivos/componentes/sidebar.html' + cacheBuster);
        if (resSidebar.ok && document.getElementById("global-sidebar")) {
            document.getElementById("global-sidebar").innerHTML = await resSidebar.text();
        }

        // 3. Inyectar el Widget de Chat (se desactiva en la página /chat)
        const resChat = await fetch('/archivos/componentes/chat.html' + cacheBuster);
        const rolesChat = (decodificarToken(localStorage.getItem("token")) || {}).roles || [];
        if (resChat.ok && document.getElementById("global-chat") && !esPaginaChat && tienePermiso(rolesChat, "Chat_Mensajes")) {
            document.getElementById("global-chat").innerHTML = await resChat.text();
        }

        verificarAccessoYInicializar();

    } catch (error) {
        console.error("Error crítico cargando los componentes:", error);
    }
}

function verificarAccessoYInicializar() {
    // Si la sesión caducó, detener aquí
    if (!verificarAcceso()) return;
    
    // Inicializamos el Chat (el widget flotante no corre en la página /chat)
    const roles = (decodificarToken(localStorage.getItem("token")) || {}).roles || [];
    if (typeof inicializarChat === 'function' && window.location.pathname !== '/chat' && tienePermiso(roles, "Chat_Mensajes")) inicializarChat();

    // Inicializamos las Notificaciones y el Tiempo Real
    if (typeof cargarCampana === 'function') {
        cargarCampana(); // Carga inicial al abrir la web
        
        // ✨ MAGIA DE TIEMPO REAL: Consultar cada 10 segundos (10000 milisegundos)
        setInterval(() => {
            const dropdown = document.getElementById("campana-dropdown");
            
            // Truco de UX: Si el usuario tiene la campanita abierta leyendo, 
            // evitamos recargar para que no le parpadee la lista en la cara.
            if (dropdown && dropdown.style.display === "block") {
                return; 
            }
            
            cargarCampana(); // Consulta silenciosa al servidor
        }, 10000); 
    }
}

document.addEventListener("DOMContentLoaded", cargarPlantillaComun);

// --- FUNCIONES DE UTILIDAD ---
function escapeHTML(texto) {
    const div = document.createElement('div');
    div.textContent = texto == null ? '' : String(texto);
    return div.innerHTML;
}

function decodificarToken(token) {
    try {
        // El JWT usa base64url (con '-' y '_', sin relleno) y el JSON va en UTF-8:
        // lo normalizamos para que atob no falle y los nombres con tildes se lean bien.
        let payloadBase64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        while (payloadBase64.length % 4) payloadBase64 += '=';
        const bytes = Uint8Array.from(atob(payloadBase64), c => c.charCodeAt(0));
        return JSON.parse(new TextDecoder('utf-8').decode(bytes));
    } catch (error) {
        return null;
    }
}

// --- CONTROL DE ACCESO ---
function verificarAcceso() {
    const token = localStorage.getItem("token");
    if (!token) { 
        window.location.href = "/login"; 
        return false; 
    }

    const datosUsuario = decodificarToken(token);
    
    // Validar expiración del token
    if (datosUsuario && datosUsuario.exp) {
        const tiempoExpiracion = datosUsuario.exp * 1000; // a milisegundos
        if (Date.now() >= tiempoExpiracion) {
            console.warn("Sesión caducada. Redirigiendo al login...");
            localStorage.removeItem('token');
            window.location.href = "/login";
            return false;
        }
    } else if (!datosUsuario) {
        localStorage.removeItem('token');
        window.location.href = "/login";
        return false;
    }

    // Si llegamos aquí, el token es válido. Procedemos a inyectar UI.
    // 1. Inyectamos el Nombre
    if (document.getElementById("nombre-usuario")) {
        document.getElementById("nombre-usuario").innerText = datosUsuario.nombre;
    }
    
    // ✨ 2. EL CAMBIO: Ahora inyectamos el SECTOR en lugar de los roles
    if (document.getElementById("roles-usuario")) {
        // Usa datosUsuario.sector_nombre o datosUsuario.sector según cómo lo envíe tu backend
        document.getElementById("roles-usuario").innerText = datosUsuario.sector || "Sin Sector";
    }
    const roles = datosUsuario.roles || [];
    const esAdmin = roles.includes("Administrador");

    aplicarPermisosSidebar(roles);

    const pagina = paginaDeRuta(window.location.pathname);
    if (pagina && !esAdmin && !tienePermiso(roles, pagina.codigo)) {
        window.location.href = "/";
        return false;
    }

    mostrarAvatarNavbar();

    return true;
}

async function mostrarAvatarNavbar() {
    const contenedor = document.querySelector(".user-circle-icon");
    if (!contenedor) return;

    let foto = localStorage.getItem("foto_perfil") || "";
    const token = localStorage.getItem("token");
    try {
        const res = await fetch(`${API_URL}/usuarios/me`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
            const datos = await res.json();
            foto = datos.foto || foto;
            localStorage.setItem("foto_perfil", foto);
            localStorage.setItem("nombre_perfil", `${datos.nombre || ""} ${datos.apellido || ""}`.trim());
        }
    } catch (e) {
        /* Offline: usamos la última foto guardada en localStorage */
    }

    if (foto) {
        contenedor.style.backgroundImage = `url("${foto}")`;
        contenedor.style.backgroundSize = "cover";
        contenedor.style.backgroundPosition = "center";
        contenedor.innerHTML = "";
    }
}

async function cerrarSesion() {
    const token = localStorage.getItem("token");
    if (token) {
        try { await fetch(`${API_URL}/logout`, { method: "POST", headers: { "Authorization": `Bearer ${token}` } }); } 
        catch (e) { console.log("Servidor inalcanzable al salir"); }
    }
    localStorage.removeItem("token");
    sessionStorage.removeItem("estadoChat"); 
    window.location.href = "/login";
}

// --- MENÚ DE PERFIL EN NAVBAR ---
function toggleMenuPerfil(event) {
    if (event) event.stopPropagation();
    const dropdown = document.getElementById("perfil-dropdown");
    if (dropdown) dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
}

window.addEventListener("click", () => {
    const dropdown = document.getElementById("perfil-dropdown");
    if (dropdown) dropdown.style.display = "none";
});