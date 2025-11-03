# agendamentos/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from .models import Service, Booking, Professional
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta, time
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from .forms import QuickBookingForm
from django.views.decorators.csrf import csrf_exempt

# Configurações iniciais
WORK_START = time(9, 0)
WORK_END = time(19, 0)
SLOT_INTERVAL_MIN = 15

def parse_day_to_date(day_str):
    """
    Aceita:
     - '2025-11-03' (ISO)
     - '3 de Novembro de 2025' (Português) -> fallback
    Retorna uma datetime.date
    """
    # 1) tenta ISO (YYYY-MM-DD)
    try:
        return datetime.fromisoformat(day_str).date()
    except Exception:
        pass

    # 2) tenta formato '3 de Novembro de 2025' (ou '3 Novembro 2025')
    meses = {
        'janeiro':1,'fevereiro':2,'março':3,'marco':3,'abril':4,'maio':5,'junho':6,
        'julho':7,'agosto':8,'setembro':9,'outubro':10,'novembro':11,'dezembro':12
    }
    try:
        parts = day_str.strip().lower().replace('  ',' ').split()
        day = None; month = None; year = None
        for token in parts:
            if token.isdigit() and len(token) <= 2 and day is None:
                day = int(token)
            if token.isdigit() and len(token) == 4:
                year = int(token)
            if token in meses and month is None:
                month = meses[token]
        if day and month and year:
            from datetime import date
            return date(year, month, day)
    except Exception:
        pass

    # se não conseguiu, levanta ValueError
    raise ValueError(f"Formato de data inválido: {day_str}")

def index(request):
    services = Service.objects.all()
    prof = Professional.objects.first()
    days = [ (timezone.localdate() + timedelta(days=i)) for i in range(0, 14) ]
    return render(request, 'agendamentos/index.html', {'services': services, 'professional': prof, 'days': days})

def generate_slots_for_day(day_date, service_duration_min):
    slots = []
    cur = datetime.combine(day_date, WORK_START)
    end_of_day = datetime.combine(day_date, WORK_END)
    while cur + timedelta(minutes=service_duration_min) <= end_of_day:
        slots.append(cur)
        cur += timedelta(minutes=SLOT_INTERVAL_MIN)
    return slots

def is_conflicting(professional, start_dt, end_dt):
    return Booking.objects.filter(
        professional=professional,
        start_datetime__lt=end_dt,
        end_datetime__gt=start_dt
    ).exists()

def slots_for_day(request):
    day = request.GET.get('day')
    service_id = request.GET.get('service_id')
    prof_id = request.GET.get('professional_id')
