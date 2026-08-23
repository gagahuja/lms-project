"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse("OK - Server Running")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),

    # fallback route (optional safety)
    path('health/', home),

]


from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )



# =========================================================
# GLOBAL 500 ERROR LOGGER
# =========================================================

import logging

logger = logging.getLogger(__name__)


def custom_500(request):
    logger.exception(
        "Unhandled server error: path=%s user=%s",
        request.path,
        (
            request.user.username
            if request.user.is_authenticated
            else "anonymous"
        ),
    )

    from django.shortcuts import render

    return render(
        request,
        "500.html",
        status=500
    )


handler500 = "config.urls.custom_500"


