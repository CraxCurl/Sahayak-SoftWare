/**
 * Sahayak AI Browser Automation Demo Script
 * Handles form validation, data persistence, and page transitions
 */

document.addEventListener('DOMContentLoaded', () => {
  // Check if we are on Page 1 (Registration / Login Form)
  const loginForm = document.getElementById('demo-form');
  if (loginForm) {
    initLoginPage(loginForm);
  }

  // Check if we are on Page 2 (Success Dashboard)
  const successContainer = document.getElementById('success-dashboard');
  if (successContainer) {
    initSuccessPage();
  }
});

/**
 * Initialize Page 1: Form Validation & Submission
 */
function initLoginPage(form) {
  const firstNameInput = document.getElementById('first-name');
  const lastNameInput = document.getElementById('last-name');
  const ageInput = document.getElementById('age');
  const stateInput = document.getElementById('state');
  const loginBtn = document.getElementById('login-button');

  // Clear error states on input
  [firstNameInput, lastNameInput, ageInput, stateInput].forEach((input) => {
    if (!input) return;
    input.addEventListener('input', () => {
      const group = input.closest('.form-group');
      if (group) group.classList.remove('has-error');
    });
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();

    let isValid = true;
    const data = {
      firstName: firstNameInput ? firstNameInput.value.trim() : '',
      lastName: lastNameInput ? lastNameInput.value.trim() : '',
      age: ageInput ? ageInput.value.trim() : '',
      state: stateInput ? stateInput.value.trim() : ''
    };

    // Validation checks
    if (!data.firstName) {
      setError(firstNameInput, 'First name is required');
      isValid = false;
    }

    if (!data.lastName) {
      setError(lastNameInput, 'Last name is required');
      isValid = false;
    }

    if (!data.age || isNaN(data.age) || Number(data.age) <= 0 || Number(data.age) > 130) {
      setError(ageInput, 'Please enter a valid age (1-130)');
      isValid = false;
    }

    if (!data.state) {
      setError(stateInput, 'State is required');
      isValid = false;
    }

    if (!isValid) {
      return;
    }

    // Persist data in storage
    try {
      sessionStorage.setItem('sahayak_demo_user', JSON.stringify(data));
      localStorage.setItem('sahayak_demo_user', JSON.stringify(data));
    } catch (err) {
      console.warn('Storage unavailable, using query parameters fallback', err);
    }

    // Prepare query parameters for file:// and cross-origin compatibility
    const params = new URLSearchParams({
      firstName: data.firstName,
      lastName: data.lastName,
      age: data.age,
      state: data.state
    });

    // Navigate to Page 2
    window.location.href = `success.html?${params.toString()}`;
  });
}

function setError(inputElement, message) {
  if (!inputElement) return;
  const group = inputElement.closest('.form-group');
  if (group) {
    group.classList.add('has-error');
    const errorSpan = group.querySelector('.error-text');
    if (errorSpan && message) {
      errorSpan.textContent = message;
    }
  }
}

/**
 * Initialize Page 2: Success Dashboard & Data Display
 */
function initSuccessPage() {
  const displayGreeting = document.getElementById('welcome-heading');
  const displayFirstName = document.getElementById('display-first-name');
  const displayLastName = document.getElementById('display-last-name');
  const displayFullName = document.getElementById('display-full-name');
  const displayAge = document.getElementById('display-age');
  const displayState = document.getElementById('display-state');
  const resetBtn = document.getElementById('reset-button');

  // Read data from URL Query Parameters -> sessionStorage -> localStorage -> fallback defaults
  const urlParams = new URLSearchParams(window.location.search);
  let userData = null;

  if (urlParams.get('firstName') || urlParams.get('lastName')) {
    userData = {
      firstName: urlParams.get('firstName') || '',
      lastName: urlParams.get('lastName') || '',
      age: urlParams.get('age') || '',
      state: urlParams.get('state') || ''
    };
  }

  if (!userData) {
    try {
      const stored = sessionStorage.getItem('sahayak_demo_user') || localStorage.getItem('sahayak_demo_user');
      if (stored) {
        userData = JSON.parse(stored);
      }
    } catch (err) {
      console.warn('Could not read from local storage', err);
    }
  }

  // Fallback default sample for demo presentation if accessed directly
  if (!userData || !userData.firstName) {
    userData = {
      firstName: 'Arpit',
      lastName: 'Raj',
      age: '20',
      state: 'Bihar'
    };
  }

  // Populate elements
  const fullName = `${userData.firstName} ${userData.lastName}`.trim();

  if (displayGreeting) {
    displayGreeting.textContent = `Welcome, ${fullName}!`;
  }
  if (displayFirstName) {
    displayFirstName.textContent = userData.firstName;
  }
  if (displayLastName) {
    displayLastName.textContent = userData.lastName;
  }
  if (displayFullName) {
    displayFullName.textContent = fullName;
  }
  if (displayAge) {
    displayAge.textContent = userData.age;
  }
  if (displayState) {
    displayState.textContent = userData.state;
  }

  // Setup Reset / Back button
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      try {
        sessionStorage.removeItem('sahayak_demo_user');
        localStorage.removeItem('sahayak_demo_user');
      } catch (err) {
        // Ignore
      }
      window.location.href = 'index.html';
    });
  }
}
