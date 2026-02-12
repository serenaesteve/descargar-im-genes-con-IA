
const btn = document.getElementById('themeBtn');
const key = 'theme_light';
function apply() {
  const isLight = localStorage.getItem(key) === '1';
  document.body.classList.toggle('light', isLight);
  btn.textContent = isLight ? 'Modo oscuro' : 'Modo claro';
}
btn?.addEventListener('click', () => {
  const isLight = localStorage.getItem(key) === '1';
  localStorage.setItem(key, isLight ? '0' : '1');
  apply();
});
apply();
