namespace Lighthouse.Web.Services;

public interface IEmailTwoFactorCodeStore
{
    string CreateCode(string userId);
    bool ValidateCode(string userId, string code);
}
