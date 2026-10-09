
/* ==========================================================
   INICIO.JS
   Sistema Inteligente de Gestión Documental
   Sofitel Mexico City Reforma
   ========================================================== */

document.addEventListener("DOMContentLoaded", function () {

    /* ======================================================
       MENÚ DEL USUARIO
       ====================================================== */

    const userMenuButton = document.getElementById("userMenuButton");
    const userDropdown = document.getElementById("userDropdown");

    if (userMenuButton && userDropdown) {

        userMenuButton.addEventListener("click", function (event) {
            event.stopPropagation();

            const isOpen = userDropdown.classList.toggle("show");

            userMenuButton.setAttribute(
                "aria-expanded",
                String(isOpen)
            );
        });

        document.addEventListener("click", function (event) {

            if (
                !userDropdown.contains(event.target) &&
                !userMenuButton.contains(event.target)
            ) {
                userDropdown.classList.remove("show");
                userMenuButton.setAttribute("aria-expanded", "false");
            }
        });

        document.addEventListener("keydown", function (event) {

            if (event.key === "Escape") {
                userDropdown.classList.remove("show");
                userMenuButton.setAttribute("aria-expanded", "false");
            }
        });

    }


    /* ======================================================
       SIDEBAR PLEGABLE
       ====================================================== */

    const dashboardLayout = document.getElementById("dashboardLayout");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarToggleIcon = document.getElementById("sidebarToggleIcon");

    if (dashboardLayout && sidebarToggle) {

        sidebarToggle.addEventListener("click", function () {

            const isCollapsed = dashboardLayout.classList.toggle(
                "sidebar-collapsed"
            );

            sidebarToggle.setAttribute(
                "aria-expanded",
                String(!isCollapsed)
            );

            sidebarToggle.setAttribute(
                "aria-label",
                isCollapsed
                    ? "Expandir menú lateral"
                    : "Contraer menú lateral"
            );

            sidebarToggle.setAttribute(
                "title",
                isCollapsed
                    ? "Expandir menú"
                    : "Contraer menú"
            );

            if (sidebarToggleIcon) {

                sidebarToggleIcon.className = isCollapsed
                    ? "bi bi-layout-sidebar-inset-reverse"
                    : "bi bi-layout-sidebar-inset";

            }

        });

    }

});
