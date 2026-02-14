// Autoplay audio quando il post è visibile
const posts = document.querySelectorAll(".post");

if ("IntersectionObserver" in window) {
    let observer = new IntersectionObserver(
        entries => {
            entries.forEach(entry => {
                const audio = entry.target.querySelector("audio");
                if (!audio) return;

                if (entry.isIntersecting) {
                    audio.currentTime = 0;
                    audio.play().catch(() => {});
                } else {
                    audio.pause();
                }
            });
        },
        { threshold: 0.8 }
    );

    posts.forEach(post => observer.observe(post));
}
