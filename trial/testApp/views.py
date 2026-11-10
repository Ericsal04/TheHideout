from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_safe


@require_safe
def home(request):
    return render(request, 'testApp/home.html')


@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    # Bind even an empty POST so required-field errors are displayed.
    form = UserCreationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your account is ready. Log in to TheHideout.')
        return redirect('login')

    return render(request, 'testApp/register.html', {'form': form})