document.addEventListener("DOMContentLoaded", function () {
    const carousel = document.querySelector(".carousel");
    const slides = document.querySelectorAll(".video-slide");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");

    let index = 0;
    const totalSlides = slides.length;

    function updateCarousel() {
        const translateValue = `translateX(-${index * 100}%)`;
        carousel.style.transform = translateValue;
    }

    prevBtn.addEventListener("click", function () {
        index = (index > 0) ? index - 1 : totalSlides - 1;
        updateCarousel();
    });

    nextBtn.addEventListener("click", function () {
        index = (index < totalSlides - 1) ? index + 1 : 0;
        updateCarousel();
    });

    // Iniciar correctamente en la posición 0
    updateCarousel();

    window.addEventListener("resize", function () {
        index = 0; // Resetear índice en caso de cambio de tamaño
        updateCarousel();
    });
});
