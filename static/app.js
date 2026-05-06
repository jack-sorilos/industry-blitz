// Load embedded account data
const allAccounts = JSON.parse(document.getElementById('accounts-data').textContent);
let filteredAccounts = [...allAccounts];
let currentIndex = 0;
const prepCache = {};

function applyFilters() {
    const tier = document.getElementById('filter-tier').value;
    const industries = Array.from(document.querySelectorAll('.industry-checkbox:checked')).map(cb => cb.value);
    const countries = Array.from(document.querySelectorAll('.country-checkbox:checked')).map(cb => cb.value);
    const platforms = Array.from(document.querySelectorAll('.platform-checkbox:checked')).map(cb => cb.value);

    filteredAccounts = allAccounts.filter(a => {
        if (tier && a.priority_tier !== tier) return false;
        if (industries.length > 0 && !industries.includes(a.Industry)) return false;
        if (countries.length > 0 && !countries.includes(a.BillingCountry)) return false;
        if (platforms.length > 0 && !platforms.includes(a.Current_E_Commerce_Platform__c)) return false;
        return true;
    });

    currentIndex = 0;
    renderCard();
    updateCounter();
}

function clearIndustries() {
    document.querySelectorAll('.industry-checkbox').forEach(cb => cb.checked = false);
    applyFilters();
}

function clearPlatforms() {
    document.querySelectorAll('.platform-checkbox').forEach(cb => cb.checked = false);
    applyFilters();
}

function clearCountries() {
    document.querySelectorAll('.country-checkbox').forEach(cb => cb.checked = false);
    applyFilters();
}

function navigate(direction) {
    const max = filteredAccounts.length - 1;
    currentIndex = Math.max(0, Math.min(max, currentIndex + direction));
    renderCard();
    updateCounter();
}

function renderCard() {
    const a = filteredAccounts[currentIndex];
    if (!a) {
        document.getElementById('account-name').textContent = 'No matching accounts';
        document.getElementById('prep-content').innerHTML = '';
        return;
    }

    // Basic fields
    document.getElementById('account-name').textContent = a.Name;
    document.getElementById('account-revenue').textContent = a.revenue_formatted || 'N/A';

    let platformDisplay = a.Current_E_Commerce_Platform__c || '';
    if (platformDisplay === 'Other' && a.Other_Current_E_Commerce_Platform__c) {
        platformDisplay = `Other (${a.Other_Current_E_Commerce_Platform__c})`;
    }
    document.getElementById('account-platform').textContent = platformDisplay || 'Unknown';

    document.getElementById('account-industry').textContent = a.Industry || 'Unknown';
    document.getElementById('account-country').textContent = a.BillingCountry || 'Unknown';
    document.getElementById('account-score').textContent = `${a.priority_score}/12 — ${a.priority_tier}`;

    // Website link
    const website = a.Website ?
        (a.Website.startsWith('http') ? a.Website : `https://${a.Website}`) : null;
    const wsEl = document.getElementById('account-website');
    if (website) {
        wsEl.href = website;
        wsEl.textContent = a.Website;
    } else {
        wsEl.href = '#';
        wsEl.textContent = '';
    }

    // Badges
    const tierBadge = document.getElementById('tier-badge');
    tierBadge.textContent = a.priority_tier;
    tierBadge.className = `badge badge-tier ${a.priority_tier}`;

    document.getElementById('priority-badge').textContent = `Score: ${a.priority_score}`;
    document.getElementById('industry-badge').textContent = `${a.industry_label} (${a.industry_score}/3)`;
    document.getElementById('platform-badge').textContent = `${a.platform_label} (${a.platform_score}/4)`;

    // Contacts
    renderContacts(a.Contacts || []);

    // Prep: show cached or placeholder
    if (prepCache[a.Id]) {
        renderPrep(prepCache[a.Id]);
    } else {
        document.getElementById('prep-content').innerHTML =
            '<p class="prep-placeholder">Click "Generate with AI" to create call prep for this account.</p>';
    }
}

function renderContacts(contacts) {
    const el = document.getElementById('contacts-list');
    if (!contacts.length) {
        el.innerHTML = '<p class="text-muted">No contacts on record.</p>';
        return;
    }
    el.innerHTML = contacts.map(c => {
        const name = `${c.FirstName || ''} ${c.LastName || ''}`.trim();
        const title = c.Title ? `<div class="contact-title">${c.Title}</div>` : '';
        const mobile = c.MobilePhone ? `<div class="contact-mobile">📱 ${c.MobilePhone}</div>` : '';
        const phone = c.Phone ? `<div class="contact-phone">☎ ${c.Phone}</div>` : '';
        const email = c.Email ? `<div class="contact-email"><a href="mailto:${c.Email}">${c.Email}</a></div>` : '';
        return `
            <div class="contact-card">
                <strong>${name}</strong>
                ${title}
                ${mobile}
                ${phone}
                ${email}
            </div>
        `;
    }).join('');
}

