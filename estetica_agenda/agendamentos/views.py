# agendamentos/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from .models import Service, Booking, Professional
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta, time, date
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from .forms import QuickBookingForm
from django.views.decorators.csrf import csrf_exempt
import traceback

# Configurações iniciais
WORK_START = time(9, 0)
WORK_END = time(19, 0)
SLOT_INTERVAL_MIN = 15

def parse_day_to_date(day_str):
    """
    Aceita ISO (YYYY-MM-DD) ou formato tipo '3 de Novembro de 2025'.
    Retorna datetime.date
    """
    try:
        return datetime.fromisoformat(day_str).date()
    except Exception:
        pass

    meses = {
        'janeiro':1,'fevereiro':2,'março':3,'marco':3,'abril':4,'maio':5,'junho':6,
        'julho':7,'agosto':8,'setembro':9,'outubro':10,'novembro':11,'dezembro':12
    }
    try:
        parts = day_str.strip().lower().replace('  ',' ').split()
        day_v = None; month = None; year = None
        for token in parts:
            if token.isdigit() and len(token) <= 2 and day_v is None:
                day_v = int(token)
            if token.isdigit() and len(token) == 4:
                year = int(token)
            if token in meses and month is None:
                month = meses[token]
        if day_v and month and year:
            return date(year, month, day_v)
    except Exception:
        pass

    raise ValueError(f"Formato de data inválido: {day_str}")

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

def index(request):
    services = Service.objects.all()
    prof = Professional.objects.first()
    # Próximos 14 dias (a partir de hoje)
    raw_days = [ (timezone.localdate() + timedelta(days=i)) for i in range(0, 14) ]

    # Para cada dia, contamos quantos agendamentos existem para o profissional
    days_info = []
    for d in raw_days:
        day_start = datetime.combine(d, time(0,0))
        day_end = datetime.combine(d, time(23,59,59))
        count = 0
        if prof:
            count = Booking.objects.filter(professional=prof, start_datetime__gte=day_start, start_datetime__lte=day_end).count()
        days_info.append({'date': d, 'iso': d.isoformat(), 'count': count})

    return render(request, 'agendamentos/index.html', {
        'services': services,
        'professional': prof,
        'days_info': days_info,
    })

def slots_for_day(request):
    try:
        day = request.GET.get('day')
        service_id = request.GET.get('service_id')
        prof_id = request.GET.get('professional_id')
        if not (day and service_id and prof_id):
            return HttpResponseBadRequest('Parâmetros faltando')

        try:
            day_date = parse_day_to_date(day)
        except ValueError:
            return HttpResponseBadRequest('Formato de data inválido')

        service = get_object_or_404(Service, pk=service_id)
        prof = get_object_or_404(Professional, pk=prof_id)

        slots = generate_slots_for_day(day_date, service.duration_min)
        day_start = datetime.combine(day_date, time(0,0))
        day_end = datetime.combine(day_date, time(23,59,59))
        bookings = Booking.objects.filter(professional=prof, start_datetime__gte=day_start, start_datetime__lte=day_end)

        occupied = []
        for b in bookings:
            occupied.append((b.start_datetime, b.end_datetime))

        # Importante: passamos também a string ISO pronta para o template
        slots_info = []
        for s in slots:
            s_end = s + timedelta(minutes=service.duration_min)
            available = True
            for (o_s, o_e) in occupied:
                if s < o_e and s_end > o_s:
                    available = False
                    break
            slots_info.append({
                'start': s,
                'start_iso': s.isoformat(),   # <-- string ISO pronta
                'available': available
            })

        html = render_to_string('agendamentos/partials/slots.html', {'slots_info': slots_info, 'service': service, 'request': request})
        return HttpResponse(html)
    except Exception as e:
        print("ERROR in slots_for_day:", str(e))
        traceback.print_exc()
        return HttpResponse("Erro interno ao obter horários.", status=500)

@require_POST
@csrf_exempt
def book_appointment(request):
    imp
