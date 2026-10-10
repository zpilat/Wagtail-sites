(function () {
    "use strict";

    const button = document.querySelector(".recipe-print-button");
    if (button) {
        button.addEventListener("click", function () {
            window.print();
        });
        button.classList.remove("d-none");
    }
})();
