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
WORK_START = time(9, 0)
WORK_END = time(19, 0)
SLOT_INTERVAL_MIN = 15
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
    if not (day and service_id and prof_id):
        return HttpResponseBadRequest('Parâmetros faltando')
    day_date = datetime.fromisoformat(day).date()
    service = get_object_or_404(Service, pk=service_id)
    prof = get_object_or_404(Professional, pk=prof_id)
    slots = generate_slots_for_day(day_date, service.duration_min)
    day_start = datetime.combine(day_date, time(0,0))
    day_end = datetime.combine(day_date, time(23,59,59))
    bookings = Booking.objects.filter(professional=prof, start_datetime__gte=day_start, start_datetime__lte=day_end)
    occupied = []
    for b in bookings:
        occupied.append((b.start_datetime, b.end_datetime))
    slots_info = []
    for s in slots:
        s_end = s + timedelta(minutes=service.duration_min)
        available = True
        for (o_s, o_e) in occupied:
            if s < o_e and s_end > o_s:
                available = False
                break
        slots_info.append({'start': s, 'available': available})
    html = render_to_string('agendamentos/partials/slots.html', {'slots_info': slots_info, 'service': service, 'request': request})
    return HttpResponse(html)
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
    professional = get_object_or_404(Professional, pk=prof_id)
    service = get_object_or_404(Service, pk=service_id)
    try:
        start_dt = datetime.fromisoformat(start_iso)
    except Exception:
        return HttpResponseBadRequest('Formato de data inválido')
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
