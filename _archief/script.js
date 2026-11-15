// Filter & zoek functionaliteit
const filterBtns = document.querySelectorAll('.filter-btn');
const searchInput = document.getElementById('search');
const cards = document.querySelectorAll('.promise-card');
const noResults = document.getElementById('no-results');

let activeFilter = 'all';
let searchQuery = '';

function updateCards() {
  let visible = 0;

  cards.forEach(card => {
    const status = card.dataset.status;
    const text = card.innerText.toLowerCase();
    const matchesFilter = activeFilter === 'all' || status === activeFilter;
    const matchesSearch = searchQuery === '' || text.includes(searchQuery);

    if (matchesFilter && matchesSearch) {
      card.style.display = '';
      visible++;
    } else {
      card.style.display = 'none';
    }
  });

  noResults.classList.toggle('hidden', visible > 0);
}

filterBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    updateCards();
  });
});

searchInput.addEventListener('input', () => {
  searchQuery = searchInput.value.toLowerCase().trim();
  updateCards();
});

// Mobiel menu toggle
const menuToggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('nav');

menuToggle.addEventListener('click', () => {
  const isOpen = nav.style.display === 'flex';
  nav.style.display = isOpen ? '' : 'flex';
  if (!isOpen) {
    nav.style.flexDirection = 'column';
    nav.style.position = 'absolute';
    nav.style.top = '64px';
    nav.style.left = '0';
    nav.style.right = '0';
    nav.style.background = 'white';
    nav.style.padding = '16px 24px';
    nav.style.borderBottom = '1px solid #e2e8f0';
    nav.style.gap = '16px';
    nav.style.zIndex = '99';
  }
});

// Sluit menu bij klik op link
nav.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    if (window.innerWidth < 768) nav.style.display = '';
  });
});
