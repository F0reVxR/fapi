button = document.getElementById('toggle')

button.addEventListener('click', () => {
    document.body.classList.toggle("dark");
    button.classList.toggle("dark");
})