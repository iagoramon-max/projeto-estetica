# agendamentos/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from .models import Service, Booking, Professional
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta, time, date
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
import traceback

# configuração: granulação dos slots (15 minutos)
SLOT_INTERVAL_MIN = 15

# horários por dia da semana (0=segunda, 6=domingo)
# cada valor é (start_time, end_time) onde end_time é hora limite do expediente
DAY_SCHEDULE = {
    0: (time(8, 0), time(17, 0)),  # seg
    1: (time(8, 0), time(17, 0)),  # ter
    2: (time(8, 0), time(17, 0)),  # qua
    3: (time(8, 0), time(17, 0)),  # qui
    4: (time(8, 0), time(17, 0)),  # sex
    5: (time(8, 0), time(12, 0)),  # sab
    6: None,                       # dom fechado
}


def make_aware_if_naive(dt):
    """
    Recebe um datetime e retorna um aware datetime usando timezone.get_current_timezone()
    se o datetime for naive. Se já for aware, retorna como está.
    """
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


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


def get_work_period_for_date(day_date):
    """
    Retorna (start_time, end_time) do expediente para a data dada.
    Se fechado, retorna None.
    """
    weekday = day_date.weekday()  # 0=segunda
    return DAY_SCHEDULE.get(weekday, None)


def generate_slots_for_day(day_date, service_duration_min):
    """
    Gera lista de datetimes (início) válidos naquele dia respeitando o expediente.
    Retorna datetimes *aware* (com timezone) para evitar comparações inválidas.
    Se dia fechado, retorna [].
    """
    period = get_work_period_for_date(day_date)
    if not period:
        return []  # dia fechado

    start_time, end_time = period
    slots = []
    cur = datetime.combine(day_date, start_time)
    end_of_day = datetime.combine(day_date, end_time)

    # tornar aware (se o projeto usa USE_TZ=True, fazemos aware)
    # use make_aware_if_naive para ser seguro
    cur = make_aware_if_naive(cur)
    end_of_day = make_aware_if_naive(end_of_day)

    # permitimos slots enquanto slot_start + duration <= end_of_day
    while cur + timedelta(minutes=service_duration_min) <= end_of_day:
        slots.append(cur)
        cur = cur + timedelta(minutes=SLOT_INTERVAL_MIN)
    return slots


def is_conflicting(professional, start_dt, end_dt):
    # garantir start_dt/end_dt aware
    start_dt = make_aware_if_naive(start_dt)
    end_dt = make_aware_if_naive(end_dt)
    return Booking.objects.filter(
        professional=professional,
        start_datetime__lt=end_dt,
        end_datetime__gt=start_dt
    ).exists()


def index(request):
    services = Service.objects.all()
    prof = Professional.objects.first()
    # próximos 14 dias (inclui hoje)
    raw_days = [ (timezone.localdate() + timedelta(days=i)) for i in range(0, 14) ]

    days_info = []
    for d in raw_days:
        # day_start/day_end em aware para consistência
        day_start = make_aware_if_naive(datetime.combine(d, time(0,0)))
        day_end = make_aware_if_naive(datetime.combine(d, time(23,59,59)))
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
    """
    Endpoint que retorna o partial HTML com os slots daquele dia para um serviço e profissional.
    """
    try:
        day = request.GET.get('day')
        service_id = request.GET.get('service_id')
        prof_id = request.GET.get('professional_id')
        if not (day and service_id and prof_id):
            return HttpResponseBadRequest('Parâmetros faltando')

        # parse da data
        try:
            day_date = parse_day_to_date(day)
        except ValueError:
            return HttpResponseBadRequest('Formato de data inválido')

        service = get_object_or_404(Service, pk=service_id)
        prof = get_object_or_404(Professional, pk=prof_id)

        slots = generate_slots_for_day(day_date, service.duration_min)

        # bookings do dia (para marcar ocupados)
        day_start = make_aware_if_naive(datetime.combine(day_date, time(0,0)))
        day_end = make_aware_if_naive(datetime.combine(day_date, time(23,59,59)))
        bookings = Booking.objects.filter(professional=prof, start_datetime__gte=day_start, start_datetime__lte=day_end)

        occupied = []
        for b in bookings:
            # b.start_datetime e b.end_datetime costumam ser aware vindo do banco
            occupied.append((b.start_datetime, b.end_datetime))

        slots_info = []
        for s in slots:
            s_end = s + timedelta(minutes=service.duration_min)
            available = True
            for (o_s, o_e) in occupied:
                # garantir comparações entre aware datetimes
                o_s = make_aware_if_naive(o_s)
                o_e = make_aware_if_naive(o_e)
                if s < o_e and s_end > o_s:
                    available = False
                    break
            slots_info.append({
                'start': s,
                'start_iso': s.isoformat(),
                'available': available
            })

        # PASSAR professional explicitamente (não depender de request.GET no template)
        html = render_to_string('agendamentos/partials/slots.html', {
            'slots_info': slots_info,
            'service': service,
            'professional': prof
        }, request=request)
        return HttpResponse(html)
    except Exception as e:
        print("ERROR in slots_for_day:", str(e))
        traceback.print_exc()
        return HttpResponse("Erro interno ao obter horários.", status=500)


@require_POST
@csrf_exempt
def book_appointment(request):
    import json
    try:
        if request.content_type == 'application/json':
            payload = json.loads(request.body)
        else:
            payload = request.POST.dict()
    except:
        payload = request.POST.dict()

    try:
        prof_id = int(payload.get('professional_id'))
        service_id = int(payload.get('service_id'))
        start_iso = payload.get('start')
        client_name = payload.get('client_name')
        client_phone = payload.get('client_phone')
    except Exception:
        return HttpResponseBadRequest('Dados inválidos')

    try:
        professional = get_object_or_404(Professional, pk=prof_id)
        service = get_object_or_404(Service, pk=service_id)
    except:
        return HttpResponseBadRequest('Profissional ou serviço inválido')

    try:
        # parse start ISO em aware/naive: fromisoformat produz naive se sem offset, então convertemos
        start_dt = datetime.fromisoformat(start_iso)
    except Exception:
        return HttpResponseBadRequest('Formato de data inválido')

    # tornar aware se necessário
    start_dt = make_aware_if_naive(start_dt)
    end_dt = start_dt + timedelta(minutes=service.duration_min)

    try:
        with transaction.atomic():
            if is_conflicting(professional, start_dt, end_dt):
                return JsonResponse({'status':'error','message':'Horário já reservado'}, status=409)
            booking = Booking.objects.create(
                professional=professional,
                service=service,
                client_name=client_name,
                client_phone=client_phone,
                start_datetime=start_dt,
                end_datetime=end_dt
            )
    except Exception as e:
        print("ERROR in book_appointment:", str(e))
        traceback.print_exc()
        return JsonResponse({'status':'error','message':str(e)}, status=500)

    return JsonResponse({'status':'ok', 'booking':{
        'id': booking.id,
        'service': service.name,
        'start': booking.start_datetime.isoformat(),
        'end': booking.end_datetime.isoformat(),
        'client_name': booking.client_name,
        'client_phone': booking.client_phone
    }})


@require_POST
@csrf_exempt
def notify_whatsapp(request):
    import json
    try:
        payload = json.loads(request.body)
    except:
        payload = request.POST.dict()
    booking_id = payload.get('booking_id')
    to = payload.get('to', 'professional')
    print(f"[SIMULATED-WHATSAPP] Notify {to} about booking {booking_id}")
    return JsonResponse({'status':'ok','msg':'simulated'})
