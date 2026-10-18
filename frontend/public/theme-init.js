// Aplica el tema guardado antes del primer pintado: sin esto, la app siempre
// arrancaría en claro y saltaría a oscuro un instante después (FOUC). Login y
// registro se saltan esto a propósito: siempre van en claro (AuthLayout,
// useForceLightTheme), así que aplicar oscuro aquí solo provocaría el parpadeo
// contrario nada más montar React.
//
// Va en un fichero y no en línea en index.html: la CSP de producción solo admite
// scripts del propio origen (deploy/web/nginx.conf). Se carga síncrono, sin
// `type="module"` ni `defer`, para que corra antes de pintar.
(function () {
  try {
    if (location.pathname === "/login" || location.pathname === "/register") return;
    var stored = localStorage.getItem("theme");
    var dark =
      stored === "dark" ||
      (stored !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    if (dark) document.documentElement.classList.add("dark");
  } catch (e) {}
})();
