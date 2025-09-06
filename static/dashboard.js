// Dropdown functionality
const dropdownBtn = document.querySelector('.dropbtn');
const dropdownMenu = document.querySelector('.dropdown-menu');

dropdownBtn.addEventListener('click', () => {
    dropdownMenu.classList.toggle('active');
});
