(function () {
  const key = "lh-theme"
  const root = document.documentElement

  function apply(stored) {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
    const theme = stored === "light" || stored === "dark" ? stored : prefersDark ? "dark" : "light"
    root.setAttribute("data-bs-theme", theme)
    return theme
  }

  let current = apply(localStorage.getItem(key))

  document.querySelectorAll(".lh-theme-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      current = current === "dark" ? "light" : "dark"
      localStorage.setItem(key, current)
      apply(current)
    })
  })
})()
