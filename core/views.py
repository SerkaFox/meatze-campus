from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def home(request):
    if request.user.is_authenticated:
        return redirect('/alumno/')
    # отдельный шаблон, который наследует base.html
    return render(request, "home.html")

def admin_panel(request):
    return render(request, "meatze_admin/base_admin.html")

def login_redirect(request):
    # если кто-то попал на /accounts/login/ → показываем главную и сразу открываем авторизацию
    return render(request, "home.html", {"force_login": True})


