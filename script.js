const posts = document.querySelectorAll(".post")

let observer = new IntersectionObserver(
    entries => {
        entries.forEach(entry => {
            const audio = entry.target.querySelector("audio")
            if (!audio) return

            if (entry.isIntersecting) {
                audio.currentTime = 0
                audio.play()
            } else {
                audio.pause()
            }
        })
    },
    { threshold: 0.8 }
)

posts.forEach(post => observer.observe(post))
