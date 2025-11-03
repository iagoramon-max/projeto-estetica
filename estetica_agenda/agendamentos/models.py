from django.db import models
class Professional(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    def __str__(self):
        return self.name
class Service(models.Model):
    name = models.CharField(max_length=120)
    duration_min = models.PositiveIntegerField(default=60)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    def __str__(self):
        return f"{self.name} ({self.duration_min} min)"
class Booking(models.Model):
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    client_name = models.CharField(max_length=120)
    client_phone = models.CharField(max_length=30)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['start_datetime']
    def __str__(self):
        return f"{self.client_name} - {self.service.name} @ {self.start_datetime}"
