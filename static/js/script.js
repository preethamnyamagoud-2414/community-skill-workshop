/**
 * SkillConnect - Community Skill-Building Workshop Platform
 * Script: script.js
 */

document.addEventListener('DOMContentLoaded', function () {
  // ----------------------------------------------------
  // 1. Mobile Navigation Toggle
  // ----------------------------------------------------
  const navToggle = document.getElementById('navToggle');
  const navMenu = document.getElementById('navMenu');

  if (navToggle && navMenu) {
    navToggle.addEventListener('click', function () {
      const isOpen = navMenu.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    // Close mobile menu when a nav link is clicked
    const navLinks = navMenu.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        navMenu.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // ----------------------------------------------------
  // 2. Alert Dismissal
  // ----------------------------------------------------
  const alertCloseButtons = document.querySelectorAll('.alert-close');
  alertCloseButtons.forEach(button => {
    button.addEventListener('click', function () {
      const alertBox = this.closest('.alert');
      if (alertBox) {
        alertBox.style.opacity = '0';
        alertBox.style.transform = 'translateY(-6px)';
        alertBox.style.transition = 'all 0.25s ease';
        setTimeout(() => alertBox.remove(), 250);
      }
    });
  });

  // Auto-dismiss alerts after 5 seconds
  const autoAlerts = document.querySelectorAll('.alert');
  if (autoAlerts.length > 0) {
    setTimeout(() => {
      autoAlerts.forEach(alertBox => {
        alertBox.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        alertBox.style.opacity = '0';
        alertBox.style.transform = 'translateY(-6px)';
        setTimeout(() => alertBox.remove(), 400);
      });
    }, 5000);
  }

  // ----------------------------------------------------
  // 3. Homepage Contact Form Handler
  // ----------------------------------------------------
  const contactForm = document.getElementById('contactForm');
  const contactSuccessMsg = document.getElementById('contactSuccessMsg');

  if (contactForm && contactSuccessMsg) {
    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();
      contactForm.reset();
      contactSuccessMsg.style.display = 'block';
      setTimeout(() => {
        contactSuccessMsg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 100);
    });
  }

  // ----------------------------------------------------
  // 4. Workshop Search & Filter (on workshops.html)
  // ----------------------------------------------------
  const searchInput = document.getElementById('workshopSearch');
  const categoryFilter = document.getElementById('categoryFilter');
  const workshopCards = document.querySelectorAll('.workshop-card');

  function filterWorkshops() {
    if (!workshopCards.length) return;

    const searchTerm = (searchInput ? searchInput.value : '').toLowerCase().trim();
    const selectedCategory = (categoryFilter ? categoryFilter.value : 'all').toLowerCase();

    let matchCount = 0;

    workshopCards.forEach(card => {
      const title = (card.dataset.title || '').toLowerCase();
      const trainer = (card.dataset.trainer || '').toLowerCase();
      const category = (card.dataset.category || '').toLowerCase();

      const matchesSearch = !searchTerm || title.includes(searchTerm) || trainer.includes(searchTerm);
      const matchesCategory = selectedCategory === 'all' || category === selectedCategory || category.includes(selectedCategory);

      if (matchesSearch && matchesCategory) {
        card.style.display = 'flex';
        matchCount++;
      } else {
        card.style.display = 'none';
      }
    });

    const emptyState = document.getElementById('noResultsMsg');
    if (emptyState) {
      emptyState.style.display = matchCount === 0 ? 'block' : 'none';
    }
  }

  if (searchInput) searchInput.addEventListener('input', filterWorkshops);
  if (categoryFilter) categoryFilter.addEventListener('change', filterWorkshops);

  // Parse URL query parameter (e.g. ?cat=Technology) when redirected from Homepage categories
  const urlParams = new URLSearchParams(window.location.search);
  const catParam = urlParams.get('cat');
  if (catParam && categoryFilter) {
    for (let i = 0; i < categoryFilter.options.length; i++) {
      if (categoryFilter.options[i].value.toLowerCase().includes(catParam.toLowerCase())) {
        categoryFilter.selectedIndex = i;
        break;
      }
    }
    filterWorkshops();
  }

  // ----------------------------------------------------
  // 5. Interactive Star Rating (on feedback.html)
  // ----------------------------------------------------
  const starInputs = document.querySelectorAll('.star-rating input[type="radio"]');
  const ratingValueDisplay = document.getElementById('selectedRatingText');

  starInputs.forEach(star => {
    star.addEventListener('change', function () {
      if (ratingValueDisplay) {
        ratingValueDisplay.textContent = `You selected ${this.value} out of 5 stars`;
      }
    });
  });

  // ----------------------------------------------------
  // 6. Generic Confirmation Prompt for destructive actions
  // ----------------------------------------------------
  const confirmActions = document.querySelectorAll('[data-confirm]');
  confirmActions.forEach(el => {
    el.addEventListener('click', function (e) {
      const message = this.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // ----------------------------------------------------
  // 7. Dashboard Sidebar Active Link State
  // ----------------------------------------------------
  const sidebarLinks = document.querySelectorAll('.dashboard-sidebar .sidebar-link');
  sidebarLinks.forEach(link => {
    link.addEventListener('click', function () {
      const href = this.getAttribute('href');
      if (href && href.startsWith('#')) {
        sidebarLinks.forEach(l => l.classList.remove('active'));
        this.classList.add('active');
      }
    });
  });

  // ----------------------------------------------------
  // 8. Admin Workshop Table Live Search & Status Filter
  // ----------------------------------------------------
  const adminSearch = document.getElementById('adminWorkshopSearch');
  const adminStatus = document.getElementById('adminStatusFilter');
  const adminRows = document.querySelectorAll('.admin-workshop-row');

  function filterAdminWorkshops() {
    if (!adminRows.length) return;
    const term = (adminSearch ? adminSearch.value : '').toLowerCase().trim();
    const statusVal = (adminStatus ? adminStatus.value : 'all').toLowerCase();

    adminRows.forEach(row => {
      const text = row.innerText.toLowerCase();
      const status = (row.dataset.status || '').toLowerCase();

      const matchesSearch = !term || text.includes(term);
      const matchesStatus = statusVal === 'all' || status === statusVal;

      row.style.display = (matchesSearch && matchesStatus) ? '' : 'none';
    });
  }

  if (adminSearch) adminSearch.addEventListener('input', filterAdminWorkshops);
  if (adminStatus) adminStatus.addEventListener('change', filterAdminWorkshops);
});
