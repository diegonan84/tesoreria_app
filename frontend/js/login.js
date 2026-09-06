// ============================================================================
// login.js - WIDGETS Y UX DE LA PANTALLA DE INICIO DE SESIÓN
// ============================================================================

function iniciarReloj() {
    const reloj = document.getElementById("login-hora");
    const fechaEl = document.getElementById("login-fecha");
    if (!reloj || !fechaEl) return;

    setInterval(() => {
        const ahora = new Date();
        reloj.innerText = ahora.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
        let textoFecha = ahora.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'short' });
        fechaEl.innerText = textoFecha.charAt(0).toUpperCase() + textoFecha.slice(1);
    }, 1000);
}

// Función auxiliar para traducir los códigos del clima a iconos y texto
function obtenerIconoClima(codigo) {
    let icono = "🌤️"; let desc = "Despejado";
    if (codigo === 0) { icono = "☀️"; desc = "Despejado"; }
    else if (codigo >= 1 && codigo <= 3) { icono = "⛅"; desc = "P. Nublado"; }
    else if (codigo >= 45 && codigo <= 48) { icono = "🌫️"; desc = "Neblina"; }
    else if (codigo >= 51 && codigo <= 67) { icono = "🌧️"; desc = "Llovizna"; }
    else if (codigo >= 71 && codigo <= 82) { icono = "🌧️"; desc = "Lluvia"; }
    else if (codigo >= 95) { icono = "⛈️"; desc = "Tormenta"; }
    return { icono, desc };
}

// 1. CLIMA (Actual + Diario + Por Hora)
async function cargarClima() {
    // Pedimos actual, el diario (min/max) y el por hora (hourly) para 1 día.
    const url = "https://api.open-meteo.com/v1/forecast?latitude=-34.61&longitude=-58.38&current_weather=true&daily=temperature_2m_max,temperature_2m_min&hourly=weathercode&timezone=America%2FArgentina%2FBuenos_Aires&forecast_days=1";
    
    try {
        const res = await fetch(url);
        const data = await res.json();
        
        // --- 1. Clima Actual ---
        const tempActual = Math.round(data.current_weather.temperature);
        const tempMin = Math.round(data.daily.temperature_2m_min[0]);
        const tempMax = Math.round(data.daily.temperature_2m_max[0]);
        const climaActual = obtenerIconoClima(data.current_weather.weathercode);

        document.getElementById("clima-temp").innerText = `${tempActual}°`;
        document.getElementById("clima-minmax").innerText = `Min: ${tempMin}° | Máx: ${tempMax}°`;
        document.getElementById("clima-icono").innerText = climaActual.icono;
        document.getElementById("clima-desc").innerText = climaActual.desc;

        // --- 2. Pronóstico del Día ---
        // Extraemos los códigos de clima a las 9hs (Mañana), 15hs (Tarde) y 21hs (Noche)
        const climaManana = obtenerIconoClima(data.hourly.weathercode[9]);
        document.getElementById("clima-icono-manana").innerText = climaManana.icono;
        document.getElementById("clima-desc-manana").innerText = climaManana.desc;

        const climaTarde = obtenerIconoClima(data.hourly.weathercode[15]);
        document.getElementById("clima-icono-tarde").innerText = climaTarde.icono;
        document.getElementById("clima-desc-tarde").innerText = climaTarde.desc;

        const climaNoche = obtenerIconoClima(data.hourly.weathercode[21]);
        document.getElementById("clima-icono-noche").innerText = climaNoche.icono;
        document.getElementById("clima-desc-noche").innerText = climaNoche.desc;

    } catch (error) {
        document.getElementById("clima-temp").innerText = "--°";
        console.error("Error al cargar el clima:", error);
    }
}

// 2. NOTICIAS RSS (tarjetas con imagen estilo MSN, fuente random + scroll automático)
let scrollInterval = null;
let scrollPausado = false;

function iniciarScrollAutomatico() {
    const contenedor = document.getElementById("contenedor-rss");
    if (!contenedor) return;

    if (scrollInterval) clearInterval(scrollInterval);

    scrollInterval = setInterval(() => {
        if (scrollPausado) return;
        const maxScroll = contenedor.scrollHeight - contenedor.clientHeight;
        if (maxScroll <= 0) return;
        contenedor.scrollTop += 1;
        if (contenedor.scrollTop >= maxScroll) {
            contenedor.scrollTop = 0;
        }
    }, 40); // ~25px por segundo, velocidad de lectura suave
}

