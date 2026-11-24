from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from .services import snapshot


@login_required
def index(request):
    return render(request, "office/index.html")


@login_required
def data(request):
    return JsonResponse(snapshot())
