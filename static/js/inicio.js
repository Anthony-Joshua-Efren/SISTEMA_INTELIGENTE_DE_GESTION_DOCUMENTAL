console.log("inicio.js cargado correctamente");
document.addEventListener("DOMContentLoaded", function () {

    const userMenuButton = document.getElementById("userMenuButton");
    const userDropdown = document.getElementById("userDropdown");

    if (!userMenuButton || !userDropdown) {
        return;
    }

    userMenuButton.addEventListener("click", function (event) {

        event.stopPropagation();

        const isOpen = userDropdown.classList.toggle("show");

        userMenuButton.setAttribute(
            "aria-expanded",
            isOpen ? "true" : "false"
        );
    });


    document.addEventListener("click", function (event) {

        if (!userDropdown.contains(event.target)) {

            userDropdown.classList.remove("show");

            userMenuButton.setAttribute(
                "aria-expanded",
                "false"
            );
        }
    });

});

/* ==========================================================
   SIDEBAR PLEGABLE
   Sistema Inteligente de Gestión Documental - Sofitel
   ========================================================== */

document.addEventListener("DOMContentLoaded", function () {

    const dashboardLayout = document.getElementById("dashboardLayout");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarToggleIcon = document.getElementById("sidebarToggleIcon");

    if (!dashboardLayout || !sidebarToggle) {
        return;
    }

    // Contraer o expandir el menú lateral
    sidebarToggle.addEventListener("click", function () {

        const isCollapsed = dashboardLayout.classList.toggle(
            "sidebar-collapsed"
        );

        // Actualizar accesibilidad y descripción del botón
        sidebarToggle.setAttribute(
            "aria-expanded",
            String(!isCollapsed)
        );

        sidebarToggle.setAttribute(
            "aria-label",
            isCollapsed ? "Expandir menú lateral" : "Contraer menú lateral"
        );

        sidebarToggle.setAttribute(
            "title",
            isCollapsed ? "Expandir menú" : "Contraer menú"
        );

        // Cambiar el icono
        if (sidebarToggleIcon) {
            sidebarToggleIcon.className = isCollapsed
                ? "bi bi-layout-sidebar-inset-reverse"
                : "bi bi-layout-sidebar-inset";
        }

    });

});
