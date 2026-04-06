using System.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using Lighthouse.Web.Models;

namespace Lighthouse.Web.Controllers;

public class HomeController : Controller
{
    public IActionResult Index()
    {
        ViewBag.Page = "home";
        return View("ReactApp");
    }

    [HttpGet]
    public IActionResult Impact()
    {
        ViewBag.Page = "impact";
        return View("ReactApp");
    }

    [HttpGet]
    public IActionResult About()
    {
        ViewBag.Page = "about";
        return View("ReactApp");
    }

    [HttpGet]
    public IActionResult Contact()
    {
        ViewBag.Page = "contact";
        return View("ReactApp");
    }

    [HttpGet]
    public IActionResult Privacy()
    {
        ViewBag.Page = "privacy";
        return View("ReactApp");
    }

    [HttpPost]
    [IgnoreAntiforgeryToken]
    public IActionResult Contact(string name, string email, string message)
    {
        var ok = !string.IsNullOrWhiteSpace(name) && !string.IsNullOrWhiteSpace(email) && !string.IsNullOrWhiteSpace(message);
        ViewBag.Page = "contact";
        ViewBag.ContactSent = ok;
        return View("ReactApp");
    }

    [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
    public IActionResult Error()
    {
        return View(new ErrorViewModel { RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier });
    }
}
