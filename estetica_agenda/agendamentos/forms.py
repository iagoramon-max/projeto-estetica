from django import forms
class QuickBookingForm(forms.Form):
    professional_id = forms.IntegerField(widget=forms.HiddenInput())
    service_id = forms.IntegerField(widget=forms.HiddenInput())
    start = forms.CharField(widget=forms.HiddenInput())  # ISO datetime
    client_name = forms.CharField(max_length=120)
    client_phone = forms.CharField(max_length=30)
