from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render


@login_required
@permission_required("wanderer.basic_access")
def index(request):
    context = {"version": __import__("wanderer").__version__}
    return render(request, "wanderer/index.html", context)
