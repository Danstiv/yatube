from django.shortcuts import render


def forbidden_handler(request, exception):
    return render(request, 'core/403.html')


def page_not_found_handler(request, exception):
    return render(request, 'core/404.html', {'path': request.path}, status=404)


def server_error_handler(request):
    return render(request, 'core/500.html')
