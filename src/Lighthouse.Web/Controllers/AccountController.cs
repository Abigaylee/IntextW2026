using Lighthouse.Web.Authorization;
using Lighthouse.Web.Models.Identity;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;

namespace Lighthouse.Web.Controllers;

public class AccountController : Controller
{
    private readonly SignInManager<ApplicationUser> _signInManager;
    private readonly UserManager<ApplicationUser> _userManager;

    public AccountController(SignInManager<ApplicationUser> signInManager, UserManager<ApplicationUser> userManager)
    {
        _signInManager = signInManager;
        _userManager = userManager;
    }

    [HttpGet]
    [AllowAnonymous]
    public IActionResult Login(string? returnUrl = null)
    {
        ViewBag.ReturnUrl = returnUrl;
        return View();
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    [AllowAnonymous]
    public async Task<IActionResult> Login(string email, string password, string? returnUrl = null)
    {
        ViewBag.ReturnUrl = returnUrl;
        if (string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(password))
        {
            ModelState.AddModelError(string.Empty, "Email and password are required.");
            return View();
        }

        var user = await _userManager.FindByEmailAsync(email);
        if (user == null)
        {
            ModelState.AddModelError(string.Empty, "Invalid login attempt.");
            return View();
        }

        var result = await _signInManager.PasswordSignInAsync(user, password, isPersistent: true, lockoutOnFailure: true);
        if (result.Succeeded)
            return LocalRedirect(string.IsNullOrEmpty(returnUrl) ? Url.Content("~/") : returnUrl!);

        ModelState.AddModelError(string.Empty, "Invalid login attempt.");
        return View();
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    [Authorize]
    public async Task<IActionResult> Logout()
    {
        await _signInManager.SignOutAsync();
        return RedirectToAction("Index", "Home");
    }

    [HttpGet]
    [AllowAnonymous]
    public IActionResult Register()
    {
        return View();
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    [AllowAnonymous]
    public async Task<IActionResult> Register(string email, string password, string confirmPassword, string? supporterId)
    {
        if (string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(password))
        {
            ModelState.AddModelError(string.Empty, "Email and password are required.");
            return View();
        }

        if (password != confirmPassword)
        {
            ModelState.AddModelError(string.Empty, "Passwords do not match.");
            return View();
        }

        int? sid = null;
        if (!string.IsNullOrWhiteSpace(supporterId) && int.TryParse(supporterId, out var parsed))
            sid = parsed;

        var user = new ApplicationUser
        {
            UserName = email,
            Email = email,
            EmailConfirmed = true,
            SupporterId = sid
        };

        var result = await _userManager.CreateAsync(user, password);
        if (!result.Succeeded)
        {
            foreach (var err in result.Errors)
                ModelState.AddModelError(string.Empty, err.Description);
            return View();
        }

        await _userManager.AddToRoleAsync(user, AppRoles.Donor);

        await _signInManager.SignInAsync(user, isPersistent: true);
        return RedirectToAction("Index", "Home");
    }

    [HttpGet]
    [AllowAnonymous]
    public IActionResult AccessDenied()
    {
        return View();
    }
}
