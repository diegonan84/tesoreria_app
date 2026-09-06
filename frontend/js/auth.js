// ============================================================================
// auth.js - LOGIN, REGISTRO Y GESTIÓN DE CUENTA PROPIA
// ============================================================================

function hacerLogin(event) { iniciarSesion(event); }

async function iniciarSesion(event) {
    if (event) event.preventDefault();
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "X-PC-Nombre": navigator.platform || "Desconocido",
                "X-PC-Usuario": window.localStorage.getItem('usuario_pc') || "Desconocido"
            },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) {
            localStorage.setItem("token", data.access_token);
            window.location.href = "/";
        } else {
            alert(data.detail || "Error al iniciar sesión");
        }
    } catch (error) { alert("Error de conexión con el servidor."); }
}

async function registrarUsuario(event) {
    if (event) event.preventDefault(); 
    
    const nombre = document.getElementById("reg-nombre").value;
    const apellido = document.getElementById("reg-apellido").value;
    const cuil = document.getElementById("reg-cuil").value;
    const reparticion = document.getElementById("reg-reparticion").value;
    const email = document.getElementById("reg-email").value;
    const password = document.getElementById("reg-password").value;
    const confirmarPassword = document.getElementById("reg-confirm").value;

    if (password !== confirmarPassword) {
        alert("Las contraseñas no coinciden. Por favor, verifícalas.");
        return; 
    }

    try {
        const res = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nombre, apellido, cuil, email, reparticion, password, confirm_password: confirmarPassword })
        });
        const data = await res.json();
        if (res.ok) {
            alert("Registro exitoso. Su cuenta está pendiente de aprobación.");
            window.location.href = "/login";
        } else {
            if (Array.isArray(data.detail)) {
                const errores = data.detail.map(err => `👉 Campo '${err.loc[err.loc.length-1]}': ${err.msg}`).join('\n');
                alert("Datos incorrectos o incompletos:\n" + errores);
            } else {
                alert(data.detail || "Error al registrarse.");
            }
        }
    } catch (error) { alert("Error de conexión."); }
}


async function guardarCambioClave(event) {
    event.preventDefault();
    const claveActual = document.getElementById("perf-actual").value;
    const nuevaClave = document.getElementById("perf-nueva").value;
    const confirmarClave = document.getElementById("perf-confirmar").value;

    if (nuevaClave !== confirmarClave) return alert("La nueva contraseña y su confirmación no coinciden.");

    try {
        const res = await fetch(`${API_URL}/usuarios/me/cambiar-clave`, {
            method: "PUT",
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}`, "Content-Type": "application/json" },
            body: JSON.stringify({ clave_actual: claveActual, nueva_clave: nuevaClave, confirmar_clave: confirmarClave })
        });
        const data = await res.json();
        if (res.ok) {
            alert("Contraseña modificada exitosamente. Deberá iniciar sesión nuevamente.");
            localStorage.removeItem("token");
            window.location.href = "/login";
        } else alert(data.detail || "Error al actualizar la contraseña.");
    } catch (error) { alert("Error de conexión con el servidor."); }
}

function cargarDatosPantallaPerfil() {
    const token = localStorage.getItem("token");
    const datos = decodificarToken(token); // Requiere app.js cargado antes
    if (datos && document.getElementById("perf-nombre")) {
        document.getElementById("perf-nombre").value = datos.nombre || "";
        document.getElementById("perf-email").value = datos.sub || "";
        document.getElementById("perf-roles").value = datos.roles ? datos.roles.join(", ") : "";
    }
}