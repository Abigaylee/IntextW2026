using System.Security.Cryptography;
using Microsoft.Extensions.Caching.Memory;

namespace Lighthouse.Web.Services;

public class InMemoryEmailTwoFactorCodeStore : IEmailTwoFactorCodeStore
{
    private const int CodeLifetimeMinutes = 10;
    private readonly IMemoryCache _cache;

    public InMemoryEmailTwoFactorCodeStore(IMemoryCache cache)
    {
        _cache = cache;
    }

    public string CreateCode(string userId)
    {
        var code = RandomNumberGenerator.GetInt32(0, 1_000_000).ToString("D6");
        _cache.Set(GetKey(userId), code, TimeSpan.FromMinutes(CodeLifetimeMinutes));
        return code;
    }

    public bool ValidateCode(string userId, string code)
    {
        if (!_cache.TryGetValue<string>(GetKey(userId), out var expected) || string.IsNullOrWhiteSpace(expected))
            return false;

        var isValid = string.Equals(expected, code, StringComparison.Ordinal);
        if (isValid)
            _cache.Remove(GetKey(userId));

        return isValid;
    }

    private static string GetKey(string userId) => $"email-2fa:{userId}";
}
