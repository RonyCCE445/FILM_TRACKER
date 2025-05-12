document.addEventListener("DOMContentLoaded", function () {
    const toggleBtn = document.getElementById("modeToggle");

   
    if (localStorage.getItem("theme") === "dark") {
        document.body.classList.add("dark-mode");
    }

    toggleBtn.addEventListener("click", () => {
        document.body.classList.toggle("dark-mode");
        
  
        const mode = document.body.classList.contains("dark-mode") ? "dark" : "light";
        localStorage.setItem("theme", mode);
        
        
        toggleBtn.textContent = document.body.classList.contains("dark-mode") ? "Light Mode" : "Dark Mode";
    });
});
