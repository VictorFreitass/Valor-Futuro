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

    // Property detail gallery (carousel + lightbox)
    const galleryRoot = document.querySelector('.gallery');
    if (galleryRoot && galleryRoot.querySelectorAll('.gallery-image').length > 0) {
        new PropertyGallery(galleryRoot);
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

    // Basic numeric guard on price/area filters
    document.querySelectorAll('.filters input[type="number"]').forEach(input => {
        input.addEventListener('input', () => {
            if (input.value && Number(input.value) < 0) input.value = 0;
        });
    });
});


class PropertyGallery {
    constructor(root) {
        this.root = root;
        this.images = Array.from(root.querySelectorAll('.gallery-image'));
        this.thumbs = Array.from(root.querySelectorAll('.gallery-thumb'));
        this.counterCurrent = root.querySelector('.gallery-counter-current');
        this.current = 0;
        this.bind();
    }

    bind() {
        const prev = this.root.querySelector('.gallery-arrow-prev');
        const next = this.root.querySelector('.gallery-arrow-next');
        const expand = this.root.querySelector('.gallery-expand');

        prev && prev.addEventListener('click', (e) => { e.stopPropagation(); this.go(-1); });
        next && next.addEventListener('click', (e) => { e.stopPropagation(); this.go(+1); });

        this.thumbs.forEach((thumb, i) => {
            thumb.addEventListener('click', () => this.set(i));
        });

        this.images.forEach(img => {
            img.addEventListener('click', () => this.openLightbox());
        });
        expand && expand.addEventListener('click', (e) => { e.stopPropagation(); this.openLightbox(); });

        // Touch swipe
        const stage = this.root.querySelector('.gallery-stage');
        if (stage) this.attachSwipe(stage, (dir) => this.go(dir));
    }

    go(delta) {
        if (this.images.length < 2) return;
        const len = this.images.length;
        this.set((this.current + delta + len) % len);
    }

    set(index) {
        if (this.images.length === 0) return;
        this.images[this.current].classList.remove('active');
        if (this.thumbs[this.current]) this.thumbs[this.current].classList.remove('active');
        this.current = index;
        this.images[this.current].classList.add('active');
        if (this.thumbs[this.current]) {
            this.thumbs[this.current].classList.add('active');
            this.thumbs[this.current].scrollIntoView({ inline: 'center', behavior: 'smooth', block: 'nearest' });
        }
        if (this.counterCurrent) this.counterCurrent.textContent = String(index + 1);
    }

    attachSwipe(el, onSwipe) {
        let startX = 0, startY = 0, active = false;
        el.addEventListener('touchstart', (e) => {
            const t = e.touches[0];
            startX = t.clientX;
            startY = t.clientY;
            active = true;
        }, { passive: true });
        el.addEventListener('touchend', (e) => {
            if (!active) return;
            active = false;
            const t = e.changedTouches[0];
            const dx = t.clientX - startX;
            const dy = t.clientY - startY;
            if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) {
                onSwipe(dx > 0 ? -1 : +1);
            }
        }, { passive: true });
    }

    openLightbox() {
        if (this.images.length === 0) return;

        const overlay = document.createElement('div');
        overlay.className = 'lightbox';
        overlay.innerHTML = `
            <button type="button" class="lightbox-close" aria-label="Fechar">×</button>
            <button type="button" class="lightbox-arrow lightbox-arrow-prev" aria-label="Anterior">‹</button>
            <button type="button" class="lightbox-arrow lightbox-arrow-next" aria-label="Seguinte">›</button>
            <img class="lightbox-image" alt="">
            <div class="lightbox-counter"><span class="lightbox-counter-current"></span> / ${this.images.length}</div>
        `;

        const img = overlay.querySelector('.lightbox-image');
        const counter = overlay.querySelector('.lightbox-counter-current');
        const arrowPrev = overlay.querySelector('.lightbox-arrow-prev');
        const arrowNext = overlay.querySelector('.lightbox-arrow-next');
        const closeBtn = overlay.querySelector('.lightbox-close');

        let lbIndex = this.current;

        const render = () => {
            const src = this.images[lbIndex].getAttribute('src');
            img.classList.add('fading');
            const swap = () => {
                img.src = src;
                counter.textContent = String(lbIndex + 1);
                requestAnimationFrame(() => img.classList.remove('fading'));
            };
            // Pre-decode for smooth swap
            const probe = new Image();
            probe.onload = swap;
            probe.onerror = swap;
            probe.src = src;
        };

        const move = (delta) => {
            const len = this.images.length;
            if (len < 2) return;
            lbIndex = (lbIndex + delta + len) % len;
            render();
        };

        const close = () => {
            overlay.remove();
            document.removeEventListener('keydown', onKey);
            // Sincroniza a galeria principal com a posição final do lightbox
            this.set(lbIndex);
        };

        const onKey = (e) => {
            if (e.key === 'Escape') close();
            else if (e.key === 'ArrowLeft') move(-1);
            else if (e.key === 'ArrowRight') move(+1);
        };

        // Hide arrows for single image
        if (this.images.length < 2) {
            arrowPrev.style.display = 'none';
            arrowNext.style.display = 'none';
            overlay.querySelector('.lightbox-counter').style.display = 'none';
        }

        arrowPrev.addEventListener('click', (e) => { e.stopPropagation(); move(-1); });
        arrowNext.addEventListener('click', (e) => { e.stopPropagation(); move(+1); });
        closeBtn.addEventListener('click', close);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
        img.addEventListener('click', (e) => e.stopPropagation());

        // Swipe in lightbox
        this.attachSwipe(img, move);
        this.attachSwipe(overlay, move);

        document.addEventListener('keydown', onKey);
        document.body.appendChild(overlay);
        render();
    }
}
