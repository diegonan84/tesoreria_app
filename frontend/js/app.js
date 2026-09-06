// ============================================================================
// app.js - NÚCLEO Y CONFIGURACIÓN GLOBAL
// ============================================================================
const API_URL = "http://localhost:8000"; 

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
    
    return response; 
};

// --- FUNCIÓN MAESTRA (PLANTILLA COMÚN Y CACHE BUSTER) ---
async function cargarPlantillaComun() {
    const path = window.location.pathname;

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
                if (path.includes("/usuarios")) subtitulo.innerText = "Gestión de Usuarios";
                else if (path.includes("/auditoria")) subtitulo.innerText = "Auditoría de Accesos";
                else if (path.includes("/patrimonio")) subtitulo.innerText = "Patrimonio";
                else if (path.includes("/perfil")) subtitulo.innerText = "Mi Perfil";
                else if (path.includes("/notificaciones")) subtitulo.innerText = "Gestión de Avisos";
                else subtitulo.innerText = "Panel Operativo";
            }
        }

        // 2. Inyectar la Sidebar
        const resSidebar = await fetch('/archivos/componentes/sidebar.html' + cacheBuster);
        if (resSidebar.ok && document.getElementById("global-sidebar")) {
            document.getElementById("global-sidebar").innerHTML = await resSidebar.text();
        }

        // 3. Inyectar el Widget de Chat
        const resChat = await fetch('/archivos/componentes/chat.html' + cacheBuster);
        if (resChat.ok && document.getElementById("global-chat")) {
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
    
    // Inicializamos el Chat
    if (typeof inicializarChat === 'function') inicializarChat(); 

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
        const payloadBase64 = token.split('.')[1];
        return JSON.parse(atob(payloadBase64));
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

    const menuUsuarios = document.getElementById("menu-usuarios");
    if (menuUsuarios && !esAdmin) menuUsuarios.style.display = "none";
    
    const menuPatrimonio = document.getElementById("menu-patrimonio");
    if (menuPatrimonio && !esAdmin && !roles.includes("Patrimonio")) menuPatrimonio.style.display = "none";

    const menuNotif = document.getElementById("menu-notificaciones");
    if (menuNotif && esAdmin) menuNotif.style.display = "block";
    
    const path = window.location.pathname;
    if ((path === "/usuarios" || path === "/auditoria" || path === "/notificaciones") && !esAdmin) {
        window.location.href = "/";
        return false;
    }

    return true;
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