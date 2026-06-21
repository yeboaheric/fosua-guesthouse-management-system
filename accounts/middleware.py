import hashlib
import secrets

from django.core.cache import cache
from django.http import HttpResponse

from accounts.audit import client_ip, log_audit_event, module_from_url_name, set_current_request
from accounts.models import AuditLog


class SecurityHeadersMiddleware:
    """Apply browser security policy consistently to every response."""

    CONTENT_SECURITY_POLICY_PARTS = [
        "default-src 'self'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob:",
        "connect-src 'self'",
        "media-src 'self'",
        "worker-src 'self' blob:",
        "upgrade-insecure-requests",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(18)
        response = self.get_response(request)
        script_policy = (
            "script-src 'self' "
            f"'nonce-{request.csp_nonce}' "
            "https://cdn.jsdelivr.net https://unpkg.com"
        )
        response.setdefault(
            "Content-Security-Policy",
            "; ".join([*self.CONTENT_SECURITY_POLICY_PARTS, script_policy]),
        )
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response


class SensitiveEndpointRateLimitMiddleware:
    """Add IP/identity throttles around sensitive authentication endpoints."""

    PATH_LIMITS = {
        "/login/": (20, 300),
        "/password-reset/": (5, 3600),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _cache_key(scope, value):
        digest = hashlib.sha256((value or "unknown").encode("utf-8")).hexdigest()
        return f"security-rate:{scope}:{digest}"

    @staticmethod
    def _increment(key, timeout):
        if cache.add(key, 1, timeout=timeout):
            return 1
        try:
            return cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=timeout)
            return 1

    def __call__(self, request):
        if request.method == "POST" and request.path in self.PATH_LIMITS:
            limit, timeout = self.PATH_LIMITS[request.path]
            ip_value = client_ip(request) or "unknown"
            count = self._increment(self._cache_key(request.path, ip_value), timeout)
            identity = request.POST.get("username") or request.POST.get("email")
            identity_count = 0
            if identity:
                identity_count = self._increment(
                    self._cache_key(f"{request.path}:identity", identity.strip().casefold()),
                    timeout,
                )
            identity_limit = 10 if request.path == "/login/" else 3
            if count > limit or identity_count > identity_limit:
                try:
                    log_audit_event(
                        request=request,
                        action=AuditLog.ActionType.OTHER,
                        module="dashboard",
                        status_code=429,
                        details={"event": "authentication_rate_limited", "path": request.path},
                        mark_request=False,
                    )
                except Exception:
                    # Security logging must never make authentication unavailable.
                    pass
                response = HttpResponse(
                    "Too many requests. Please wait before trying again.",
                    status=429,
                    content_type="text/plain; charset=utf-8",
                )
                response["Retry-After"] = str(timeout)
                return response
        return self.get_response(request)


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        try:
            response = self.get_response(request)
        finally:
            set_current_request(None)

        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return response
        if response.status_code in {401, 403}:
            log_audit_event(
                request=request,
                action=AuditLog.ActionType.OTHER,
                module=module_from_url_name(
                    getattr(getattr(request, "resolver_match", None), "url_name", "")
                ),
                status_code=response.status_code,
                details={
                    "event": "authorization_denied",
                    "method": request.method,
                },
            )
            return response
        if getattr(request, "_audit_logged", False):
            return response
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return response
        if response.status_code >= 400:
            return response

        resolver_match = getattr(request, "resolver_match", None)
        url_name = getattr(resolver_match, "url_name", "")
        action_map = {
            "POST": AuditLog.ActionType.MANAGE,
            "PUT": AuditLog.ActionType.UPDATE,
            "PATCH": AuditLog.ActionType.UPDATE,
            "DELETE": AuditLog.ActionType.DELETE,
        }
        log_audit_event(
            request=request,
            action=action_map.get(request.method, AuditLog.ActionType.OTHER),
            module=module_from_url_name(url_name),
            status_code=response.status_code,
            details={
                "method": request.method,
                "url_name": url_name,
            },
        )
        return response
