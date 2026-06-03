from accounts.audit import log_audit_event, module_from_url_name, set_current_request
from accounts.models import AuditLog


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
