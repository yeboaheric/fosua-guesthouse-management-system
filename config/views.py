from django.http import JsonResponse
from django.utils import timezone


def healthz(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "fosua-guesthouse",
            "timestamp": timezone.now().isoformat(),
        }
    )
