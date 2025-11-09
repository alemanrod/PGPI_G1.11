from django.shortcuts import render
from django.views import View

class EscaparateView(View):
    def get(self, request):
        return render(request, 'product/escaparate.html')