async function cargarRSS() {
    const contenedor = document.getElementById("contenedor-rss");
    if (!contenedor) return;

    try {
        // Pausar el scroll mientras se recargan las noticias
        scrollPausado = true;

        const res = await fetch("/api/rss");
        const data = await res.json();

        // Cabecera que indica la fuente y categoría
        const cabecera = `<div style="margin-bottom: 8px; text-align: left; font-size: 0.72rem; color: #9ee4d3;">
            <span style="font-weight: bold; text-transform: uppercase; color: #9ee4d3;">${escapeHTML(data.categoria || "")}</span>
            · <span style="text-transform: uppercase;">${escapeHTML(data.fuente || "Noticias")}</span>
        </div>`;

        if (!data.items || data.items.length === 0) {
            contenedor.innerHTML = cabecera + "<div style='font-size: 0.85rem; color: #e0e6e8; text-align: center; margin-top: 20px;'>No se pudieron cargar las noticias.</div>";
            return;
        }

        contenedor.innerHTML = cabecera;

        const items = data.items;

        // NOTICIA PRINCIPAL (portada grande con imagen arriba)
        const principal = items[0];
        const imgPrincipal = principal.image
            ? `<img src="${escapeHTML(principal.image)}" alt="" style="width: 100%; height: 110px; object-fit: cover; border-radius: 6px 6px 0 0; display: block;">`
            : "";
        contenedor.innerHTML += `
            <a href="${escapeHTML(principal.link)}" target="_blank" rel="noopener noreferrer" style="display: block; background: rgba(0,0,0,0.25); border-radius: 8px; overflow: hidden; text-decoration: none; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
                ${imgPrincipal}
                <div style="padding: 10px 12px;">
                    <div style="font-size: 0.9rem; font-weight: bold; color: white; line-height: 1.3; margin-bottom: 4px;">${escapeHTML(principal.title)}</div>
                    <div style="font-size: 0.75rem; color: #b8c2cc; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${escapeHTML(principal.description)}</div>
                </div>
            </a>
        `;

        // RESTO DE NOTICIAS (minitarjetas con imagen a la izquierda)
        items.slice(1).forEach(item => {
            const img = item.image
                ? `<img src="${escapeHTML(item.image)}" alt="" style="width: 52px; height: 52px; object-fit: cover; border-radius: 6px; flex-shrink: 0;">`
                : "";
            contenedor.innerHTML += `
                <a href="${escapeHTML(item.link)}" target="_blank" rel="noopener noreferrer" style="display: flex; gap: 10px; align-items: center; background: rgba(0,0,0,0.25); padding: 8px; border-radius: 8px; border-left: 3px solid #9ee4d3; text-decoration: none; transition: background 0.2s;">
                    ${img}
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-size: 0.8rem; font-weight: bold; color: white; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${escapeHTML(item.title)}</div>
                    </div>
                </a>
            `;
        });

        // Reiniciar desde arriba y reanudar el scroll
        contenedor.scrollTop = 0;
        scrollPausado = false;
        iniciarScrollAutomatico();
    } catch (error) {
        contenedor.innerHTML = "<div style='font-size: 0.85rem; color: #e0e6e8; text-align: center; margin-top: 20px;'>No se pudieron cargar las noticias.</div>";
        console.error("Error al cargar RSS:", error);
        scrollPausado = false;
    }
}

// Pausar el scroll al pasar el mouse, reanudar al salir
document.addEventListener('mouseover', e => {
    if (e.target.closest && e.target.closest('#contenedor-rss')) scrollPausado = true;
});
document.addEventListener('mouseout', e => {
    if (e.target.closest && e.target.closest('#contenedor-rss')) scrollPausado = false;
});

document.addEventListener('DOMContentLoaded', () => {
    iniciarReloj();
    cargarClima();
    cargarRSS(); // fuente random en cada carga
    setInterval(cargarRSS, 45000); // nueva fuente random cada 45 segundos
});