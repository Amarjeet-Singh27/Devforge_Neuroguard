// ===== Dynamic Features & Enhancements =====

// Smooth page transitions
document.addEventListener('DOMContentLoaded', () => {
  // Add smooth scroll behavior
  document.documentElement.style.scrollBehavior = 'smooth';

  // Animate all sections on scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.animation = 'fadeIn 0.6s ease-in';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.card, .stat-card, .auth-card').forEach(el => {
    observer.observe(el);
  });
});

// Add ripple effect on button clicks
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.btn').forEach(button => {
    button.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      ripple.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        background: rgba(255, 255, 255, 0.5);
        border-radius: 50%;
        left: ${x}px;
        top: ${y}px;
        animation: ripple-animation 0.6s ease-out;
        pointer-events: none;
      `;

      this.style.position = 'relative';
      this.style.overflow = 'hidden';
      this.appendChild(ripple);

      setTimeout(() => ripple.remove(), 600);
    });
  });
});

// Ripple animation
const style = document.createElement('style');
style.textContent = `
  @keyframes ripple-animation {
    from {
      transform: scale(0);
      opacity: 1;
    }
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

// Form field focus effects
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input, textarea, select').forEach(field => {
    field.addEventListener('focus', function() {
      this.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.1)';
      this.parentElement.style.animation = 'fadeIn 0.3s ease';
    });

    field.addEventListener('blur', function() {
      this.style.boxShadow = 'none';
    });
  });
});

// Animate page exit on link navigation
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', function(e) {
      // Skip if it's an internal action link
      if (this.onclick || this.getAttribute('onclick') || this.href === '#') {
        return;
      }

      // Skip if it's an external link or anchor
      if (this.target === '_blank' || this.href.startsWith('#') || this.href.includes('mailto')) {
        return;
      }

      // Only animate if navigating away
      const currentDomain = window.location.hostname;
      const linkDomain = new URL(this.href, window.location.origin).hostname;

      if (currentDomain === linkDomain && this.href !== window.location.href) {
        e.preventDefault();
        document.body.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => {
          window.location.href = this.href;
        }, 300);
      }
    });
  });
});

// Add loading class to buttons while processing
document.addEventListener('DOMContentLoaded', () => {
  const originalFetch = window.fetch;
  window.fetch = function(...args) {
    const buttons = document.querySelectorAll('button[type="submit"]');
    buttons.forEach(btn => {
      btn.disabled = true;
      btn.style.opacity = '0.7';
    });

    return originalFetch.apply(this, args).then(response => {
      buttons.forEach(btn => {
        btn.disabled = false;
        btn.style.opacity = '1';
      });
      return response;
    }).catch(error => {
      buttons.forEach(btn => {
        btn.disabled = false;
        btn.style.opacity = '1';
      });
      throw error;
    });
  };
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  // ESC to close modals
  if (e.key === 'Escape') {
    const modal = document.querySelector('.modal.active');
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  // Ctrl+K for focus search (if exists)
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const searchInput = document.querySelector('[data-search]');
    if (searchInput) {
      searchInput.focus();
    }
  }
});

// Prevent page exit unsaved changes
let hasUnsavedChanges = false;
let isFormSubmitting = false;

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input, textarea, select').forEach(field => {
    field.addEventListener('change', () => {
      hasUnsavedChanges = true;
    });
  });

  // Reset on successful form submission
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', () => {
      // User intentionally submitted the form; don't block navigation.
      isFormSubmitting = true;
      hasUnsavedChanges = false;
      setTimeout(() => {
        isFormSubmitting = false;
      }, 2000);
    });
  });
});

window.addEventListener('beforeunload', (e) => {
  if (hasUnsavedChanges && !isFormSubmitting) {
    const message = 'You have unsaved changes. Are you sure you want to leave?';
    e.returnValue = message;
    return message;
  }
});

// Add window resize listener for responsive behavior
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  document.body.style.opacity = '0.95';
  resizeTimer = setTimeout(() => {
    document.body.style.opacity = '1';
  }, 150);
});

// Detect dark mode preference
function initDarkModeDetection() {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
  
  const updateTheme = (isDark) => {
    if (isDark) {
      // Apply dark mode styles if needed
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
    }
  };

  updateTheme(prefersDark.matches);
  prefersDark.addEventListener('change', (e) => {
    updateTheme(e.matches);
  });
}

initDarkModeDetection();

// Performance monitoring
window.addEventListener('load', () => {
  if (window.performance && window.performance.timing) {
    const perfData = window.performance.timing;
    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
    console.log(`Page loaded in ${pageLoadTime}ms`);
  }
});

// Network status indicator
window.addEventListener('online', () => {
  showAlert('✓ Connection restored!', 'success');
});

window.addEventListener('offline', () => {
  showAlert('✕ No internet connection', 'warning');
});

console.log('Dynamic features loaded! ✨');
