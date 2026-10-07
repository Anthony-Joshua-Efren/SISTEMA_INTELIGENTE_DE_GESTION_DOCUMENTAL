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