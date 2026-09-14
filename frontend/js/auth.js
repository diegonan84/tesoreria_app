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

function inicialesAvatar(nombre) {
    if (!nombre) return "?";
    return nombre.split(/\s+/).map(p => p[0]).slice(0, 2).join("").toUpperCase() || "?";
}

function colorAvatar(nombre) {
    let h = 0;
    for (let i = 0; i < nombre.length; i++) h = (h * 31 + nombre.charCodeAt(i)) % 360;
    return `hsl(${h}, 45%, 52%)`;
}

function formatearFecha(fecha) {
    if (!fecha) return "—";
    const d = new Date(fecha);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function aplicarPerfil(datos) {
    const nombreCompleto = `${datos.nombre || ""} ${datos.apellido || ""}`.trim();
    if (document.getElementById("perf-nombre-completo")) {
        document.getElementById("perf-nombre-completo").innerText = nombreCompleto || "Usuario";
    }
    if (document.getElementById("perf-sub")) {
        document.getElementById("perf-sub").innerText = `${datos.reparticion || ""}${datos.puesto ? " · " + datos.puesto : ""}`.trim();
    }
    if (document.getElementById("perf-rol-badge")) {
        document.getElementById("perf-rol-badge").innerText = datos.rol || "Operador";
    }
    if (document.getElementById("perf-estado-badge")) {
        document.getElementById("perf-estado-badge").style.display = datos.aprobado ? "inline-block" : "none";
    }
    if (document.getElementById("perf-pendiente-badge")) {
        document.getElementById("perf-pendiente-badge").style.display = datos.aprobado ? "none" : "inline-block";
    }

    const setValor = (id, valor) => {
        const el = document.getElementById(id);
        if (el) el.value = valor != null ? valor : "—";
    };
    setValor("perf-nombre", nombreCompleto);
    setValor("perf-email", datos.email);
    setValor("perf-cuil", datos.cuil);
    setValor("perf-reparticion", datos.reparticion);
    setValor("perf-puesto", datos.puesto || "—");
    setValor("perf-sector", datos.sector || "—");
    setValor("perf-fecha-alta", formatearFecha(datos.fecha_creacion));
    setValor("perf-equipos", datos.equipos_asignados != null ? datos.equipos_asignados : 0);

    const avatar = document.getElementById("perf-avatar");
    if (avatar) {
        if (datos.foto) {
            avatar.style.backgroundImage = `url("${datos.foto}")`;
            avatar.innerText = "";
        } else {
            avatar.style.backgroundImage = "";
            avatar.style.background = colorAvatar(nombreCompleto);
            avatar.innerText = inicialesAvatar(nombreCompleto);
        }
    }
}

function redimensionarImagen(file, maxLado) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            const lado = maxLado;
            const canvas = document.createElement("canvas");
            canvas.width = lado;
            canvas.height = lado;
            const ctx = canvas.getContext("2d");
            const escala = Math.max(lado / img.width, lado / img.height);
            const w = img.width * escala;
            const h = img.height * escala;
            ctx.drawImage(img, (lado - w) / 2, (lado - h) / 2, w, h);
            resolve(canvas.toDataURL("image/jpeg", 0.9));
        };
        img.onerror = () => reject(new Error("Imagen inválida"));
        img.src = URL.createObjectURL(file);
    });
}

async function cargarDatosPantallaPerfil() {
    const token = localStorage.getItem("token");
    if (!token) return;

    const btnFoto = document.getElementById("btn-foto");
    const inputFoto = document.getElementById("input-foto");
    if (btnFoto && inputFoto) {
        btnFoto.addEventListener("click", () => inputFoto.click());
        inputFoto.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            try {
                const fotoBase64 = await redimensionarImagen(file, 256);
                const avatar = document.getElementById("perf-avatar");
                if (avatar) {
                    avatar.style.backgroundImage = `url("${fotoBase64}")`;
                    avatar.style.backgroundSize = "cover";
                    avatar.innerText = "";
                }
                const res = await fetch(`${API_URL}/usuarios/me/foto`, {
                    method: "PUT",
                    headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
                    body: JSON.stringify({ foto: fotoBase64 })
                });
                const data = await res.json();
                if (!res.ok) {
                    alert(data.detail || "Error al subir la foto");
                    return;
                }
                localStorage.setItem("foto_perfil", data.foto);
                localStorage.setItem("nombre_perfil", document.getElementById("perf-nombre-completo").innerText);
            } catch (err) {
                alert("Error de conexión al subir la foto.");
            }
        });
    }

    try {
        const res = await fetch(`${API_URL}/usuarios/me`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (res.ok) {
            aplicarPerfil(data);
            return;
        }
    } catch (e) {
        console.error("Error cargando perfil:", e);
    }

    const datos = decodificarToken(token);
    if (datos) {
        aplicarPerfil({
            nombre: datos.nombre || "",
            apellido: "",
            email: datos.sub || "",
            rol: datos.roles ? datos.roles.join(", ") : "Operador"
        });
    }
}