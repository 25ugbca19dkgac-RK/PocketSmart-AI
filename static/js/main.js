/* ============================================================
   PocketSmart AI – Main JavaScript
   ============================================================ */

// ── Navigation ──
document.addEventListener('DOMContentLoaded', () => {
    const navbar = document.getElementById('navbar');
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');

    // Scroll effect
    window.addEventListener('scroll', () => {
        navbar?.classList.toggle('scrolled', window.scrollY > 30);
    });

    // Mobile toggle
    navToggle?.addEventListener('click', () => {
        navLinks?.classList.toggle('active');
    });

    // Close mobile nav on link click
    navLinks?.querySelectorAll('.nav-link, .nav-btn').forEach(link => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('active');
        });
    });

    // Intersection Observer for section animations
    const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -50px 0px' };
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    document.querySelectorAll('.animate-on-scroll').forEach(el => observer.observe(el));
});


// ── Loading Overlay ──
function showLoading(message = 'Generating AI recommendations...', subtext = 'This may take a few seconds') {
    let overlay = document.getElementById('loadingOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">${message}</div>
            <div class="loading-subtext">${subtext}</div>
        `;
        document.body.appendChild(overlay);
    } else {
        overlay.querySelector('.loading-text').textContent = message;
        overlay.querySelector('.loading-subtext').textContent = subtext;
    }
    overlay.classList.add('active');
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.remove('active');
}


// ── Markdown Renderer (simple) ──
function renderMarkdown(text) {
    if (!text) return '';
    let html = text
        // Headers
        .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Bold & Italic
        .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Unordered lists
        .replace(/^\* (.+)$/gm, '<li>$1</li>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        // Ordered lists
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>.*?<\/li>)(\s*<br>\s*)?(<li>)/g, '$1$3');
    html = html.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');

    // Simple table support
    if (html.includes('|')) {
        html = html.replace(
            /(?:<br>|\n)?(\|.+\|)(?:<br>|\n)(\|[-: |]+\|)(?:<br>|\n)((?:\|.+\|(?:<br>|\n)?)+)/g,
            (match, header, separator, body) => {
                const headers = header.split('|').filter(c => c.trim());
                const rows = body.split(/<br>|\n/).filter(r => r.includes('|'));
                let table = '<table><thead><tr>';
                headers.forEach(h => { table += `<th>${h.trim()}</th>`; });
                table += '</tr></thead><tbody>';
                rows.forEach(row => {
                    const cells = row.split('|').filter(c => c.trim());
                    table += '<tr>';
                    cells.forEach(c => { table += `<td>${c.trim()}</td>`; });
                    table += '</tr>';
                });
                table += '</tbody></table>';
                return table;
            }
        );
    }

    return `<p>${html}</p>`;
}


// ── Display Recommendations ──
function displayResults(data, containerId = 'resultsContainer') {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = `
        <div class="result-card">
            <h3><i class="fas fa-sparkles"></i> AI Recommendations</h3>
            <div class="ai-content">
                ${renderMarkdown(data.ai_recommendation)}
            </div>
        </div>
    `;

    // Shopping links
    if (data.shopping_links && data.shopping_links.length > 0) {
        html += `
            <div class="result-card">
                <h3><i class="fas fa-shopping-cart"></i> Shop These Recommendations</h3>
                <div class="links-grid">
                    ${data.shopping_links.map(link => `
                        <a href="${link.url}" target="_blank" rel="noopener" class="shop-link">
                            <span class="platform-name">${link.platform}</span>
                            <span>${link.keyword}</span>
                            <i class="fas fa-external-link-alt" style="margin-left:auto; font-size:0.7rem;"></i>
                        </a>
                    `).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}


// ── Counter Controls ──
function initCounters() {
    document.querySelectorAll('.counter-control').forEach(group => {
        const input = group.querySelector('input');
        const minusBtn = group.querySelector('.counter-minus');
        const plusBtn = group.querySelector('.counter-plus');

        minusBtn?.addEventListener('click', () => {
            const val = parseInt(input.value) || 0;
            if (val > 0) input.value = val - 1;
        });

        plusBtn?.addEventListener('click', () => {
            const val = parseInt(input.value) || 0;
            input.value = val + 1;
        });
    });
}

document.addEventListener('DOMContentLoaded', initCounters);


// ── File Upload Display ──
function handleFileUpload(inputId, displayId) {
    const input = document.getElementById(inputId);
    const display = document.getElementById(displayId);
    if (!input || !display) return;

    input.addEventListener('change', () => {
        if (input.files.length > 0) {
            display.textContent = input.files[0].name;
        } else {
            display.textContent = '';
        }
    });
}


// ── History Toggle ──
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => {
            item.classList.toggle('expanded');
        });
    });
});


// ── Smooth scroll for anchor links ──
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const target = document.querySelector(anchor.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
});