async function generatePrep() {
    const a = filteredAccounts[currentIndex];
    if (!a) return;

    const btn = document.getElementById('btn-generate');
    btn.textContent = 'Generating...';
    btn.disabled = true;
    document.getElementById('prep-content').innerHTML = '<p class="loading-dots">Generating call prep with Claude...</p>';

    try {
        const res = await fetch('/generate_prep', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ account_id: a.Id })
        });
        const prep = await res.json();
        prepCache[a.Id] = prep;
        renderPrep(prep);
    } catch (e) {
        document.getElementById('prep-content').innerHTML = `<p class="error">Generation failed: ${e.message}</p>`;
    } finally {
        btn.textContent = 'Regenerate';
        btn.disabled = false;
    }
}

function renderPrep(prep) {
    if (prep.error) {
        document.getElementById('prep-content').innerHTML =
            `<p class="error">${prep.talking_points[0]?.detail || 'Generation failed'}</p>`;
        return;
    }

    let html = '<div class="prep-content">';

    // Opening Intro
    if (prep.intro) {
        html += `<div class="prep-intro"><strong>${prep.intro}</strong></div>`;
    }

    // Talking Points
    if (prep.talking_points && prep.talking_points.length) {
        html += '<div class="prep-section"><h4>Talking Points</h4>';
        prep.talking_points.forEach(tp => {
            html += `<div class="prep-item">
                <div class="prep-item-headline">${tp.headline}</div>
                <div class="prep-item-detail">${tp.detail}</div>
            </div>`;
        });
        html += '</div>';
    }

    // Discovery Questions
    if (prep.discovery_questions && prep.discovery_questions.length) {
        html += '<div class="prep-section"><h4>Discovery Questions</h4>';
        prep.discovery_questions.forEach(dq => {
            html += `<div class="prep-item">
                <div class="prep-item-headline">${dq.question}</div>
                <div class="prep-item-detail"><em>${dq.why}</em></div>
            </div>`;
        });
        html += '</div>';
    }

    // Objection Handlers
    if (prep.objection_handlers && prep.objection_handlers.length) {
        html += '<div class="prep-section"><h4>Objection Handlers</h4>';
        prep.objection_handlers.forEach(oh => {
            html += `<div class="prep-item">
                <div class="prep-item-headline">${oh.objection}</div>
                <div class="prep-item-detail">${oh.response}</div>
            </div>`;
        });
        html += '</div>';
    }

    html += '</div>';
    document.getElementById('prep-content').innerHTML = html;
}

function updateCounter() {
    document.getElementById('card-counter').textContent =
        `Account ${currentIndex + 1} of ${filteredAccounts.length}`;
}

function shuffleAccounts() {
    for (let i = filteredAccounts.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [filteredAccounts[i], filteredAccounts[j]] = [filteredAccounts[j], filteredAccounts[i]];
    }
    currentIndex = 0;
    renderCard();
    updateCounter();
}

function downloadCSV() {
    const tier = document.getElementById('filter-tier').value;
    const industries = Array.from(document.querySelectorAll('.industry-checkbox:checked')).map(cb => cb.value);
    const countries = Array.from(document.querySelectorAll('.country-checkbox:checked')).map(cb => cb.value);
    const platforms = Array.from(document.querySelectorAll('.platform-checkbox:checked')).map(cb => cb.value);

    let url = '/export.csv?';
    const params = [];
    if (tier) params.push(`tier=${encodeURIComponent(tier)}`);
    industries.forEach(ind => params.push(`industry=${encodeURIComponent(ind)}`));
    countries.forEach(country => params.push(`country=${encodeURIComponent(country)}`));
    platforms.forEach(plat => params.push(`platform=${encodeURIComponent(plat)}`));

    if (params.length > 0) url += params.join('&');
    window.location.href = url;
}

async function triggerRefresh() {
    document.getElementById('loading-overlay').classList.remove('hidden');
    document.getElementById('loading-message').textContent = 'Pulling data from Salesforce (BanffProd)...';

    await fetch('/refresh', { method: 'POST' });

    const poll = setInterval(async () => {
        const status = await fetch('/status').then(r => r.json());
        document.getElementById('loading-message').textContent = `Loaded ${status.count} accounts...`;
        if (!status.loading) {
            clearInterval(poll);
            window.location.reload();
        }
    }, 2000);
}

function toggleDropdown(type) {
    const dropdownId = `${type}-dropdown`;
    const dropdown = document.getElementById(dropdownId);
    dropdown.classList.toggle('open');
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown-filter')) {
        document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('open'));
    }
});

// Initial render
renderCard();
updateCounter();
