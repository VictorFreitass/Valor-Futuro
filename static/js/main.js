// Valor Futuro — interactivity for the luxury real estate site

document.addEventListener('DOMContentLoaded', () => {
    // Header shrinks on scroll
    const header = document.getElementById('site-header');
    if (header) {
        const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 30);
        onScroll();
        window.addEventListener('scroll', onScroll, { passive: true });
    }

    // Smooth-scroll for in-page anchors (e.g. "Em Destaque" button)
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener('click', (e) => {
            const id = link.getAttribute('href');
            if (id.length <= 1) return;
            const target = document.querySelector(id);
            if (!target) return;
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    // Property detail: clicking a thumbnail swaps the main image
    const mainImage = document.getElementById('main-image');
    if (mainImage) {
        document.querySelectorAll('.property-thumbnail').forEach(thumb => {
            thumb.addEventListener('click', () => {
                const full = thumb.dataset.full || thumb.src;
                const previous = mainImage.src;
                mainImage.src = full;
                thumb.dataset.full = previous;
                document.querySelectorAll('.property-thumbnail').forEach(t => t.classList.remove('active'));
                thumb.classList.add('active');
            });
        });

        mainImage.addEventListener('click', () => openLightbox(mainImage.src, mainImage.alt));
    }

    // Auto-dismiss flash messages after 5s
    const flash = document.getElementById('flash-stack');
    if (flash) {
        setTimeout(() => {
            flash.querySelectorAll('.alert').forEach(el => {
                el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                el.style.opacity = '0';
                el.style.transform = 'translateX(20px)';
                setTimeout(() => el.remove(), 500);
            });
        }, 5000);
    }

    // Reveal-on-scroll
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -50px 0px' });

        document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
    } else {
        document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
    }

    // Basic numeric guard on price/area filters (prevent silly negative values)
    document.querySelectorAll('.filters input[type="number"]').forEach(input => {
        input.addEventListener('input', () => {
            if (input.value && Number(input.value) < 0) input.value = 0;
        });
    });
});

function openLightbox(src, alt) {
    const lightbox = document.createElement('div');
    lightbox.className = 'lightbox';
    const img = document.createElement('img');
    img.src = src;
    img.alt = alt || '';
    lightbox.appendChild(img);

    const close = () => lightbox.remove();
    lightbox.addEventListener('click', close);
    document.addEventListener('keydown', function onEsc(e) {
        if (e.key === 'Escape') {
            close();
            document.removeEventListener('keydown', onEsc);
        }
    });

    document.body.appendChild(lightbox);
}
