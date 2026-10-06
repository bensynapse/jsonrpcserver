import sys

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from jsonrpcserver import Result, Success, dispatch, method

# A whole Django project in one file. In a real project, the view and the URL
# pattern go in your app as usual.
settings.configure(
    ROOT_URLCONF=__name__,
    ALLOWED_HOSTS=["localhost", "127.0.0.1"],
    SECRET_KEY="replace-me",
)


@method
def ping() -> Result:
    return Success("pong")


@csrf_exempt
def jsonrpc(request: HttpRequest) -> HttpResponse:
    if response := dispatch(request.body.decode()):
        return HttpResponse(response, content_type="application/json")
    return HttpResponse(status=204)


urlpatterns = [path("", jsonrpc)]

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line([sys.argv[0], "runserver", "5000", "--noreload"])
